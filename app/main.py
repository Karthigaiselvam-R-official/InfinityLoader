from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
import asyncio
import uuid
import shutil
import os
import sys
import subprocess
from .downloader import run_download, download_status

app = FastAPI()

# Mount static folder
base_dir = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(base_dir, "../static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.on_event("startup")
async def startup_check():
    """Checks if FFmpeg is available."""
    system_ffmpeg = shutil.which("ffmpeg")
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    project_root = os.path.dirname(current_dir) 
    local_ffmpeg = os.path.join(project_root, 'bin', 'ffmpeg.exe')

    if not system_ffmpeg and not os.path.exists(local_ffmpeg):
        print("WARNING: FFmpeg NOT FOUND. Conversions will fail.")
    else:
        print(f"[OK] FFmpeg detected.")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(static_path, 'index.html'))

@app.get("/api/choose-path")
def choose_path():
    """
    Opens the native folder picker.
    Prioritizes 'zenity' on Linux for a better UI.
    """
    try:
        path = None
        
        # Check for Zenity (Linux/GNOME native-like dialog)
        zenity_path = shutil.which("zenity")
        
        if zenity_path:
            try:
                # Zenity command for directory selection
                result = subprocess.run(
                    [zenity_path, "--file-selection", "--directory", "--title=Select Download Folder"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    path = result.stdout.strip()
            except Exception as e:
                print(f"Zenity failed: {e}")

        # Fallback to existing methods ONLY if Zenity is missing
        # (If Zenity was used but user cancelled, we do NOT want to open the old dialog)
        if not zenity_path:
            if os.name == 'nt':
                # --- WINDOWS STRATEGY: Python Tkinter (More Robust than PowerShell) ---
                # We run a tiny isolated script to open the dialog.
                script = """
import tkinter as tk
from tkinter import filedialog
import sys

try:
    # Create invisible root window
    root = tk.Tk()
    root.withdraw() 
    
    # Make it topmost so it detects focus
    root.attributes('-topmost', True)
    
    # Open Directory Picker
    path = filedialog.askdirectory(title="Select Download Folder")
    
    if path:
        print(path)
        
    root.destroy()
except Exception as e:
    pass
"""
                # Run the script in a separate python process
                # CRITICAL FIX: capture_output=True ensures we keep stdout (path) and stderr (warnings) separate.
                # We only want the path from stdout.
                proc = subprocess.run(
                    [sys.executable, "-c", script], 
                    capture_output=True,
                    text=True,
                    creationflags=0x08000000 # Hide console window
                )
                
                # Print stderr to console for debugging, but don't include it in 'path'
                if proc.stderr:
                    print(f"[DEBUG] Picker stderr: {proc.stderr.strip()}")
                    
                path = proc.stdout.strip()
                print(f"[DEBUG] Folder selected: {path}")

            else:
                # --- MAC/LINUX STRATEGY: Python Tkinter ---
                script = """
import tkinter as tk
from tkinter import filedialog
import os
try:
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()
    p = filedialog.askdirectory()
    if p: print(p)
    root.destroy()
except: pass
"""
                result = subprocess.check_output(
                    [sys.executable, "-c", script], 
                    stderr=subprocess.DEVNULL
                )
                path = result.decode().strip()

        if path:
            # Fix slashes for consistency
            clean_path = path.replace('\\', '/')
            return {"path": clean_path}
        else:
            return {"path": "Default"}
            
    except Exception as e:
        print(f"Dialog Error: {e}")
        return {"path": "Default"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # We maintain tasks here if we want to cancel them, but for now simple handling
    active_tasks = [] 
    
    try:
        while True:
            # Wait for any message from the client
            data = await websocket.receive_json()
            action = data.get("action", "download")
            
            if action == "fetch_info":
                # --- FETCH MODES ---
                await websocket.send_json({"state": "fetching", "message": "Analyzing URL..."})
                
                # Import here to avoid circular dependency issues if any
                from .downloader import fetch_formats
                
                url = data.get("url")
                if not url:
                    await websocket.send_json({"status": "error", "message": "No URL provided"})
                    continue

                result = await run_in_threadpool(fetch_formats, url)
                await websocket.send_json(result)
                
            elif action == "download":
                # --- DOWNLOAD MODE ---
                url = data.get("url")
                format_id = data.get("format_id", "best") 
                dl_path = data.get("download_path", "Default")
                
                task_id = str(uuid.uuid4())
                
                # Start download in a separate task so we don't block the loop
                # However, we also want to send status updates.
                # The original code had a while loop monitoring 'download_status'.
                # We can launch a monitor task effectively.
                
                async def monitor_download(tid):
                    while True:
                        if tid in download_status:
                            current_status = download_status[tid]
                            try:
                                await websocket.send_json(current_status)
                            except:
                                break
                            if current_status["state"] in ["completed", "error"]:
                                break
                        await asyncio.sleep(0.2)
                    # Cleanup
                    if tid in download_status:
                        del download_status[tid]

                # 1. Start the actual download
                asyncio.create_task(
                    run_in_threadpool(run_download, url, format_id, task_id, dl_path)
                )
                
                # 2. Start the monitor
                asyncio.create_task(monitor_download(task_id))

    except Exception as e:
        print(f"WS Error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass