"""
ADIE — Advanced Deep Intelligence Engine.

Forensic investigation of uploaded assets (currently: images). Extracts
EXIF/GPS metadata as background signal, then runs an interactive,
evidence-based chat over the asset using the Explainable AI response format.
"""
import os
import mimetypes
import tempfile
import uuid
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD

from config import call_model, pil_image_to_data_uri

# Explainable AI response contract (JANUS product vision, section 9). Every
# ADIE answer is structured this way so reasoning and confidence are always
# visible, not just a final answer.
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
        # 60 minutes and 3600 seconds per degree.
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


def render():
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
