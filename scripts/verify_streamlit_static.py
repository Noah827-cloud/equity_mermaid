#!/usr/bin/env python3
"""
Post-build verification script for Streamlit static files in incremental bundle.

This script checks if Streamlit static files are correctly placed in the incremental
bundle and creates necessary symlinks if needed.
"""

import os
import sys
import shutil
from pathlib import Path


def check_streamlit_static_files(dist_dir: Path) -> bool:
    """Check if Streamlit static files are correctly placed."""
    app_streamlit_static = dist_dir / "app" / "streamlit" / "static"
    streamlit_static = dist_dir / "streamlit" / "static"
    
    # Check if static files exist in app/streamlit/static
    if not app_streamlit_static.exists():
        print(f"ERROR: Streamlit static files not found at {app_streamlit_static}")
        return False
    
    # Check if index.html exists
    index_html = app_streamlit_static / "index.html"
    if not index_html.exists():
        print(f"ERROR: Streamlit index.html not found at {index_html}")
        return False
    
    print(f"OK: Streamlit static files found at {app_streamlit_static}")
    
    # Create symlink at streamlit/static if it doesn't exist
    if not streamlit_static.exists():
        try:
            if sys.platform == "win32":
                import subprocess
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(streamlit_static), str(app_streamlit_static)],
                    check=True,
                    capture_output=True
                )
                print(f"OK: Created junction link from {streamlit_static} to {app_streamlit_static}")
            else:
                streamlit_static.symlink_to(app_streamlit_static)
                print(f"OK: Created symlink from {streamlit_static} to {app_streamlit_static}")
        except Exception as e:
            print(f"WARNING: Could not create symlink: {e}")
            print("Streamlit will rely on environment variable to find static files")
    
    return True


def main():
    """Main function."""
    if len(sys.argv) > 1:
        dist_dir = Path(sys.argv[1])
    else:
        # Default to the standard incremental distribution directory
        script_dir = Path(__file__).parent
        dist_dir = script_dir.parent / "dist" / "equity_mermaid_tool_incremental"
    
    if not dist_dir.exists():
        print(f"ERROR: Distribution directory not found: {dist_dir}")
        return 1
    
    print(f"Verifying Streamlit static files in {dist_dir}")
    
    if check_streamlit_static_files(dist_dir):
        print("Streamlit static files verification completed successfully")
        return 0
    else:
        print("Streamlit static files verification failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())