"""
Runtime hook to fix Streamlit static file path in incremental bundle.

This hook ensures that Streamlit can find its static files in the correct location
within the incremental bundle structure.
"""

import os
import sys
from pathlib import Path


def _add_dll_directory(path: Path) -> None:
    """Add a directory to the DLL search path."""
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(path))
        except (FileNotFoundError, OSError):
            pass


def _fix_streamlit_static_path() -> None:
    """Fix Streamlit static file path for incremental bundle."""
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    
    # Check if we're in an incremental bundle
    app_streamlit_static = base_dir / "app" / "streamlit" / "static"
    if app_streamlit_static.exists():
        # Set environment variable to tell Streamlit where to find static files
        os.environ["STREAMLIT_STATIC_ROOT"] = str(app_streamlit_static)
        
        # Also check for the original static path and create a symlink if needed
        original_static = base_dir / "streamlit" / "static"
        if not original_static.exists():
            try:
                # Try to create a junction/symlink to the correct location
                if hasattr(os, "symlink"):
                    os.symlink(str(app_streamlit_static), str(original_static))
                elif sys.platform == "win32":
                    import subprocess
                    subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(original_static), str(app_streamlit_static)],
                        check=False,
                        capture_output=True
                    )
            except Exception:
                # If symlink creation fails, we'll rely on the environment variable
                pass


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