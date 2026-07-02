import os
import zipfile
import mimetypes
from PIL import Image
from PIL.ExifTags import TAGS

def investigate_file(file_path):
    print(f"--- Investigating: {os.path.basename(file_path)} ---")
    mime_type, _ = mimetypes.guess_type(file_path)
    print(f"Mime Type: {mime_type}")
    print(f"File Size: {os.path.getsize(file_path)} bytes\n")

    # 1. Archive Investigation (ZIP)
    if zipfile.is_zipfile(file_path):
        print("[!] Archive Detected. Extracting hidden structure:")
        with zipfile.ZipFile(file_path, 'r') as z:
            for info in z.infolist():
                print(f" -> File: {info.filename} | Compressed: {info.compress_size} bytes | System: {info.create_system}")
    
    # 2. Image Metadata Investigation (EXIF)
    elif mime_type and mime_type.startswith('image'):
        print("[!] Image Detected. Extracting EXIF Metadata:")
        try:
            img = Image.open(file_path)
            exif_data = img._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)
                    print(f" -> {tag_name}: {value}")
            else:
                print(" -> No standard EXIF data found.")
        except Exception as e:
            print(f" -> Error reading EXIF: {e}")
            
    # 3. Code/Text Investigation (Basic check)
    elif mime_type and ('text' in mime_type or 'javascript' in mime_type or 'python' in mime_type):
        print("[!] Code/Text File Detected.")
        with open(file_path, 'r', errors='ignore') as f:
            lines = f.readlines()
            print(f" -> Total Lines: {len(lines)}")
            # Future: Add AST parsing or regex for hidden API keys/secrets

    else:
        print("[?] Binary or unsupported format. Requires external specialized deep inspection tools.")

# Example execution:
# investigate_file("test_photo.jpg")
