import os
import zipfile
import mimetypes
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS

# 1. UI Header Configuration
st.set_page_config(page_title="JANUS - ADIE", page_icon="🔍", layout="centered")
st.title("🔍 JANUS - Advanced Deep Intelligence Engine")
st.subheader("Core Investigator Module")
st.write("Upload a file, archive, or image to extract hidden metadata and structural anomalies.")

# 2. File Uploader Component
uploaded_file = st.file_uploader("Choose a file to investigate...", type=None)

def investigate_file(file_data, file_name):
    st.markdown(f"### --- Investigating: `{file_name}` ---")
    
    # Save a temporary copy to read sizes/mimetypes accurately
    with open(file_name, "wb") as f:
        f.write(file_data.getbuffer())
        
    mime_type, _ = mimetypes.guess_type(file_name)
    st.metric(label="Detected Mime Type", value=str(mime_type))
    st.metric(label="File Size", value=f"{os.path.getsize(file_name)} bytes")

    # 1. Archive Investigation (ZIP)
    if zipfile.is_zipfile(file_name):
        st.warning("[!] Archive Detected. Extracting hidden structure:")
        with zipfile.ZipFile(file_name, 'r') as z:
            for info in z.infolist():
                st.code(f"File: {info.filename}\nCompressed: {info.compress_size} bytes\nSystem: {info.create_system}")
    
    # 2. Image Metadata Investigation (EXIF)
    elif mime_type and mime_type.startswith('image'):
        st.info("[!] Image Detected. Extracting EXIF Metadata:")
        st.image(file_data, caption=file_name, use_container_width=True)
        try:
            img = Image.open(file_data)
            exif_data = img._getexif()
            if exif_data:
                exif_dict = {}
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)
                    exif_dict[str(tag_name)] = str(value)
                st.json(exif_dict)
            else:
                st.write(" -> No standard EXIF data found.")
        except Exception as e:
            st.error(f"Error reading EXIF: {e}")
            
    # 3. Code/Text Investigation
    elif mime_type and ('text' in mime_type or 'javascript' in mime_type or 'python' in mime_type or 'json' in mime_type):
        st.info("[!] Code/Text File Detected.")
        content = file_data.read().decode("utf-8", errors="ignore")
        st.metric(label="Total Lines", value=len(content.splitlines()))
        st.code(content, language=mime_type.split('/')[-1])

    else:
        st.error("[?] Binary or unsupported format. Requires external specialized deep inspection tools.")
        
    # Clean up temp file
    if os.path.exists(file_name):
        os.remove(file_name)

# Trigger investigation upon upload
if uploaded_file is not None:
    investigate_file(uploaded_file, uploaded_file.name)
