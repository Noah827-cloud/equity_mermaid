"""
Runtime fix for Streamlit static files in PyInstaller bundle.

This module should be imported at the beginning of the main application
to ensure Streamlit can find its static files.
"""

import os
import sys
import shutil
from pathlib import Path


def fix_streamlit_static_files():
    """Fix Streamlit static file path for PyInstaller bundle at runtime."""
    # Get the base directory (PyInstaller temp directory or regular directory)
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent.parent
    
    # Check if we're in a PyInstaller bundle with the expected structure
    app_streamlit_static = base_dir / "app" / "streamlit" / "static"
    if app_streamlit_static.exists():
        # Create the expected static path if it doesn't exist
        expected_static = base_dir / "streamlit" / "static"
        expected_static.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy static files if they don't exist or if they're outdated
        if not expected_static.exists() or not (expected_static / "index.html").exists():
            print(f"Copying Streamlit static files from {app_streamlit_static} to {expected_static}")
            if expected_static.exists():
                shutil.rmtree(expected_static)
            shutil.copytree(app_streamlit_static, expected_static)
        
        # Set environment variable to tell Streamlit where to find static files
        os.environ["STREAMLIT_STATIC_ROOT"] = str(expected_static)
        
        # Also set the STREAMLIT_SERVER_STATIC_PATH environment variable
        os.environ["STREAMLIT_SERVER_STATIC_PATH"] = str(expected_static)
        
        # Add the expected static directory to sys.path
        if str(expected_static.parent) not in sys.path:
            sys.path.insert(0, str(expected_static.parent))
        
        return True
    return False


def apply_fix():
    """Apply the Streamlit static file fix."""
    try:
        if fix_streamlit_static_files():
            print("Streamlit static file fix applied successfully.")
        else:
            print("Streamlit static file fix not needed or failed.")
    except Exception as e:
        print(f"Error applying Streamlit static file fix: {e}")


# Apply the fix immediately when the module is imported
apply_fix()