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
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
import pvlib
import pandas as pd
import numpy as np
import google.generativeai as genai

# --- Gemini API key setup ---
# NEVER hardcode API keys/secrets as fallback defaults in source code. If no key is
# configured, fail loudly instead of silently falling back to no-auth (which caused
# the previous "ACCESS_TOKEN_TYPE_UNSUPPORTED" OAuth error).
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

if not GEMINI_KEY:
    st.error(
        "GEMINI_API_KEY is not set. Add it to your Streamlit secrets "
        "(.streamlit/secrets.toml or the Streamlit Cloud secrets manager) as:\n\n"
        'GEMINI_API_KEY = "your-key-here"'
    )
    st.stop()

genai.configure(api_key=GEMINI_KEY)

# Use a current, supported model. Gemini 1.0/1.5 models have been shut down.
GEMINI_MODEL_NAME = "gemini-2.5-flash"

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
    gps_info = {}
    if not exif_data:
        return None
    for tag, value in exif_data.items():
        tag_name = TAGS.get(tag, tag)
        if tag_name == "GPSInfo":
            for gps_tag in value:
                sub_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                gps_info[sub_tag_name] = value[gps_tag]
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
                        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
                        response = model.generate_content([full_prompt, img])
                        assistant_response = response.text
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
