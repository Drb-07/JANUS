import os
import io
import math
import zipfile
import mimetypes
from datetime import datetime
import requests
import streamlit as st
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
import pvlib
import pandas as pd

# 1. API Configuration & Fallback Geolocator
API_URL = "https://api-inference.huggingface.co/models/timm/mobilenetv3_large_100.ra_in1k"
HEADERS = {"Authorization": "Bearer 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"} 

try:
    geolocator = Nominatim(user_agent="janus_adie_investigator_v3")
except Exception:
    geolocator = None

def query_vision_api(image_bytes):
    try:
        response = requests.post(API_URL, headers=HEADERS, data=image_bytes, timeout=10)
        return response.json()
    except Exception as e:
        print(f"API Error: {e}")
        return None

# 2. UI Header Configuration
st.set_page_config(page_title="JANUS - ADIE Pro Ultra", page_icon="🔍", layout="centered")
st.title("🔍 JANUS - Advanced Deep Intelligence Engine")
st.subheader("Surroundings & Environmental Forensic Module")

uploaded_file = st.file_uploader("Upload target file for environmental scene scan...", type=None)

# 3. Helper Functions
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
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
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

def format_exif_date(raw_date):
    if not raw_date:
        return None
    try:
        return datetime.strptime(str(raw_date).strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None

def calculate_sun_position(lat, lon, dt_object):
    try:
        times = pd.DatetimeIndex([dt_object]).tz_localize('UTC')
        solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
        azimuth = solpos['azimuth'].values[0]
        apparent_elevation = solpos['apparent_elevation'].values[0]
        return azimuth, apparent_elevation
    except Exception:
        return None, None

def compute_ela(img_path, quality=95):
    try:
        original = Image.open(img_path).convert('RGB')
        tmp_resaved = "tmp_resaved.jpg"
        original.save(tmp_resaved, 'JPEG', quality=quality)
        resaved_im = Image.open(tmp_resaved)
        
        diff = ImageChops.difference(original, resaved_im)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
        
        scale = 255.0 / max_diff
        enhanced_diff = ImageEnhance.Brightness(diff).enhance(scale)
        
        resaved_im.close()
        if os.path.exists(tmp_resaved):
            os.remove(tmp_resaved)
        return enhanced_diff
    except Exception:
        return None

# 4. Core Core Analysis Pipeline
def investigate_file(file_data, file_name):
    st.markdown(f"### --- Forensic Dossier: `{file_name}` ---")
    
    with open(file_name, "wb") as f:
        f.write(file_data.getbuffer())
        
    mime_type, _ = mimetypes.guess_type(file_name)
    
    if mime_type and mime_type.startswith('image'):
        st.image(file_data, caption="Target Image Asset", use_container_width=True)
        
        try:
            img = Image.open(file_name)
            exif_data = img._getexif()
            
            # --- 1. CONTEXTUAL OBJECT DETECTION VIA API ---
            st.markdown("### 👁️ Contextual Scene Interpretation (AI Scan)")
            with st.spinner("Streaming asset to AI Inference Engine..."):
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()
                
                predictions = query_vision_api(img_bytes)
                
                if predictions and isinstance(predictions, list) and len(predictions) > 0 and 'label' in predictions[0]:
                    for item in predictions:
                        label = item['label']
                        score = item['score'] * 100
                        st.write(f" * Identified: **{label}** ({score:.1f}% confidence)")
                        
                        if any(x in label.lower() for x in ["sign", "traffic", "street", "junction", "pole"]):
                            st.warning("📌 **Surroundings Warning:** Infrastructure tracking tags recognized. Examine the photograph frame for regional signage fonts or highway shield shapes.")
                else:
                    st.write("Vision Recognition Engine is initializing or sleeping. Try uploading again in a few seconds.")

            # --- 2. CELESTIAL ANALYSIS (SUN ANGLE & SHADOWS) ---
            st.markdown("### ☀️ Celestial Surroundings Analysis")
            lat, lon = None, None
            gps_raw = get_gps_info(exif_data) if exif_data else None
            if gps_raw:
                lat, lon = get_lat_lon(gps_raw)
                
            raw_date = exif_data.get(36867) if exif_data else None
            dt_obj = format_exif_date(raw_date)
            
            if lat and lon and dt_obj:
                azimuth, elevation = calculate_sun_position(lat, lon, dt_obj)
                if azimuth is not None and elevation is not None:
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        st.metric(label="🧭 Sun Azimuth Position", value=f"{azimuth:.2f}°")
                    with col_s2:
                        st.metric(label="📐 Sun Elevation Position", value=f"{elevation:.2f}°")
                    
                    if elevation > 0:
                        shadow_ratio = 1.0 / math.tan(math.radians(elevation))
                        st.info(f"💡 **Forensic Shadow Assessment:** Estimated shadow length is roughly **{shadow_ratio:.2f}x** the target object's true height.")
                    else:
                        st.info("💡 **Temporal Note:** Calculated sun position is below the horizon array (Night capture matrix).")
                else:
                    st.write("Unable to compile accurate trajectory angles from metadata structures.")
            else:
                st.error("Missing valid internal GPS coordinates or clear EXIF timestamps to determine solar azimuth calculations.")

            # --- 3. METADATA DISPLAY ---
            st.markdown("### 📂 Baseline Metadata Summary")
            make = exif_data.get(271, "Unknown") if exif_data else "Unknown"
            model = exif_data.get(272, "Unknown") if exif_data else "Unknown"
            display_date = dt_obj.strftime("%d/%m/%Y %H:%M:%S") if dt_obj else "Unknown"
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="📸 Capture Hardware Manufacturer", value=str(make))
                st.metric(label="📱 Hardware Model", value=str(model))
            with col2:
                st.metric(label="📅 Registered Acquisition Time", value=display_date)

            if lat and lon:
                st.markdown("### 📍 Location Verification Profile")
                loc_name = "Unavailable description context"
                if geolocator:
                    try:
                        location = geolocator.reverse((lat, lon), timeout=3)
                        if location: loc_name = location.address
                    except Exception: 
                        loc_name = "Lookup timeout exception triggered"
                st.text(f"{loc_name}\n({lat:.6f}, {lon:.6f})")

            # --- 4. DEEP ARTIFACT BOX ---
            with st.expander("➕ Deep Forensic Layers & Raw Metadata"):
                st.markdown("**Compression Verification Matrix (Error Level Analysis)**")
                ela_img = compute_ela(file_name)
                if ela_img:
                    st.image(ela_img, caption="Error Level Analysis Map", use_container_width=True)
                
                if exif_data:
                    exif_dict = {str(TAGS.get(t, t)): str(v) for t, v in exif_data.items()}
                    st.json(exif_dict)
                else:
                    st.write("No deep metadata structures accessible inside asset.")

        except Exception as e:
            st.error(f"Error handling deep asset extraction structure: {e}")
            
    elif zipfile.is_zipfile(file_name):
        st.success("📦 Zip Archive Detected")
        try:
            with zipfile.ZipFile(file_name, 'r') as z:
                st.metric(label="Total Contained Files", value=len(z.infolist()))
                with st.expander("➕ More Data / File Tree Structure"):
                    for info in z.infolist():
                        st.code(f"File: {info.filename}\nSize: {info.file_size} bytes")
        except Exception as e:
            st.error(f"Error reading zip: {e}")

    elif mime_type and any(t in mime_type for t in ['text', 'javascript', 'python', 'json']):
        st.success("📝 Code/Text File Detected")
        try:
            content = file_data.read().decode("utf-8", errors="ignore")
            st.metric(label="Total Code Lines", value=len(content.splitlines()))
            with st.expander("➕ More Data / View Source Code"):
                st.code(content, language=mime_type.split('/')[-1])
        except Exception as e:
            st.error(f"Error reading text: {e}")

    else:
        st.warning("⚠️ Unsupported format. Basic details below.")
        with st.expander("➕ More Data / System Properties"):
            st.write(f"Mime type: {mime_type}")
            st.write(f"File size: {os.path.getsize(file_name)} bytes")
        
    if os.path.exists(file_name):
        os.remove(file_name)

if uploaded_file is not None:
    investigate_file(uploaded_file, uploaded_file.name)
