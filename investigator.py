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


def call_model(messages):
    """Call the configured provider, trying each candidate model in order until
    one succeeds (handles free-tier models being retired/rotated mid-session)."""
    last_error = None
    for candidate_model in CANDIDATE_MODELS:
        try:
            response = client.chat.completions.create(model=candidate_model, messages=messages)
            return response.choices[0].message.content
        except Exception as candidate_error:
            last_error = candidate_error
            continue
    raise last_error


try:
    geolocator = Nominatim(user_agent="janus_adie_investigator_v3")
except Exception:
    geolocator = None

# --- JANUS platform metadata ---
# Full roadmap per the JANUS product vision. Only ADIE and CODEX are real,
# working engines today — everything else is shown honestly as planned/
# in-development rather than faked, so the shell reflects the actual state
# of the build.
JANUS_ENGINES = [
    {"name": "ADIE", "full_name": "Advanced Deep Intelligence Engine", "icon": "🔍",
     "desc": "Investigates images, documents, and evidence with explainable reasoning.",
     "status": "active"},
    {"name": "CODEX", "full_name": "Software Engineering Intelligence", "icon": "💻",
     "desc": "Code generation, architecture, debugging, security review, ROCm guidance.",
     "status": "active"},
    {"name": "AUIN", "full_name": "Universal Intelligence Network", "icon": "🌐",
     "desc": "Knowledge graph across search, research papers, news, and maps.",
     "status": "roadmap"},
    {"name": "UKE", "full_name": "Universal Knowledge Engine", "icon": "📚",
     "desc": "Cross-discipline academic and professional knowledge support.",
     "status": "roadmap"},
    {"name": "UKPE", "full_name": "Universal Knowledge Processing Engine", "icon": "📄",
     "desc": "Summaries, notes, flashcards, and mind maps from large document sets.",
     "status": "roadmap"},
    {"name": "AMIE", "full_name": "Medical Intelligence Engine", "icon": "🩺",
     "desc": "Digital twin, 3D anatomy, disease and medicine intelligence.",
     "status": "roadmap"},
    {"name": "NAVIS", "full_name": "Navigation Intelligence", "icon": "🗺️",
     "desc": "Route planning and geographic reasoning via A*/Dijkstra.",
     "status": "roadmap"},
    {"name": "USE", "full_name": "Universal Simulation Engine", "icon": "🧪",
     "desc": "Interactive simulation across physics, chemistry, engineering, medicine.",
     "status": "roadmap"},
    {"name": "UDI", "full_name": "Universal Design Intelligence", "icon": "🏗️",
     "desc": "Idea → requirements → 3D model → simulation → engineering report.",
     "status": "roadmap"},
]

# Explainable AI response contract (JANUS product vision, section 9). Every
# engine answer is structured this way so reasoning and confidence are always
# visible, not just a final answer — this is the one contract every engine
# shares, regardless of specialization.
ADIE_INSTRUCTIONS = """You are ADIE (Advanced Deep Intelligence Engine), the forensic investigation \
engine inside JANUS, a Universal AI Cognitive Operating System. You provide evidence-based, explainable analysis \
— never fabricate facts not visible in the image or given metadata.

Structure your ENTIRE response using exactly these markdown section headers, in this order, every time:

### 🎯 Final Answer
A direct, concise answer to the user's request.

### 📊 Confidence
State High / Medium / Low, with a one-sentence justification.

### 🧠 Reasoning
2-4 sentences on how you reached the answer.

### 🔍 Evidence
Bullet points citing specific visual details or metadata signals that support the answer.

### 🔄 Better Alternatives
Other plausible interpretations, if any. If none, say so.

### ❓ Missing Information
What additional information/angle/metadata would improve confidence.

### ➡️ Suggested Next Steps
1-3 concrete follow-up actions the investigator could take.
"""

CODEX_INSTRUCTIONS = """You are CODEX, the Software Engineering Intelligence engine inside JANUS, a Universal \
AI Cognitive Operating System. You help with code generation, architecture design, debugging, performance \
optimization, security review, and AMD ROCm/GPU-compute guidance. Never fabricate APIs, flags, or behavior you \
aren't confident about — flag uncertainty explicitly instead.

Structure your ENTIRE response using exactly these markdown section headers, in this order, every time:

### 🎯 Final Answer
The solution, code, or direct answer. Use fenced code blocks with the correct language tag for any code.

### 📊 Confidence
State High / Medium / Low, with a one-sentence justification (e.g. untested, version-dependent, assumes X).

### 🧠 Reasoning
2-4 sentences on the approach/design decisions behind the answer.

### 🔍 Evidence
Bullet points: relevant language/framework/hardware facts, complexity analysis, or known behavior that supports the answer.

### 🔄 Better Alternatives
Other valid approaches and their tradeoffs. If none, say so.

### ❓ Missing Information
What context (target hardware, ROCm version, constraints, existing codebase) would sharpen the answer.

### ➡️ Suggested Next Steps
1-3 concrete follow-up actions (e.g. tests to add, benchmarks to run, profiling to do).
"""


# --- Basic EXIF/GPS helpers (used by ADIE) ---
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


def render_adie():
    st.markdown("#### 🔍 ADIE — Advanced Deep Intelligence Engine _(Active)_")
    st.caption("Evidence-based forensic investigation, with full explainable reasoning on every answer.")

    if "chat_history_adie" not in st.session_state:
        st.session_state.chat_history_adie = []

    uploaded_file = st.file_uploader("Upload an asset for ADIE to investigate...", type=None, key="adie_uploader")

    if uploaded_file is None:
        return

    # Use a randomized temp filename to avoid collisions/overwrites between users
    # and to avoid trusting the uploaded filename directly.
    original_name = uploaded_file.name
    _, ext = os.path.splitext(original_name)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(tempfile.gettempdir(), safe_name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    mime_type, _ = mimetypes.guess_type(original_name)

    try:
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

            # --- ADIE INVESTIGATION PORTAL ---
            st.markdown("### 💬 Interrogate File Content")
            st.caption(
                "Ask ADIE about surroundings, wardrobe markers, identities, or geographic hints inside the "
                "frame. Every answer includes its reasoning, evidence, and confidence."
            )

            for message in st.session_state.chat_history_adie:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if user_query := st.chat_input(
                "Ex: What is the subject wearing? What country does this architecture belong to?",
                key="adie_chat_input",
            ):
                with st.chat_message("user"):
                    st.markdown(user_query)
                st.session_state.chat_history_adie.append({"role": "user", "content": user_query})

                meta_context = ""
                if lat and lon:
                    meta_context = (
                        f"\n[System Signal - Hardware Exif Embedded Geo-Coordinates: "
                        f"Latitude {lat:.4f}, Longitude {lon:.4f}]"
                    )

                full_prompt = (
                    f"{ADIE_INSTRUCTIONS}\n\n"
                    f"Analyze this image from a forensic investigation standpoint.{meta_context}\n\n"
                    f"User Request: {user_query}"
                )

                with st.chat_message("assistant"):
                    with st.spinner("Interrogating context..."):
                        try:
                            image_data_uri = pil_image_to_data_uri(img)
                            assistant_response = call_model([
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": full_prompt},
                                        {"type": "image_url", "image_url": {"url": image_data_uri}},
                                    ],
                                }
                            ])
                            st.markdown(assistant_response)
                        except Exception as e:
                            assistant_response = f"⚠️ ADIE engine error: {e}. Check API deployment/model status."
                            st.error(assistant_response)

                st.session_state.chat_history_adie.append({"role": "assistant", "content": assistant_response})

            with st.expander("🛠️ View Raw Sensor & System Properties Dump"):
                if exif_data:
                    exif_dict = {str(TAGS.get(t, t)): str(v) for t, v in exif_data.items()}
                    st.json(exif_dict)
                else:
                    st.write("No traditional metadata properties indexed inside file.")

        else:
            st.warning(
                "ADIE currently investigates image assets only. Document/PDF/video investigation is on the "
                "JANUS roadmap (see sidebar) but not yet active."
            )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def render_codex():
    st.markdown("#### 💻 CODEX — Software Engineering Intelligence _(Active)_")
    st.caption("Code generation, architecture, debugging, optimization, security review, and AMD ROCm guidance.")

    if "chat_history_codex" not in st.session_state:
        st.session_state.chat_history_codex = []

    task_focus = st.selectbox(
        "Task focus",
        [
            "General / Not sure",
            "Generate Code",
            "Architecture Design",
            "Debug an Error",
            "Performance Optimization",
            "Security Review",
            "AMD ROCm Guidance",
        ],
        key="codex_task_focus",
    )

    for message in st.session_state.chat_history_codex:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input(
        "Describe your task, paste code, or paste an error message...",
        key="codex_chat_input",
    ):
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.chat_history_codex.append({"role": "user", "content": user_query})

        full_prompt = (
            f"{CODEX_INSTRUCTIONS}\n\n"
            f"Task Focus: {task_focus}\n\n"
            f"User Request:\n{user_query}"
        )

        with st.chat_message("assistant"):
            with st.spinner("CODEX is working..."):
                try:
                    assistant_response = call_model([{"role": "user", "content": full_prompt}])
                    st.markdown(assistant_response)
                except Exception as e:
                    assistant_response = f"⚠️ CODEX engine error: {e}. Check API deployment/model status."
                    st.error(assistant_response)

        st.session_state.chat_history_codex.append({"role": "assistant", "content": assistant_response})


# UI Header Configuration
st.set_page_config(page_title="JANUS - Cognitive OS", page_icon="🧠", layout="wide")

# --- Sidebar: Core Orchestrator ---
with st.sidebar:
    st.markdown("## 🧠 JANUS")
    st.caption("Universal AI Cognitive Operating System")
    st.markdown("---")
    st.markdown("### Core Orchestrator")
    st.caption("Select an engine to route to.")

    engine_labels = [f"{e['icon']} {e['name']}" for e in JANUS_ENGINES]
    selected_label = st.radio(
        "Engine",
        engine_labels,
        label_visibility="collapsed",
        key="selected_engine_label",
    )
    selected_engine = JANUS_ENGINES[engine_labels.index(selected_label)]

    st.markdown(f"**{selected_engine['full_name']}**")
    st.caption(selected_engine["desc"])
    if selected_engine["status"] == "active":
        st.success("✅ Active", icon="✅")
    else:
        st.warning("🚧 On the roadmap — not built yet", icon="🚧")

    st.markdown("---")
    st.caption(f"Active backend: `{API_PROVIDER}` · `{MODEL_NAME}`")

st.title("🧠 JANUS — Universal AI Cognitive Operating System")

if selected_engine["name"] == "ADIE":
    render_adie()
elif selected_engine["name"] == "CODEX":
    render_codex()
else:
    st.markdown(f"#### {selected_engine['icon']} {selected_engine['full_name']} _(Roadmap)_")
    st.info(
        f"**{selected_engine['name']}** is part of the JANUS product vision but isn't built yet.\n\n"
        f"Planned capability: {selected_engine['desc']}\n\n"
        "Switch to **🔍 ADIE** or **💻 CODEX** in the sidebar to use the engines that are live today."
    )
