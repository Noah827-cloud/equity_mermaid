# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# 收集必要的文件
datas = [
    ('manual_equity_editor.py', '.'),
    ('mermaid_function.py', '.')
]

# 隐藏导入 - 确保包含所有必要的模块
hiddenimports = [
    'streamlit',
    'streamlit_mermaid',
    'streamlit.logger',
    'streamlit.scriptrunner.magic_funcs',
    'streamlit.script_runner',
    'streamlit.web.bootstrap',
    'streamlit.command_line',
    'streamlit.cli',
    'streamlit.runtime.scriptrunner.magic_funcs',
    'pandas',
    'numpy',
    'PIL',
    'altair',
    'plotly',
    'plotly.offline',
    'plotly.graph_objs',
    'plotly.graph_objs.layout',
    'pyexpat',
    'xml.parsers.expat',
    'xml.parsers',
    'xml',
    'pkg_resources',
    'pkg_resources.py2_warn',
    'pkg_resources.py31compat',
    '_io',
    'lzma',
    'socket',
    'select',
    'unicodedata',
    'ctypes',
    'importlib_metadata',
    'typing_extensions',
    'zipp'
]

# 分析应用
a = Analysis(['manual_equity_editor.py'],
             pathex=[],
             binaries=[],
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# 确保添加pyexpat相关的DLL
dlls_dir = 'C:\\Users\\z001syzk\\AppData\\Local\\anaconda3\\DLLs'
for dll in ['pyexpat.pyd', '_ctypes.pyd', 'select.pyd', 'unicodedata.pyd', '_socket.pyd']:
    dll_path = os.path.join(dlls_dir, dll)
    if os.path.exists(dll_path):
        a.binaries.append((dll, dll_path, 'BINARY'))

# 创建PYZ文件
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建EXE文件
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='equity_editor_v9',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          argv_emulation=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)

# 收集所有文件到一个目录
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='equity_editor_v9')