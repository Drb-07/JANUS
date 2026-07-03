import os
import io
import zipfile
import mimetypes
from datetime import datetime
import streamlit as st
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim

# NEW FORENSIC LIBRARIES
from transformers import pipeline
import torch
import pvlib
import pandas as pd

# Initialize models and geolocator safely
try:
    geolocator = Nominatim(user_agent="janus_adie_investigator_v3")
except Exception:
    geolocator = None

@st.cache_resource
def load_object_detector():
    try:
        # Lightweight open-source Object Detection pipeline
        return pipeline("object-detection", model="facebook/detr-resnet-50")
    except Exception:
        return None

detector = load_object_detector()

st.set_page_config(page_title="JANUS - ADIE Pro Ultra", page_icon="🔍", layout="centered")
st.title("🔍 JANUS - Advanced Deep Intelligence Engine")
st.subheader("Surroundings & Environmental Forensic Module")

uploaded_file = st.file_uploader("Upload target file for environmental scene scan...", type=None)

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

def calculate_sun_position(lat, lon, dt_object):
    """Calculates the exact sun angle based on coordinates and timestamps."""
    try:
        # Ensure timezone-aware datetime for accurate solar computation
        times = pd.DatetimeIndex([dt_object]).tz_localize('UTC')
        solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
        azimuth = solpos['azimuth'].values[0]
        apparent_elevation = solpos['apparent_elevation'].values[0]
        return azimuth, apparent_elevation
    except Exception:
        return None, None

def investigate_file(file_data, file_name):
    st.markdown(f"### --- Environmental Scene Analysis: `{file_name}` ---")
    
    with open(file_name, "wb") as f:
        f.write(file_data.getbuffer())
        
    mime_type, _ = mimetypes.guess_type(file_name)
    
    if mime_type and mime_type.startswith('image'):
        st.image(file_data, caption="Target Image Asset", use_container_width=True)
        
        try:
            img = Image.open(file_name)
            exif_data = img._getexif()
            
            # --- 1. CONTEXT ARCHITECTURE (WHAT IS IN THE IMAGE) ---
            st.markdown("### 👁️ Contextual Object Detection (AI Scan)")
            if detector:
                with st.spinner("Analyzing elements inside the photo..."):
                    predictions = detector(img)
                    if predictions:
                        detected_items = {}
                        for item in predictions:
                            label = item['label']
                            detected_items[label] = detected_items.get(label, 0) + 1
                        
                        # Render findings cleanly
                        for item_name, count in detected_items.items():
                            st.write(f" * Found **{count}x {item_name}**")
                            if "sign" in item_name or "traffic" in item_name:
                                st.warning("📌 **Verification Alert:** Potential traffic/road markers detected. Inspect visual frames closely for regional fonts or regulatory shields.")
                    else:
                        st.write("No distinct standard objects indexed by AI pipeline.")
            else:
                st.write("AI Computer Vision Engine offline.")

            # --- 2. CELESTIAL ANALYSIS (SUN ANGLE & SHADOWS) ---
            st.markdown("### ☀️ Celestial Surroundings Analysis")
            
            # Extract basic markers for math pipeline
            lat, lon = None, None
            gps_raw = get_gps_info(exif_data) if exif_data else None
            if gps_raw:
                lat, lon = get_lat_lon(gps_raw)
                
            raw_date = exif_data.get(36867) if exif_data else None
            dt_obj = None
            if raw_date:
                try:
                    dt_obj = datetime.strptime(str(raw_date).strip(), "%Y:%m:%d %H:%M:%S")
                except Exception:
                    pass
            
            # Math execution if baseline data elements exist
            if lat and lon and dt_obj:
                azimuth, elevation = calculate_sun_position(lat, lon, dt_obj)
                if azimuth and elevation:
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        st.metric(label="🧭 Sun Azimuth Angle", value=f"{azimuth:.2f}°")
                    with col_s2:
                        st.metric(label="📐 Sun Elevation Angle", value=f"{elevation:.2f}°")
                    
                    st.info(f"💡 **Shadow Analysis:** Based on an elevation of {elevation:.2f}°, shadows will be approximately **{1 / math.tan(math.radians(max(0.1, elevation))):.2f}x** the height of any vertical object.")
                else:
                    st.write("Could not calculate exact angles from provided metadata.")
            else:
                st.error("Missing GPS coordinates or valid EXIF digital time markers to generate solar trajectory data vectors.")

            # Dynamic regional lookups for signs/surroundings
            if gps_raw and lat and lon:
                st.markdown("### 🗺️ Infrastructure & Regional Context")
                loc_name = "Unknown Location Description"
                if geolocator:
                    try:
                        location = geolocator.reverse((lat, lon), timeout=3)
                        if location: 
                            loc_name = location.address
                            # Check address fields for infrastructure hints
                            st.write(f"**Identified Roadway System:** {loc_name}")
                            st.caption("Cross-reference any visible street signs against standard regional configurations matching this locality.")
                    except Exception: 
                        st.write("Location lookup timed out.")

        except Exception as e:
            st.error(f"Error executing forensic analysis sequence: {e}")
            
    if os.path.exists(file_name):
        os.remove(file_name)

if uploaded_file is not None:
    investigate_file(uploaded_file, uploaded_file.name)
