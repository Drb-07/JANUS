import os
import io
import math
import zipfile
import mimetypes
import tempfile
import uuid
from datetime import datetime
import streamlit as st
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from geopy.geocoders import Nominatim
import pvlib
import pandas as pd
import numpy as np
import base64
from io import BytesIO
from openai import OpenAI

# --- AI backend setup ---
# Two providers are supported, chosen by a single secret so you can switch
# without touching code (e.g. once your Fireworks credits land tomorrow):
#
#   API_PROVIDER = "openrouter"   -> free tier, no card, rate-limited (default for now)
#   API_PROVIDER = "fireworks"    -> paid/credited, higher limits
#
# NEVER hardcode API keys/secrets as fallback defaults in source code. Fail loudly
# if the required key is missing instead of silently falling back to no-auth.
API_PROVIDER = st.secrets.get("API_PROVIDER", "openrouter").strip().lower()

PROVIDER_CONFIG = {
    "openrouter": {
        "key_name": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        # "openrouter/free" is OpenRouter's own auto-router: it picks a working
        # free model for you, so we don't have to keep chasing which specific
        # free model slug is alive this week. Falls back to a specific,
        # verified-current (as of this session) free vision model if the
        # router alias itself is ever unavailable.
        # Check https://openrouter.ai/models (filter: Price = Free, Vision) if
        # both of these ever 404 — the free catalog rotates WITHOUT NOTICE.
        "model_name_secret": "OPENROUTER_MODEL_NAME",
        "default_model": "openrouter/free",
        "fallback_models": [
            "google/gemma-4-31b-it:free",
        ],
    },
    "fireworks": {
        "key_name": "FIREWORKS_API_KEY",
        "base_url": "https://api.fireworks.ai/inference/v1",
        # Check https://app.fireworks.ai/models (filter: Vision) if this 404s.
        "model_name_secret": "FIREWORKS_MODEL_NAME",
        "default_model": "accounts/fireworks/models/qwen3p7-plus",
        "fallback_models": [],
    },
}

if API_PROVIDER not in PROVIDER_CONFIG:
    st.error(f"Unknown API_PROVIDER '{API_PROVIDER}'. Use 'openrouter' or 'fireworks'.")
    st.stop()

_cfg = PROVIDER_CONFIG[API_PROVIDER]
API_KEY = st.secrets.get(_cfg["key_name"], "")

if not API_KEY:
    st.error(
        f"{_cfg['key_name']} is not set. Add it to your Streamlit secrets "
        "(.streamlit/secrets.toml or the Streamlit Cloud secrets manager) as:\n\n"
        f'{_cfg["key_name"]} = "your-key-here"'
    )
    st.stop()

# Both Fireworks and OpenRouter expose OpenAI-compatible endpoints, so the same
# client class works for either — only base_url/key/model differ.
client = OpenAI(api_key=API_KEY, base_url=_cfg["base_url"])
MODEL_NAME = st.secrets.get(_cfg["model_name_secret"], _cfg["default_model"])
# Try the configured model first, then fall back through known-good alternatives
# if it's been rotated out of the free tier or otherwise 404s.
CANDIDATE_MODELS = [MODEL_NAME] + [m for m in _cfg["fallback_models"] if m != MODEL_NAME]


def pil_image_to_data_uri(pil_image, fmt="JPEG"):
    """Encode a PIL Image as a base64 data URI for the OpenAI-style image_url field."""
    buffer = BytesIO()
    # Vision models generally expect RGB; convert to avoid failures on RGBA/P images.
    if pil_image.mode not in ("RGB", "L"):
        pil_image = pil_image.convert("RGB")
    pil_image.save(buffer, format=fmt)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return f"data:{mime};base64,{encoded}"

try:
    geolocator = Nominatim(user_agent="janus_adie_investigator_v3")
except Exception:
    geolocator = None

# UI Header Configuration
st.set_page_config(page_title="JANUS - ADIE Chat", page_icon="🔍", layout="centered")
st.title("🔍 JANUS - Advanced Deep Intelligence Engine")
st.subheader("Interactive Forensic Chat Engine")

# Initialize session state before it's used anywhere.
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

uploaded_file = st.file_uploader("Upload target asset file for conversational interrogation...", type=None)

# Basic Technical Metadata Helpers
def get_gps_info(exif_data):
    if not exif_data:
        return None
    try:
        # getexif() (unlike the legacy _getexif()) does not auto-resolve the
        # GPSInfo tag into a dict — it's just a pointer to a sub-IFD. Use
        # get_ifd() to explicitly pull out the parsed GPS tag dict.
        gps_ifd = exif_data.get_ifd(IFD.GPSInfo)
    except (KeyError, AttributeError):
        return None
    if not gps_ifd:
        return None
    gps_info = {}
    for gps_tag, value in gps_ifd.items():
        sub_tag_name = GPSTAGS.get(gps_tag, gps_tag)
        gps_info[sub_tag_name] = value
    return gps_info

def convert_to_degrees(value):
    try:
        # 60 minutes and 3600 seconds per degree (was incorrectly 3360).
        return float(value[0]) + (float(value[1]) / 60.0) + (float(value[2]) / 3600.0)
    except Exception:
        return 0.0

def get_lat_lon(gps_info):
    if not gps_info or 'GPSLatitude' not in gps_info or 'GPSLongitude' not in gps_info:
        return None, None
    try:
        lat = convert_to_degrees(gps_info['GPSLatitude'])
        if gps_info.get('GPSLatitudeRef', 'N') != 'N':
            lat = -lat
        lon = convert_to_degrees(gps_info['GPSLongitude'])
        if gps_info.get('GPSLongitudeRef', 'E') != 'E':
            lon = -lon
        return lat, lon
    except Exception:
        return None, None

# Core Analysis Logic
if uploaded_file is not None:
    # Use a randomized temp filename to avoid collisions/overwrites between users
    # and to avoid trusting the uploaded filename directly.
    original_name = uploaded_file.name
    _, ext = os.path.splitext(original_name)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(tempfile.gettempdir(), safe_name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    mime_type, _ = mimetypes.guess_type(original_name)

    if mime_type and mime_type.startswith('image'):
        st.image(uploaded_file, caption="Target Forensic Asset", use_container_width=True)
        img = Image.open(file_path)

        # Use the public getexif() API instead of the private _getexif(), which is
        # undocumented and raises AttributeError on formats like PNG.
        try:
            exif_data = img.getexif() or None
        except Exception:
            exif_data = None

        # Pull low-level raw signals quietly for cross reference background checks
        gps_raw = get_gps_info(exif_data) if exif_data else None
        lat, lon = get_lat_lon(gps_raw)

        # --- FORENSIC CONVERSATION PORTAL ---
        st.markdown("### 💬 Interrogate File Content")
        st.caption("Ask questions about surroundings, wardrobe markers, identities, or geographic hints inside the frame.")

        # Render historical messages
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_query := st.chat_input("Ex: What is the subject wearing? What country does this architecture belong to?"):
            with st.chat_message("user"):
                st.markdown(user_query)
            st.session_state.chat_history.append({"role": "user", "content": user_query})

            # Formulate prompt inject with auxiliary background metadata signals
            meta_context = ""
            if lat and lon:
                meta_context = f"\n[System Signal - Hardware Exif Embedded Geo-Coordinates: Latitude {lat:.4f}, Longitude {lon:.4f}]"

            full_prompt = f"Analyze this image from a forensic investigation standpoint. {meta_context}\nUser Request: {user_query}"

            with st.chat_message("assistant"):
                with st.spinner("Interrogating context..."):
                    try:
                        image_data_uri = pil_image_to_data_uri(img)
                        response = None
                        last_error = None
                        for candidate_model in CANDIDATE_MODELS:
                            try:
                                response = client.chat.completions.create(
                                    model=candidate_model,
                                    messages=[
                                        {
                                            "role": "user",
                                            "content": [
                                                {"type": "text", "text": full_prompt},
                                                {"type": "image_url", "image_url": {"url": image_data_uri}},
                                            ],
                                        }
                                    ],
                                )
                                break  # success — stop trying further candidates
                            except Exception as candidate_error:
                                last_error = candidate_error
                                continue  # this model unavailable/retired, try the next one
                        if response is None:
                            raise last_error
                        assistant_response = response.choices[0].message.content
                        st.markdown(assistant_response)
                    except Exception as e:
                        assistant_response = f"Chat interface compilation block: {e}. Check API deployment status keys."
                        st.error(assistant_response)

            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})

        # Keep tech specs collapsed to keep interface clutter-free
        with st.expander("🛠️ View Raw Sensor & System Properties Dump"):
            if exif_data:
                exif_dict = {str(TAGS.get(t, t)): str(v) for t, v in exif_data.items()}
                st.json(exif_dict)
            else:
                st.write("No traditional metadata properties indexed inside file.")

    else:
        st.warning("Conversational chat features currently optimization targeted for Image asset structures.")

    if os.path.exists(file_path):
        os.remove(file_path)
