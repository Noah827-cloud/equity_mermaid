# -*- mode: python ; coding: utf-8 -*-
import sys
import os
sys.setrecursionlimit(10000)

block_cipher = None

# 获取当前目录和Python DLL路径
current_dir = os.getcwd()
# 使用Anaconda的Library\bin目录，这里包含所有必要的DLL文件
# 注意：这会包含大量DLL文件，可能导致包体积较大和启动较慢
# 如果使用纯Python虚拟环境重新打包，可显著减小体积
anaconda_lib_bin = r'C:\Users\z001syzk\AppData\Local\anaconda3\Library\bin'

# 添加必要的二进制文件
# 明确列出所有需要的DLL文件
required_dlls = [
    # 从Anaconda的Library\bin目录添加必要的DLL
    (os.path.join(anaconda_lib_bin, 'ffi.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libbz2.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libcrypto-3-x64.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libexpat.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'liblzma.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'libssl-3-x64.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'sqlite3.dll'), '.'),
    # 添加protobuf相关的DLL文件
    (os.path.join(anaconda_lib_bin, 'libprotobuf.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'abseil_dll.dll'), '.'),
    # 添加PyArrow相关的DLL文件
    (os.path.join(anaconda_lib_bin, 'arrow.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow_flight.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow_dataset.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow_acero.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'arrow_substrait.dll'), '.'),
    (os.path.join(anaconda_lib_bin, 'parquet.dll'), '.'),
    # 从Anaconda的DLLs目录添加Python扩展模块
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', 'pyexpat.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_ctypes.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_ssl.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_hashlib.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_sqlite3.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_lzma.pyd'), '.'),
    (os.path.join(r'C:\Users\z001syzk\AppData\Local\anaconda3\DLLs', '_bz2.pyd'), '.'),
]

APP_ROOT = 'app'
RUNTIME_ROOT = 'runtime'


def _prefix_items(items, prefix):
    """Attach a root folder to bundled artifacts to support incremental updates."""
    prefixed = []
    for src_path, target_path in items:
        normalized_target = target_path or '.'
        combined = os.path.normpath(os.path.join(prefix, normalized_target))
        prefixed.append((src_path, combined))
    return prefixed
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# 收集Streamlit及其依赖的所有数据文件
# 优化：只收集必需的数据文件，减少打包大小和启动时间
streamlit_data = collect_data_files('streamlit')
# pandas_data = collect_data_files('pandas')  # 注释：pandas不需要额外数据文件
# jinja2_data = collect_data_files('jinja2')  # 注释：jinja2不需要额外数据文件
# markdown_data = collect_data_files('markdown')  # 注释：markdown不需要额外数据文件
# altair_data = collect_data_files('altair')  # 注释：altair数据文件较大但非必需
# pydeck_data = collect_data_files('pydeck')  # 注释：pydeck数据文件较大但非必需
protobuf_data = collect_data_files('google.protobuf')  # 保留：protobuf需要
pyarrow_data = collect_data_files('pyarrow')  # 保留：pyarrow需要用于Excel处理

# 收集额外的字体和CSS资源
import streamlit as streamlit_module
streamlit_static_path = os.path.join(os.path.dirname(streamlit_module.__file__), 'static')

# 添加项目的核心文件
project_datas = [
        ('main_page.py', '.'),
        ('pages/1_图像识别模式.py', 'pages'),
        ('pages/2_手动编辑模式.py', 'pages'),
        ('.streamlit/config.toml', '.streamlit'),  # 添加streamlit配置文件
        ('.streamlit/pages/1_图像识别模式.py', '.streamlit/pages'),  # 添加streamlit页面配置
        ('.streamlit/pages/2_手动编辑模式.py', '.streamlit/pages'),  # 添加streamlit页面配置
    ('src/__init__.py', 'src'),
    ('src/config/__init__.py', 'src/config'),
    ('src/config/config.json.template', 'src/config'),
    ('src/config/mcp_config.json', 'src/config'),  # 添加移动后的配置文件
    ('src/main/__init__.py', 'src/main'),
    ('src/main/enhanced_equity_to_mermaid.py', 'src/main'),
    ('src/main/manual_equity_editor.py', 'src/main'),
    ('src/utils/__init__.py', 'src/utils'),
    ('src/utils/ai_equity_analyzer.py', 'src/utils'),
    ('src/utils/alicloud_translator.py', 'src/utils'),
    ('src/utils/config_encryptor.py', 'src/utils'),
    ('src/utils/equity_llm_analyzer.py', 'src/utils'),
    ('src/utils/mermaid_function.py', 'src/utils'),
    ('src/utils/visjs_equity_chart.py', 'src/utils'),  # 添加visjs图表工具
    ('src/utils/icon_integration.py', 'src/utils'),  # 添加图标集成工具
    ('src/utils/uvx_helper.py', 'src/utils'),  # 添加UVX辅助工具
    ('src/utils/state_persistence.py', 'src/utils'),  # 添加状态持久化工具
    ('src/utils/excel_smart_importer.py', 'src/utils'),  # 添加Excel智能导入工具
    ('src/utils/translator_service.py', 'src/utils'),  # 添加翻译服务模块
    ('src/utils/translation_usage.py', 'src/utils'),  # 添加翻译用量缓存模块
    ('src/utils/sidebar_helpers.py', 'src/utils'),  # 添加侧边栏辅助工具（百度搜索英文名校验）
    ('src/utils/display_formatters.py', 'src/utils'),  # 添加显示格式化工具
    # 添加SVG图标资源
    ('src/assets/icons/ant-design_picture-outlined.svg', 'src/assets/icons'),
    ('src/assets/icons/ant-design_picture-twotone.svg', 'src/assets/icons'),
    ('src/assets/icons/clarity_picture-solid.svg', 'src/assets/icons'),
    ('src/assets/icons/icon-park_edit-one.svg', 'src/assets/icons'),
    ('src/assets/icons/icon-park_upload-picture.svg', 'src/assets/icons'),
    ('src/assets/icons/ix_start-data-analysis.svg', 'src/assets/icons'),
    ('src/assets/icons/mynaui_edit-one-solid.svg', 'src/assets/icons'),
    ('src/assets/icons/streamline-sharp_edit-pdf-remix.svg', 'src/assets/icons'),
    ('src/assets/icons/streamline-sharp_edit-pdf-solid.svg', 'src/assets/icons'),
    ('scripts/run_app.py', 'scripts'),
    ('scripts/start_all.bat', 'scripts'),
        ('scripts/generate_equity_data_with_controller.py', 'scripts'),  # 更新到scripts目录
        ('scripts/import_control_relationship.py', 'scripts'),  # 更新到scripts目录
        ('scripts/mcp_env_uvx_launcher.py', 'scripts'),  # 添加移动后的脚本
        ('scripts/runtime_static_fix.py', 'scripts'),  # 添加runtime静态修复脚本
    ('README.md', '.'),
    # 添加配置文件
    ('config.json', '.'),
    ('config.key', '.'),
    # 添加archive目录以包含测试数据文件
    ('archive/', 'archive'),
    # 追加streamlit静态资源、proto目录和runtime目录
    (anaconda_lib_bin + '\\..\\..\\Lib\\site-packages\\streamlit\\static', 'app/streamlit/static'),
    (anaconda_lib_bin + '\\..\\..\\Lib\\site-packages\\streamlit\\proto',  'app/streamlit/proto'),
    (anaconda_lib_bin + '\\..\\..\\Lib\\site-packages\\streamlit\\runtime', 'app/streamlit/runtime'),
]

# 包含streamlit_mermaid组件的前端文件
streamlit_mermaid_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'streamlit_mermaid')
# 包含dashscope模块
import dashscope as dashscope_module
dashscope_path = os.path.dirname(dashscope_module.__file__)
# 包含cryptography模块
import cryptography as cryptography_module
cryptography_path = os.path.dirname(cryptography_module.__file__)

# 合并所有数据文件
# 优化：只包含必需的数据文件
alldatas = streamlit_data + protobuf_data + pyarrow_data + project_datas + [
    # 添加streamlit_mermaid组件的前端文件
    (os.path.join(streamlit_mermaid_path, 'frontend', 'build'), 'streamlit_mermaid/frontend/build'),
    # 添加streamlit_mermaid的其他必要文件
    (streamlit_mermaid_path, 'streamlit_mermaid'),
    # 添加dashscope模块
    (dashscope_path, 'dashscope'),
    # 添加cryptography模块
    (cryptography_path, 'cryptography'),
    # 修复Streamlit静态文件路径 - 确保在app/streamlit/static下正确收集
    (streamlit_static_path, 'app/streamlit/static'),
    # 添加额外的Streamlit静态文件路径，确保运行时能找到
    (anaconda_lib_bin + '\\..\\..\\Lib\\site-packages\\streamlit\\static', 'app/streamlit/static'),
]

# 过滤掉可能导致权限问题的 Jupyter runtime 临时文件
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

runtime_binaries = _prefix_items(required_dlls, RUNTIME_ROOT)
app_datas = _prefix_items(alldatas, APP_ROOT)
streamlit_metadata = _prefix_items(copy_metadata('streamlit'), APP_ROOT)

# 收集所有必要的模块
s_lit_modules = collect_submodules('streamlit')
pd_modules = collect_submodules('pandas')
np_modules = collect_submodules('numpy')

# 收集dashscope的所有子模块以确保完整包含
dashscope_modules = collect_submodules('dashscope')

# 添加hiddenimports，确保PyInstaller能正确识别和打包所有依赖
allhiddenimports = [
    'cryptography.fernet',
    'streamlit',
    'streamlit.components.v1',
    'streamlit.runtime.scriptrunner.magic_funcs',  # 添加缺少的Streamlit模块
    'streamlit.runtime',  # 添加streamlit.runtime模块
    'streamlit.runtime.scriptrunner',  # 添加streamlit.runtime.scriptrunner模块
    'streamlit.runtime.scriptrunner.script_run_context',  # 添加script_run_context模块
    'streamlit.runtime.caching',  # 添加caching模块
    'streamlit.runtime.metrics',  # 添加metrics模块
    'streamlit_mermaid',  # 添加streamlit_mermaid依赖
    'dashscope',  # 添加dashscope依赖
    'dashscope.Generation',  # 添加dashscope.Generation依赖
    'dashscope.MultiModalConversation',  # 添加dashscope.MultiModalConversation依赖
    'dashscope.api_entities',  # 添加dashscope API实体
    'dashscope.api_entities.dashscope_response',  # 添加响应相关模块
    'dashscope.audio',  # 添加音频相关模块
    'dashscope.base',  # 添加基础模块
    'dashscope.common',  # 添加通用模块
    'dashscope.conversation',  # 添加会话模块
    'dashscope.embeddings',  # 添加嵌入模块
    'dashscope.images',  # 添加图像模块
    'dashscope.multimodal',  # 添加多模态模块
    'dashscope.text',  # 添加文本模块
    # 添加protobuf相关模块
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
    # 添加PyArrow相关模块
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
    're',
    'datetime',
    'shutil',
    'webbrowser',
    'typing_extensions',
    'importlib_metadata',
    'subprocess',
    'time',
    # 添加项目工具模块
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
    'base64',
    'tempfile',
    'webbrowser',
    'urllib.parse'
] + dashscope_modules  # 添加所有收集到的dashscope子模块

# 分析应用
a = Analysis(['run_st.py'],
             pathex=[current_dir],
             binaries=runtime_binaries,
             datas=app_datas + streamlit_metadata,
             hiddenimports=allhiddenimports,
             hookspath=[],
             hooksconfig={},
             runtime_hooks=['scripts/runtime_env_hook.py', 'scripts/enhanced_streamlit_static_fix_hook.py'],
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
                 # 排除不必要的科学计算库
                 'scipy.integrate',
                 'scipy.special', 
                 'scipy.stats',
                 # 排除大数据存储库
                 'h5py',
                 'tables',
                 # 排除GUI框架
                 'PyQt5',
                 'PyQt6',
                 # 排除消息队列
                 'zmq',
                 # 排除其他不必要的库
                 'matplotlib',
                 'seaborn',
                 'plotly',
             ],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)

# 创建PYZ文件
if a.zipped_data:
    pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
else:
    # Create a minimal PYZ archive to satisfy the bootloader even though
    # we rely on unpacked modules under app/.
    pyz = PYZ([], [], cipher=block_cipher)
exe_inputs = pyz

# 创建EXE文件
exe = EXE(exe_inputs,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='equity_mermaid_tool_incremental',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          runtime_tmpdir=None,
          contents_directory='.',
          console=True,  # 使用控制台模式，便于调试
          disable_windowed_traceback=False,
          argv_emulation=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='equity_mermaid_tool_incremental')


