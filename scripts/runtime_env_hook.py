"""
Runtime hook to adjust search paths for the incremental bundle layout.

Ensures that DLL dependencies under ``runtime/`` are discoverable and that
modules placed in ``app/`` are importable before the bundled originals.
"""

import os
import sys
from pathlib import Path


def _add_dll_directory(path: Path) -> None:
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(path))
        except (FileNotFoundError, OSError):
            pass


def main() -> None:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))

    app_dir = base_dir / "app"
    if app_dir.exists():
        sys.path.insert(0, str(app_dir))

    runtime_dir = base_dir / "runtime"
    if runtime_dir.exists():
        os.environ["PATH"] = str(runtime_dir) + os.pathsep + os.environ.get("PATH", "")
        _add_dll_directory(runtime_dir)


main()
