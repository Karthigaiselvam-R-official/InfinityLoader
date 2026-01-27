import uvicorn
import os
import sys
import importlib.util

def setup_package():
    """
    Ensures the 'app' folder is treated as a Python package
    by creating an __init__.py if it's missing.
    """
    if os.path.exists("app") and not os.path.exists("app/__init__.py"):
        print("⚙️  Creating missing app/__init__.py...")
        with open("app/__init__.py", "w") as f:
            f.write("")

def pre_check_imports():
    """
    Diagnoses the project structure and finds the correct main file.
    """
    # 1. Check Root
    if os.path.exists("main.py"):
        print("[OK] Found main.py in root folder.")
        return "main:app"
        
    # 2. Check App Folder (Your case)
    elif os.path.exists("app/main.py"):
        print("[OK] Found main.py inside 'app' folder.")
        # Ensure it's a valid package
        setup_package()
        return "app.main:app"
        
    else:
        print("\n[ERROR] CRITICAL: File 'main.py' not found!")
        print(f"Searched in: {os.getcwd()}")
        print("Please ensure 'main.py' is in this folder or inside 'app/'.\n")
        return None

if __name__ == "__main__":
    # Ensure current directory is in Python path so imports work
    sys.path.insert(0, os.getcwd())

    print("Starting YouTube Downloader Server...")
    
    # 1. Find the app
    app_string = pre_check_imports()

    # 2. Create downloads folder if missing
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    if app_string:
        print("Open http://127.0.0.1:8000 in your browser")
        try:
            # Start Uvicorn with the dynamically found app string
            uvicorn.run(app_string, host="127.0.0.1", port=8000, reload=True)
        except KeyboardInterrupt:
            print("\nServer stopped by user.")
        except Exception as e:
            print(f"\n❌ Error starting server: {e}")
    else:
        print("\nServer could not start due to missing files.")