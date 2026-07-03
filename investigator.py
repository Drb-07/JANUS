import os
import io
import zipfile
import mimetypes
from datetime import datetime
import streamlit as st
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim

# Initialize geolocator safely
try:
    geolocator = Nominatim(user_agent="janus_adie_investigator_v2")
except Exception:
    geolocator = None

st.set_page_config(page_title="JANUS - ADIE Pro", page_icon="🔍", layout="centered")
st.title("🔍 JANUS - Advanced Deep Intelligence Engine")
st.subheader("Forensic-Grade Investigator Module")

uploaded_file = st.file_uploader("Upload target file for forensic deep scan...", type=None)

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
        return "Unknown"
    try:
        dt_obj = datetime.strptime(str(raw_date).strip(), "%Y:%m:%d %H:%M:%S")
        return dt_obj.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(raw_date)

def compute_ela(img_path, quality=95):
    """Generates Error Level Analysis (ELA) to spotlight digital manipulation."""
    try:
        original = Image.open(img_path).convert('RGB')
        
        # Resave at fixed compression quality
        tmp_resaved = "tmp_resaved.jpg"
        original.save(tmp_resaved, 'JPEG', quality=quality)
        resaved_im = Image.open(tmp_resaved)
        
        # Calculate pixel variance
        diff = ImageChops.difference(original, resaved_im)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
        
        scale = 255.0 / max_diff
        enhanced_diff = ImageEnhance.Brightness(diff).enhance(scale)
        
        # Cleanup
        resaved_im.close()
        if os.path.exists(tmp_resaved):
            os.remove(tmp_resaved)
            
        return enhanced_diff
    except Exception as e:
        return None

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
            
            # 1. Primary Identifiers
            make = exif_data.get(271, "Unknown") if exif_data else "Unknown"
            model = exif_data.get(272, "Unknown") if exif_data else "Unknown"
            date_orig = format_exif_date(exif_data.get(36867)) if exif_data else "Unknown"
            
            # 2. GPS Location
            gps_raw = get_gps_info(exif_data) if exif_data else None
            location_display = "Not Found"
            if gps_raw:
                lat, lon = get_lat_lon(gps_raw)
                if lat and lon:
                    loc_name = "Unknown Location Description"
                    if geolocator:
                        try:
                            location = geolocator.reverse((lat, lon), timeout=3)
                            if location: loc_name = location.address
                        except Exception: loc_name = "Lookup Timeout"
                    location_display = f"{loc_name}\n({lat:.6f}, {lon:.6f})"

            # Core Presentation Metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="📸 Camera/Phone Company", value=str(make))
                st.metric(label="📱 Model", value=str(model))
            with col2:
                st.metric(label="📅 Date and Time", value=date_orig)
                
            st.markdown("### 📍 GPS Location")
            st.text(location_display)
            
            # --- ADVANCED FORENSIC EXTRACTION ENGINE ---
            st.markdown("### 🧬 Advanced Forensic Indicators")
            
            # A. Cross-Timeline Auditing
            date_digitized = format_exif_date(exif_data.get(36868)) if exif_data else "Unknown"
            date_modified = format_exif_date(exif_data.get(306)) if exif_data else "Unknown"
            
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.write(f"**Digitized Timeline:** {date_digitized}")
            with t_col2:
                st.write(f"**Software Modification Time:** {date_modified}")
                
            # B. Hardware Signatures
            serial_num = exif_data.get(42033, "Not Found") if exif_data else "Not Found"
            lens_spec = exif_data.get(42036, "Not Found") if exif_data else "Not Found"
            software_used = exif_data.get(305, "Camera Internal Firmware") if exif_data else "Unknown"
            
            st.write(f"**Device Serial Fingerprint:** `{serial_num}`")
            st.write(f"**Lens Profile:** `{lens_spec}`")
            st.write(f"**Software Environment:** `{software_used}`")
            
            # C. Hidden Embedded Thumbnail Recovery
            if exif_data and 5097 in exif_data:
                st.info("⚠️ Embedded EXIF Thumbnail Artifact Discovered!")
                try:
                    thumb_bytes = exif_data[5097]
                    st.image(io.BytesIO(thumb_bytes), caption="Recovered Embedded Background Thumbnail", width=150)
                except Exception:
                    st.write("Could not render found thumbnail data block.")

            # D. Adobe XMP & IPTC String Hunt
            st.markdown("**Structural String Markers (XMP / History Trails)**")
            xmp_found = False
            if hasattr(img, 'info'):
                for k, v in img.info.items():
                    if 'xmp' in str(k).lower() or 'xml' in str(k).lower():
                        xmp_found = True
                        st.text_area(f"Extracted Raw Layer [{k}]", str(v)[:2000], height=150)
            if not xmp_found:
                st.caption("No custom structural XMP/Adobe transaction wrappers identified.")

            # E. Pixel Error Level Analysis (ELA) Visualizer
            st.markdown("**Pixel Manipulation Matrix (Error Level Analysis)**")
            with st.spinner("Calculating pixel compression discrepancies..."):
                ela_img = compute_ela(file_name)
                if ela_img:
                    st.image(ela_img, caption="ELA Output Map (Bright spots indicate non-uniform pixel saves)", use_container_width=True)
                else:
                    st.caption("Unable to construct ELA baseline arrays.")

            # Raw Deep Dump Box
            with st.expander("➕ More Data / Raw Metadata Dump"):
                if exif_data:
                    exif_dict = {str(TAGS.get(t, t)): str(v) for t, v in exif_data.items()}
                    st.json(exif_dict)
                else:
                    st.write("No deep metadata tags available.")
                    
        except Exception as e:
            st.error(f"Error executing forensic sequence: {e}")
            
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
