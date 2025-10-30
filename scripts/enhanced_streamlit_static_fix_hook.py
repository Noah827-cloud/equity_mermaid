"""
Enhanced runtime hook to fix Streamlit static file path in PyInstaller bundle.

This hook ensures that Streamlit can find its static files in the correct location
within the PyInstaller bundle structure.
"""

import os
import sys
import shutil
from pathlib import Path


def _add_dll_directory(path: Path) -> None:
    """Add a directory to the DLL search path."""
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(path))
        except (FileNotFoundError, OSError):
            pass


def _fix_streamlit_static_path() -> None:
    """Fix Streamlit static file path for PyInstaller bundle."""
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    
    # Check if we're in a PyInstaller bundle
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


def main() -> None:
    """Main hook function."""
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))

    # Add app directory to Python path
    app_dir = base_dir / "app"
    if app_dir.exists():
        sys.path.insert(0, str(app_dir))

    # Add runtime directory to PATH and DLL search path
    runtime_dir = base_dir / "runtime"
    if runtime_dir.exists():
        os.environ["PATH"] = str(runtime_dir) + os.pathsep + os.environ.get("PATH", "")
        _add_dll_directory(runtime_dir)
    
    # Fix Streamlit static file path
    _fix_streamlit_static_path()


if __name__ == "__main__":
    main()
else:
    main()