import os
import zipfile
import mimetypes
from datetime import datetime
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim

# Initialize geolocator safely
try:
    geolocator = Nominatim(user_agent="janus_adie_investigator_v1")
except Exception:
    geolocator = None

# UI Header Configuration
st.set_page_config(page_title="JANUS - ADIE", page_icon="🔍", layout="centered")
st.title("🔍 JANUS - Advanced Deep Intelligence Engine")
st.subheader("Core Investigator Module")

uploaded_file = st.file_uploader("Choose a file to investigate...", type=None)

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

def investigate_file(file_data, file_name):
    st.markdown(f"### --- Analysis: `{file_name}` ---")
    
    with open(file_name, "wb") as f:
        f.write(file_data.getbuffer())
        
    mime_type, _ = mimetypes.guess_type(file_name)
    
    if mime_type and mime_type.startswith('image'):
        st.image(file_data, caption=file_name, use_container_width=True)
        
        try:
            img = Image.open(file_data)
            exif_data = img._getexif()
            
            # Format Date and Time safely
            raw_date = exif_data.get(36867) if exif_data else None
            formatted_date = "Unknown"
            if raw_date:
                try:
                    dt_obj = datetime.strptime(str(raw_date), "%Y:%m:%d %H:%M:%S")
                    formatted_date = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    formatted_date = str(raw_date)

            # Location processing
            gps_raw = get_gps_info(exif_data) if exif_data else None
            location_display = "Not Found"
            
            if gps_raw:
                lat, lon = get_lat_lon(gps_raw)
                if lat and lon:
                    location_name = "Unknown Location Description"
                    if geolocator:
                        try:
                            location = geolocator.reverse((lat, lon), timeout=3)
                            if location:
                                location_name = location.address
                        except Exception:
                            location_name = "Lookup Timeout"
                    location_display = f"{location_name}\n({lat:.6f}, {lon:.6f})"

            make = exif_data.get(271, "Unknown") if exif_data else "Unknown"
            model = exif_data.get(272, "Unknown") if exif_data else "Unknown"
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="📸 Camera/Phone Company", value=str(make))
                st.metric(label="📱 Model", value=str(model))
            with col2:
                st.metric(label="📅 Date and Time", value=formatted_date)
                
            st.markdown("### 📍 GPS Location")
            st.text(location_display)
            
            with st.expander("➕ More Data / Raw Metadata Dump"):
                if exif_data:
                    exif_dict = {str(TAGS.get(t, t)): str(v) for t, v in exif_data.items()}
                    st.json(exif_dict)
                else:
                    st.write("No deep EXIF metadata available.")
                    
        except Exception as e:
            st.error(f"Error parsing image metadata: {e}")
            
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
