import yt_dlp
import os
import shutil
from pathlib import Path

# Shared dictionary
download_status = {}

class MyLogger:
    def debug(self, msg):
        pass
    def info(self, msg):
        pass
    def warning(self, msg):
        ignore_keywords = ["PO Token", "JavaScript runtime", "SABR", "missing a url"]
        if not any(k in msg for k in ignore_keywords):
            print(f"[WARNING] {msg}")
    def error(self, msg):
        print(f"[ERROR] {msg}")

def get_ffmpeg_path():
    """
    Smartly finds FFmpeg.
    1. Checks the project 'bin' folder (OS aware).
    2. Checks the system PATH.
    """
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Determine binary name based on OS
    if os.name == 'nt':
        bin_name = 'ffmpeg.exe'
    else:
        bin_name = 'ffmpeg'

    local_bin = os.path.join(project_dir, 'bin', bin_name)
    
    # Check local bin first
    if os.path.exists(local_bin):
        # On Linux/Mac, ensure it's executable
        if os.name != 'nt' and not os.access(local_bin, os.X_OK):
             pass # Not executable, fallback
        else:
             return local_bin
    
    # Check system PATH
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg:
        return system_ffmpeg
        
    return None

def progress_hook(d, task_id):
    if d['status'] == 'downloading':
        # Clean ANSI colors logic
        p = d.get('_percent_str', '0%').replace('\x1b[0;94m', '').replace('\x1b[0m', '')
        if task_id in download_status:
            download_status[task_id].update({
                "state": "processing",
                "message": f"Downloading: {p}",
                "filename": d.get('filename', 'unknown')
            })
    elif d['status'] == 'finished':
        if task_id in download_status:
            download_status[task_id].update({
                "state": "converting",
                "message": "Download complete. Processing/Converting...",
            })

def fetch_formats(url: str):
    """
    Fetches available formats for a given URL without downloading.
    Returns a dictionary with video info and sorted format lists.
    """
    print(f"[DEBUG] Fetching formats for: {url}")
    ffmpeg_path = get_ffmpeg_path()
    opts = {
        'quiet': False, # Enabled logs to debug "Infinite Loading"
        'ffmpeg_location': ffmpeg_path,
        'noplaylist': True,
        'logger': MyLogger(),
    }
    
    try:
        print("[DEBUG] Starting yt-dlp extraction...")
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print("[DEBUG] Extraction successful!")
            
            formats = info.get('formats', [])
            video_formats = []
            audio_formats = []
            
            # Filter duplicates: Keep best bitrate for each Resolution + Container combo
            unique_videos = {} # Key: (height, ext) -> format_dict
            
            for f in formats:
                # Format Size (estimate if None)
                filesize = f.get('filesize') or f.get('filesize_approx')
                size_str = f"{filesize / 1024 / 1024:.1f} MB" if filesize else "N/A"
                filesize_val = filesize or 0
                
                # Audio extraction
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_formats.append({
                        'format_id': f['format_id'],
                        'ext': f['ext'],
                        'quality': f.get('abr', 0) or 0, # Audio bitrate
                        'note': f"{(f.get('abr') or 0):.0f}kbps",
                        'size': size_str,
                        'filesize_bytes': filesize_val
                    })
                
                # Video extraction
                elif f.get('vcodec') != 'none':
                    height = f.get('height') or 0
                    if height >= 144: # Ignore super low quality thumbnail streams
                        note = f.get('format_note', '')
                        ext = f['ext']
                        
                        # Create candidate object
                        candidate = {
                            'format_id': f['format_id'],
                            'ext': ext,
                            'quality': f"{height}p",
                            'height': height,
                            'note': note,
                            'size': size_str,
                            'filesize_bytes': filesize_val
                        }
                        
                        key = (height, ext)
                        
                        # Logic: Prefer larger filesize (usually indicates higher bitrate/quality)
                        # If current key exists, compare
                        if key in unique_videos:
                            prev = unique_videos[key]
                            if candidate['filesize_bytes'] > prev['filesize_bytes']:
                                unique_videos[key] = candidate
                            # If sizes are equal or 0, maybe prefer 'avc1' (h264) for mp4? for now size is good proxy.
                        else:
                            unique_videos[key] = candidate

            # Convert dict back to list
            video_formats = list(unique_videos.values())

            # Sort formats
            audio_formats.sort(key=lambda x: x['filesize_bytes'], reverse=True)
            video_formats.sort(key=lambda x: x['height'], reverse=True)

            return {
                "status": "success",
                "id": info.get('id'),
                "title": info.get('title', 'Unknown'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration_string', ''),
                "author": info.get('uploader', ''),
                "formats": {
                    "video": video_formats,
                    "audio": audio_formats
                }
            }
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_download(url: str, format_id: str, task_id: str, download_path: str = "Default"):
    """
    Downloads a specific format ID.
    If format_id is 'best_audio', it downloads best audio and converts to mp3.
    """
    # 1. Initialize Status
    download_status[task_id] = {"state": "starting", "message": "Initializing..."}
    
    ffmpeg_path = get_ffmpeg_path()
    
    # Common Options
    opts = {
        'quiet': True,
        'ffmpeg_location': ffmpeg_path,
        'noplaylist': True,
        'progress_hooks': [lambda d: progress_hook(d, task_id)],
        'logger': MyLogger(),
        'overwrites': True,
    }

    # Determine Output Folder
    # Determine Output Folder
    if download_path == "Default" or not os.path.exists(download_path):
        # User requested System Download Folder (Requirement: ~/Downloads/Youtube Download)
        base_folder = os.path.join(Path.home(), "Downloads", "Youtube Download")
        # Ensure it exists
        os.makedirs(base_folder, exist_ok=True)
    else:
        base_folder = download_path

    opts['outtmpl'] = os.path.join(base_folder, "%(title)s.%(ext)s")

    # Format Logic
    if format_id == "best_audio":
        # Convert to MP3 high quality
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        # Specific Format Download
        # If it's a video, we fetch that video format + best audio and merge
        opts['format'] = f"{format_id}+bestaudio/best"
        opts['merge_output_format'] = 'mp4' # Default container

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Extension fix for Audio (if post-processed)
            if format_id == "best_audio":
                base, _ = os.path.splitext(filename)
                filename = f"{base}.mp3"
            
            display_name = os.path.basename(filename)

            download_status[task_id] = {
                "state": "completed", 
                "message": "Done!", 
                "file_path": filename,
                "filename": display_name
            }
            
    except Exception as e:
        # Retry with just the format_id if merge fails (fallback)
        try:
             print(f"Merge failed, trying direct download: {e}")
             opts['format'] = format_id
             with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                download_status[task_id] = {
                    "state": "completed", "message": "Done (Direct)", "filename": "video"
                }
        except Exception as e2:
            download_status[task_id] = {"state": "error", "message": str(e2)}