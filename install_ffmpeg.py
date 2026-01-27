import os
import zipfile
import urllib.request
import sys
import shutil

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PROJECT_DIR, "bin")

def install_ffmpeg():
    print(f"Checking for FFmpeg in {BIN_DIR}...")
    
    if os.path.exists(os.path.join(BIN_DIR, "ffmpeg.exe")):
        print("✅ FFmpeg is already installed locally.")
        return

    if not os.path.exists(BIN_DIR):
        os.makedirs(BIN_DIR)

    zip_path = os.path.join(BIN_DIR, "ffmpeg.zip")
    
    print(f"⬇️ Downloading FFmpeg from {FFMPEG_URL}...")
    try:
        urllib.request.urlretrieve(FFMPEG_URL, zip_path)
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return

    print("📦 Extracting FFmpeg...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Find the bin folder inside the zip
            exe_files = [f for f in zip_ref.namelist() if f.endswith('ffmpeg.exe') or f.endswith('ffprobe.exe')]
            
            for file in exe_files:
                # Extract to temp, then move to BIN_DIR
                zip_ref.extract(file, BIN_DIR)
                
                # Move from subfolder to BIN_DIR root
                extracted_path = os.path.join(BIN_DIR, file)
                filename = os.path.basename(file)
                shutil.move(extracted_path, os.path.join(BIN_DIR, filename))
                
        print("✅ FFmpeg installed successfully!")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
    finally:
        # Cleanup
        if os.path.exists(zip_path):
            os.remove(zip_path)
        # Cleanup empty folders
        for root, dirs, files in os.walk(BIN_DIR, topdown=False):
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except:
                    pass

if __name__ == "__main__":
    install_ffmpeg()
