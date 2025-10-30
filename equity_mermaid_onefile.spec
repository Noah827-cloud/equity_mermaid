# -*- mode: python ; coding: utf-8 -*-
"""
单文件打包配置（onefile 模式）
生成一个独立的 exe 文件，无需 _internal 目录
注意：启动速度会比 onedir 慢，因为需要临时解压
"""

import sys
import os
sys.setrecursionlimit(10000)

block_cipher = None

# 获取当前目录和Python DLL路径
current_dir = os.getcwd()
anaconda_lib_bin = r'C:\Users\z001syzk\AppData\Local\anaconda3\Library\bin'

# 添加必要的二进制文件
required_dlls = [
    (os.path.join(anaconda_lib_bin, 'ffi.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libbz2.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libcrypto-3-x64.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libexpat.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'liblzma.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libssl-3-x64.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'sqlite3.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libprotobuf.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'abseil_dll.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow_flight.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow_dataset.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow_acero.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow_substrait.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'parquet.dll'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', 'pyexpat.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_ctypes.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_ssl.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_hashlib.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_sqlite3.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_lzma.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_bz2.pyd'), '.'),
]

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# 收集数据文件
streamlit_data = collect_data_files('streamlit')
protobuf_data = collect_data_files('google.protobuf')
pyarrow_data = collect_data_files('pyarrow')

import streamlit as streamlit_module
streamlit_static_path = os.path.join(os.path.dirname(streamlit_module.__file__), 'static')

# 项目数据文件（简化版，只包含关键资源）
project_datas = [
    ('main_page.py', '.'),
    ('pages/1_图像识别模式.py', 'pages'),
    ('pages/2_手动编辑模式.py', 'pages'),
    ('src/__init__.py', 'src'),
    ('src/config/__init__.py', 'src/config'),
    ('src/config/config.json.template', 'src/config'),
    ('src/config/mcp_config.json', 'src/config'),
    ('src/main/__init__.py', 'src/main'),
    ('src/main/enhanced_equity_to_mermaid.py', 'src/main'),
    ('src/main/manual_equity_editor.py', 'src/main'),
    ('src/utils/__init__.py', 'src/utils'),
    ('src/utils/ai_equity_analyzer.py', 'src/utils'),
    ('src/utils/alicloud_translator.py', 'src/utils'),
    ('src/utils/config_encryptor.py', 'src/utils'),
    ('src/utils/display_formatters.py', 'src/utils'),
    ('src/utils/equity_llm_analyzer.py', 'src/utils'),
    ('src/utils/mermaid_function.py', 'src/utils'),
    ('src/utils/visjs_equity_chart.py', 'src/utils'),
    ('src/utils/icon_integration.py', 'src/utils'),
    ('src/utils/uvx_helper.py', 'src/utils'),
    ('src/utils/state_persistence.py', 'src/utils'),
    ('src/utils/excel_smart_importer.py', 'src/utils'),
    ('src/utils/translator_service.py', 'src/utils'),
    ('src/utils/translation_usage.py', 'src/utils'),
    ('src/utils/sidebar_helpers.py', 'src/utils'),
    # SVG图标
    ('src/assets/icons/ant-design_picture-outlined.svg', 'src/assets/icons'),
    ('src/assets/icons/ant-design_picture-twotone.svg', 'src/assets/icons'),
    ('src/assets/icons/clarity_picture-solid.svg', 'src/assets/icons'),
    ('src/assets/icons/icon-park_edit-one.svg', 'src/assets/icons'),
    ('src/assets/icons/icon-park_upload-picture.svg', 'src/assets/icons'),
    ('src/assets/icons/ix_start-data-analysis.svg', 'src/assets/icons'),
    ('src/assets/icons/mynaui_edit-one-solid.svg', 'src/assets/icons'),
    ('src/assets/icons/streamline-sharp_edit-pdf-remix.svg', 'src/assets/icons'),
    ('src/assets/icons/streamline-sharp_edit-pdf-solid.svg', 'src/assets/icons'),
    ('README.md', '.'),
    ('config.json', '.'),
    ('config.key', '.'),
    (streamlit_static_path, 'streamlit/static'),
]

# 包含必要模块
import dashscope as dashscope_module
dashscope_path = os.path.dirname(dashscope_module.__file__)

import cryptography as cryptography_module
cryptography_path = os.path.dirname(cryptography_module.__file__)

streamlit_mermaid_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'streamlit_mermaid')

# 合并所有数据文件
alldatas = streamlit_data + protobuf_data + pyarrow_data + project_datas + [
    (os.path.join(streamlit_mermaid_path, 'frontend', 'build'), 'streamlit_mermaid/frontend/build'),
    (streamlit_mermaid_path, 'streamlit_mermaid'),
    (dashscope_path, 'dashscope'),
    (cryptography_path, 'cryptography'),
    (streamlit_static_path, 'streamlit/static'),
]

# 过滤 Jupyter runtime 临时文件
jupyter_runtime_dir = os.path.normcase(
    os.path.join(os.environ.get('APPDATA', ''), 'jupyter', 'runtime')
)
if jupyter_runtime_dir:
    filtered_datas = []
    for src_path, target_path in alldatas:
        if os.path.normcase(src_path).startswith(jupyter_runtime_dir):
            continue
        filtered_datas.append((src_path, target_path))
    alldatas = filtered_datas

# 收集子模块
dashscope_modules = collect_submodules('dashscope')

# hiddenimports
allhiddenimports = [
    'cryptography.fernet',
    'streamlit',
    'streamlit.components.v1',
    'streamlit_mermaid',
    'dashscope',
    'dashscope.Generation',
    'dashscope.MultiModalConversation',
    'dashscope.api_entities',
    'dashscope.api_entities.dashscope_response',
    'dashscope.audio',
    'dashscope.base',
    'dashscope.common',
    'dashscope.conversation',
    'dashscope.embeddings',
    'dashscope.images',
    'dashscope.multimodal',
    'dashscope.text',
    'google.protobuf',
    'google.protobuf.internal',
    'google.protobuf.internal.api_implementation',
    'google.protobuf.descriptor',
    'google.protobuf.pyext._message',
    'google.protobuf.message',
    'google.protobuf.descriptor_pool',
    'google.protobuf.descriptor_database',
    'google.protobuf.text_format',
    'google.protobuf.json_format',
    'google.protobuf.any_pb2',
    'google.protobuf.duration_pb2',
    'google.protobuf.empty_pb2',
    'google.protobuf.field_mask_pb2',
    'google.protobuf.struct_pb2',
    'google.protobuf.timestamp_pb2',
    'google.protobuf.wrappers_pb2',
    'pyarrow',
    'pyarrow.lib',
    'pyarrow.compute',
    'pyarrow.csv',
    'pyarrow.feather',
    'pyarrow.json',
    'pyarrow.parquet',
    'pyarrow.plasma',
    'pyarrow.serialization',
    'pyarrow.types',
    'portalocker',
    'requests',
    'json',
    're',
    'tempfile',
    'webbrowser',
    'base64',
    'os',
    'sys',
    'dotenv',
    'typing',
    'typing_extensions',
    'importlib_metadata',
    'pkg_resources',
    'datetime',
    'shutil',
    'subprocess',
    'time',
    'urllib.parse',
    # 项目工具模块
    'src.utils.ai_equity_analyzer',
    'src.utils.alicloud_translator',
    'src.utils.config_encryptor',
    'src.utils.display_formatters',
    'src.utils.equity_llm_analyzer',
    'src.utils.excel_smart_importer',
    'src.utils.icon_integration',
    'src.utils.mermaid_function',
    'src.utils.sidebar_helpers',
    'src.utils.state_persistence',
    'src.utils.translation_usage',
    'src.utils.translator_service',
    'src.utils.uvx_helper',
    'src.utils.visjs_equity_chart',
] + dashscope_modules

# 分析应用
a = Analysis(['run_st.py'],
             pathex=[current_dir],
             binaries=required_dlls,
             datas=alldatas + copy_metadata('streamlit'),
             hiddenimports=allhiddenimports,
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[
                 'jupyter',
                 'jupyter_client',
                 'jupyter_core',
                 'jupyter_server',
                 'jupyterlab',
                 'jupyterlab_server',
                 'notebook',
                 'ipykernel',
                 'ipywidgets',
             ],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ========== 关键区别：onefile 模式 ==========
# 所有内容打包到一个 exe 文件中
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # ← 包含所有二进制文件
    a.zipfiles,      # ← 包含所有 zip 文件
    a.datas,         # ← 包含所有数据文件
    [],
    name='equity_mermaid_tool_onefile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,        # ← 启用 UPX 压缩（可选）
    upx_exclude=[],
    runtime_tmpdir=None,  # ← 使用系统临时目录
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)

# 注意：onefile 模式不需要 COLLECT

