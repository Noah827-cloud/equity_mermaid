# -*- mode: python ; coding: utf-8 -*-
"""
Slim variant of the incremental spec.

It reuses the same layout (app/ + runtime/ + hooks) so that downstream
incremental/patch tooling continues to work, but narrows binary/data
inputs to what the .venv actually needs.
"""

import os
import sys
from pathlib import Path


from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

current_dir = os.getcwd()
APP_ROOT = "app"
RUNTIME_ROOT = "runtime"


def _prefix_items(items, prefix):
    prefixed = []
    for src_path, target_path in items:
        normalized_target = target_path or "."
        combined = os.path.normpath(os.path.join(prefix, normalized_target))
        prefixed.append((src_path, combined))
    return prefixed


# Use files from the active interpreter (expected to be the .venv python)
python_base = Path(sys.base_prefix)
python_dlls = python_base / "DLLs"
python_bin = python_base / "Library" / "bin"

def _existing_items(items):
    present = []
    for src, target in items:
        path = Path(src)
        if path.exists():
            present.append((path, target))
        else:
            print(f"[WARN] Missing binary skipped: {path}")
    return present


required_dll_candidates = [
    (python_dlls / "_sqlite3.pyd", "."),
    (python_dlls / "_hashlib.pyd", "."),
    (python_dlls / "_ssl.pyd", "."),
    (python_dlls / "_bz2.pyd", "."),
    (python_dlls / "_lzma.pyd", "."),
    (python_dlls / "_ctypes.pyd", "."),
    (python_dlls / "pyexpat.pyd", "."),
    (python_dlls / "_elementtree.pyd", "."),
    (python_bin / "ffi-8.dll", "."),
    (python_bin / "ffi.dll", "."),
    (python_bin / "libexpat.dll", "."),
    (python_bin / "libssl-3-x64.dll", "."),
    (python_bin / "libcrypto-3-x64.dll", "."),
    (python_bin / "sqlite3.dll", "."),
]

required_dlls = _existing_items(required_dll_candidates)

# Streamlit resources
import streamlit as streamlit_module

streamlit_pkg = Path(streamlit_module.__file__).resolve().parent

streamlit_data = collect_data_files("streamlit")
protobuf_data = collect_data_files("google.protobuf")
pyarrow_data = collect_data_files("pyarrow")

project_datas = [
    ("main_page.py", "."),
    ("main_page_optimized.py", "."),
    ("run_st.py", "."),
    ("README.md", "."),
    ("config.json", "."),
    ("config.key", "."),
    (".streamlit", ".streamlit"),
    ("pages", "pages"),
    ("src", "src"),
    ("archive", "archive"),
]

import streamlit_mermaid as streamlit_mermaid_module
import dashscope as dashscope_module
import cryptography as cryptography_module

streamlit_mermaid_path = Path(streamlit_mermaid_module.__file__).resolve().parent
cryptography_path = Path(cryptography_module.__file__).resolve().parent
dashscope_path = Path(dashscope_module.__file__).resolve().parent

package_datas = [
    (streamlit_pkg / "static", "streamlit/static"),
    (streamlit_pkg / "proto", "streamlit/proto"),
    (streamlit_pkg / "runtime", "streamlit/runtime"),
    (streamlit_mermaid_path, "streamlit_mermaid"),
    (dashscope_path, "dashscope"),
    (cryptography_path, "cryptography"),
]

alldatas = streamlit_data + protobuf_data + pyarrow_data + project_datas + package_datas

runtime_binaries = _prefix_items([(str(src), target) for src, target in required_dlls], RUNTIME_ROOT)
app_datas = _prefix_items([(str(src), target) for src, target in alldatas], APP_ROOT)
streamlit_metadata = _prefix_items(copy_metadata("streamlit"), APP_ROOT)

base_hiddenimports = [
    "cryptography.fernet",
    "streamlit",
    "streamlit.components.v1",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "streamlit.runtime.scriptrunner.script_run_context",
    "streamlit.runtime.caching",
    "streamlit.runtime.metrics",
    "streamlit_mermaid",
    "dashscope",
    "dashscope.Generation",
    "dashscope.MultiModalConversation",
    "dashscope.api_entities",
    "dashscope.audio",
    "dashscope.base",
    "dashscope.common",
    "dashscope.conversation",
    "dashscope.embeddings",
    "google.protobuf",
    "google.protobuf.json_format",
    "google.protobuf.struct_pb2",
    "google.protobuf.wrappers_pb2",
    "pyarrow",
    "pyarrow.csv",
    "pyarrow.json",
    "pyarrow.parquet",
    "pyarrow.types",
    "portalocker",
    "requests",
    "dotenv",
    "typing_extensions",
    "pkg_resources",
    "subprocess",
    "time",
    "urllib.parse",
    "src.utils.ai_equity_analyzer",
    "src.utils.alicloud_translator",
    "src.utils.config_encryptor",
    "src.utils.display_formatters",
    "src.utils.equity_llm_analyzer",
    "src.utils.excel_smart_importer",
    "src.utils.icon_integration",
    "src.utils.mermaid_function",
    "src.utils.sidebar_helpers",
    "src.utils.state_persistence",
    "src.utils.translation_usage",
    "src.utils.translator_service",
    "src.utils.uvx_helper",
    "src.utils.visjs_equity_chart",
]

dashscope_modules = collect_submodules("dashscope")
hiddenimports = base_hiddenimports + dashscope_modules

slim_excludes = [
    "panel",
    "cv2",
    "botocore",
    "boto3",
    "llvmlite",
    "numba",
    "sympy",
    "sklearn",
    "skimage",
    "sphinx",
    "sphinxcontrib",
    "distributed",
    "dask",
    "networkx",
    "openai",
    "conda",
    "holoviews",
    "datashader",
    "bokeh",
    "astropy",
    "xarray",
    "pytest",
    "matplotlib",
    "streamlit.external.langchain",
]

analysis = Analysis(
    ["run_st.py"],
    pathex=[current_dir],
    binaries=runtime_binaries,
    datas=app_datas + streamlit_metadata,
    hiddenimports=hiddenimports + collect_submodules("dashscope"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["scripts/runtime_env_hook.py", "scripts/enhanced_streamlit_static_fix_hook.py"],
    excludes=slim_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=True,
)

if analysis.zipped_data:
    pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=None)
else:
    pyz = PYZ([], [], cipher=None)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name="equity_mermaid_tool_incremental",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    contents_directory=".",
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="equity_mermaid_tool_incremental",
)
