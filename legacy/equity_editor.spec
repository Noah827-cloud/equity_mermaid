import sys
sys.setrecursionlimit(10000)

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 获取当前目录
import os
current_dir = os.getcwd()

# 收集所有需要的DLL文件
all_binaries = []

# 添加关键系统DLL
py_exe = sys.executable
py_dir = os.path.dirname(py_exe)
dlls_dir = os.path.join(py_dir, 'DLLs')

# 添加expat相关DLL
if os.path.exists(dlls_dir):
    if os.path.exists(os.path.join(dlls_dir, 'pyexpat.pyd')):
        all_binaries.append((os.path.join(dlls_dir, 'pyexpat.pyd'), '.'))
    if os.path.exists(os.path.join(dlls_dir, '_ctypes.pyd')):
        all_binaries.append((os.path.join(dlls_dir, '_ctypes.pyd'), '.'))
    if os.path.exists(os.path.join(dlls_dir, 'select.pyd')):
        all_binaries.append((os.path.join(dlls_dir, 'select.pyd'), '.'))
    if os.path.exists(os.path.join(dlls_dir, 'unicodedata.pyd')):
        all_binaries.append((os.path.join(dlls_dir, 'unicodedata.pyd'), '.'))
    if os.path.exists(os.path.join(dlls_dir, '_socket.pyd')):
        all_binaries.append((os.path.join(dlls_dir, '_socket.pyd'), '.'))

# 添加固定路径的DLL作为备选
if os.path.exists('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\pyexpat.pyd'):
    all_binaries.append(('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\pyexpat.pyd', '.'))
if os.path.exists('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\_ctypes.pyd'):
    all_binaries.append(('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\_ctypes.pyd', '.'))
if os.path.exists('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\select.pyd'):
    all_binaries.append(('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\select.pyd', '.'))
if os.path.exists('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\unicodedata.pyd'):
    all_binaries.append(('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\unicodedata.pyd', '.'))
if os.path.exists('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\_socket.pyd'):
    all_binaries.append(('C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs\\_socket.pyd', '.'))

# 确保添加所有必要的Streamlit数据文件
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集Streamlit及其依赖的所有数据文件
streamlit_data = collect_data_files('streamlit')
pandas_data = collect_data_files('pandas')
matplotlib_data = collect_data_files('matplotlib')
jinja2_data = collect_data_files('jinja2')
markdown_data = collect_data_files('markdown')
altair_data = collect_data_files('altair')
pydeck_data = collect_data_files('pydeck')

# 合并所有数据文件
alldatas = streamlit_data + pandas_data + matplotlib_data + jinja2_data + markdown_data + altair_data + pydeck_data

# 确保manual_equity_editor.py和mermaid_function.py被包含
alldatas.append(('manual_equity_editor.py', '.'))
alldatas.append(('mermaid_function.py', '.'))

# 收集所有必要的模块
s_lit_modules = collect_submodules('streamlit')
pd_modules = collect_submodules('pandas')
np_modules = collect_submodules('numpy')
matplotlib_modules = collect_submodules('matplotlib')
pyarrow_modules = collect_submodules('pyarrow')

# 添加streamlit_mermaid模块
streamlit_mermaid_modules = collect_submodules('streamlit_mermaid')

# 基础隐藏导入
allhiddenimports = [
    'streamlit',
    'streamlit.cli',
    'streamlit.server',
    'streamlit.server.server',
    'streamlit.web.bootstrap',
    'streamlit.scriptrunner',
    'streamlit.scriptrunner.magic_funcs',
    'streamlit.script_runner',
    'streamlit.components',
    'streamlit.components.v1',
    'streamlit.runtime',
    'streamlit.runtime.caching',
    'streamlit.runtime.state.session_state',
    'streamlit.runtime.legacy_caching',
    'streamlit_mermaid',
    'streamlit.logger',
    'pandas',
    'numpy',
    'matplotlib',
    'pyarrow',
    'jinja2',
    'markdown',
    'pygments',
    'watchdog',
    'cachetools',
    'rich',
    'altair',
    'vega_datasets',
    'typing_extensions',
    'protobuf',
    'requests',
    'tornado',
    'click',
    'bokeh',
    'packaging',
    'importlib_metadata',
    'pydeck',
    'pyyaml',
    'pytz',
    'dateutil',
    'six',
    'webencodings',
    'bleach',
    'pillow',
    'traitlets',
    'entrypoints',
    'certifi',
    'idna',
    'urllib3',
    'charset_normalizer',
    'zipp',
    'more_itertools',
    'zstandard',
    'pyexpat',
    'xml.parsers.expat',
    'xml.parsers',
    'xml',
    'pkg_resources',
    'pkg_resources.extern.jaraco.text',
    'pkg_resources.extern.jaraco',
    'pkg_resources.extern',
    'pkg_resources.py2_warn',
    'pkg_resources.py31compat',
    '_io',
    'lzma',
    'socket',
    'select',
    'unicodedata',
    'ctypes',
    'PIL',
    'plotly',
    'plotly.offline',
    'plotly.graph_objs',
    'plotly.graph_objs.layout'
]

# 添加收集的子模块
allhiddenimports.extend(s_lit_modules)
allhiddenimports.extend(pd_modules)
allhiddenimports.extend(np_modules)
allhiddenimports.extend(matplotlib_modules)
allhiddenimports.extend(pyarrow_modules)
allhiddenimports.extend(streamlit_mermaid_modules)

# 添加额外的Streamlit相关模块
allhiddenimports.extend([
    'streamlit.command_line',
    'streamlit.runtime.scriptrunner.magic_funcs'
])

# 分析应用
a = Analysis(
    ['manual_equity_editor.py'],
    pathex=[current_dir],
    binaries=all_binaries,
    datas=alldatas,
    hiddenimports=allhiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 创建PYZ文件
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建EXE文件
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='equity_editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

# 收集所有文件到一个文件夹
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='equity_editor_v8'  # 使用新的目录名称
)