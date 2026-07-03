import os
import zipfile
import mimetypes
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

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

def investigate_file(file_data, file_name):
    st.markdown(f"### --- Analysis: `{file_name}` ---")
    
    with open(file_name, "wb") as f:
        f.write(file_data.getbuffer())
        
    mime_type, _ = mimetypes.guess_type(file_name)
    
    # --- IMAGE CODEPATH ---
    if mime_type and mime_type.startswith('image'):
        st.image(file_data, caption=file_name, use_container_width=True)
        
        try:
            img = Image.open(file_data)
            exif_data = img._getexif()
            
            # Extract Main High-Priority Data
            make = exif_data.get(271, "Unknown") if exif_data else "Unknown"    # Camera Make
            model = exif_data.get(272, "Unknown") if exif_data else "Unknown"   # Camera Model
            date_time = exif_data.get(36867, "Unknown") if exif_data else "Unknown" # Original Date/Time
            gps_raw = get_gps_info(exif_data) if exif_data else None
            
            # Display Main Data cleanly
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="📸 Camera/Phone Company", value=str(make))
                st.metric(label="📱 Model", value=str(model))
            with col2:
                st.metric(label="📅 Date and Time", value=str(date_time))
                st.metric(label="📍 GPS Location Data", value="Available" if gps_raw else "Not Found")
            
            # Dump everything else into a hidden "More Data" section
            with st.expander("➕ More Data / Raw Metadata Dump"):
                if exif_data:
                    exif_dict = {}
                    for tag, value in exif_data.items():
                        tag_name = TAGS.get(tag, tag)
                        exif_dict[str(tag_name)] = str(value)
                    st.json(exif_dict)
                else:
                    st.write("No deep EXIF metadata available.")
                    
        except Exception as e:
            st.error(f"Error reading EXIF: {e}")
            
    # --- ARCHIVE CODEPATH ---
    elif zipfile.is_zipfile(file_name):
        st.success("📦 Zip Archive Detected")
        # Main Data Summary
        with zipfile.ZipFile(file_name, 'r') as z:
            st.metric(label="Total Contained Files", value=len(z.infolist()))
            
            # Hidden details
            with st.expander("➕ More Data / File Tree Structure"):
                for info in z.infolist():
                    st.code(f"File: {info.filename}\nSize: {info.file_size} bytes\nCompressed: {info.compress_size} bytes")

    # --- CODE / TEXT CODEPATH ---
    elif mime_type and ('text' in mime_type or 'javascript' in mime_type or 'python' in mime_type or 'json' in mime_type):
        st.success("📝 Code/Text File Detected")
        content = file_data.read().decode("utf-8", errors="ignore")
        st.metric(label="Total Code Lines", value=len(content.splitlines()))
        
        with st.expander("➕ More Data / View Source Code"):
            st.code(content, language=mime_type.split('/')[-1])

    else:
        st.error("⚠️ Deep inspection tools required for this file format.")
        with st.expander("➕ More Data / System Properties"):
            st.write(f"Mime type: {mime_type}")
            st.write(f"File size: {os.path.getsize(file_name)} bytes")
        
    if os.path.exists(file_name):
        os.remove(file_name)

if uploaded_file is not None:
    investigate_file(uploaded_file, uploaded_file.name)
