import os
import re
import tempfile
import webbrowser
import base64
import json
import sys
import streamlit as st
import requests
from streamlit_mermaid import st_mermaid
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
# 导入翻译模块
from src.utils.translator_service import translate_text as _ali_translate_text, QuotaExceededError
from src.utils.translation_usage import get_monthly_usage
# 导入Mermaid生成功能
from src.utils.mermaid_function import generate_mermaid_from_data as generate_mermaid_diagram
from src.utils.sidebar_helpers import render_baidu_name_checker

def resolve_resource_path(relative_path: Path) -> Path:
    """Resolve data files for development, full bundle, and incremental bundle layouts."""
    relative_path = Path(relative_path)
    if relative_path.is_absolute():
        return relative_path

    candidate_roots = []
    seen = set()

    def register(path):
        if not path:
            return
        try:
            resolved = Path(path).resolve()
        except Exception:
            resolved = Path(path)
        if resolved not in seen:
            seen.add(resolved)
            candidate_roots.append(resolved)

    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).resolve().parent
        meipass = Path(getattr(sys, '_MEIPASS', exe_dir))
        register(meipass)
        register(meipass / 'app')
        register(exe_dir)
        register(exe_dir / 'app')

    origin = Path(__file__).resolve()
    register(origin.parent)
    for ancestor in list(origin.parents)[:6]:
        register(ancestor)
        if ancestor.name in {'src', 'pages'}:
            register(ancestor.parent)
        register(ancestor / 'app')

    cwd = Path.cwd()
    register(cwd)
    register(cwd / 'app')

    for base in candidate_roots:
        candidate = base / relative_path
        if candidate.exists():
            return candidate

    return candidate_roots[0] / relative_path


# 加载环境变量
load_dotenv()

# 设置页面配置
st.set_page_config(
    page_title="股权结构图生成工具 - 图像识别模式",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"  # 默认折叠侧边栏
)

# 添加CSS样式来隐藏默认的导航内容，但保留自定义侧边栏
st.markdown("""
<style>
    /* 隐藏默认的导航内容 */
    [data-testid="stSidebarNav"],
    [data-testid="stSidebar"] [href*="main_page"],
    [data-testid="stSidebar"] [href*="1_图像识别模式"],
    [data-testid="stSidebar"] [href*="2_手动编辑模式"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        opacity: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# 自定义侧边栏 - 复制main_page.py的样式，确保导航一致性
with st.sidebar:
    # 侧边栏标题
    st.sidebar.title("股权分析平台") 
    
    st.sidebar.subheader("功能导航") 
    
    # 导航按钮，使用Unicode图标
    if st.sidebar.button("🏠 主页", help="返回主页面"):
        # 使用正确的相对路径
        st.switch_page("main_page.py")
        
    if st.sidebar.button("🔍 图像识别模式", help="使用AI识别股权结构图", use_container_width=True):
        # 使用正确的相对路径
        st.switch_page("pages/1_图像识别模式.py")
        
    if st.sidebar.button("📊 手动编辑模式", help="手动创建和编辑股权结构", use_container_width=True):
        # 使用正确的相对路径
        st.switch_page("pages/2_手动编辑模式.py")
    
    # 使用展开面板显示使用说明
    usage_expander = st.sidebar.expander("ℹ️ 使用说明", expanded=False)
    with usage_expander:
        st.markdown("### ✍️ 翻译额度管理")
        try:
            usage = get_monthly_usage()
            used = usage.get('used', 0)
            limit = usage.get('limit', 0)
            remaining = max(0, limit - used)
            st.markdown(f"**本月已用/总额：** {used} / {limit}（剩余 {remaining}）")
        except Exception:
            pass

        st.markdown("### 🔍 图像识别操作流程")
        st.markdown("1. **上传图片**：选择包含股权结构信息的 PNG/JPG/JPEG，或点击\"🧪 加载测试数据\"体验示例。")
        st.markdown("2. **配置选项**：按需调整识别模型、输入提示词，并可勾选\"将中文股权信息翻译成英文\"。")
        st.markdown("3. **开始分析**：点击\"开始分析\"后系统会提取核心公司、股东、子公司与关系，并输出详细日志。")
        st.markdown("4. **复核调整**：在结果表格中检查、编辑或删除识别信息，所有改动会同步到图表。")
        st.markdown("5. **导出分享**：生成 Mermaid 代码、JSON 数据、交互式 HTML（支持全屏、拖拽、主题切换、PNG 下载）。")

        st.markdown("### 🛠️ 辅助工具")
        st.markdown("• 底部\"识别过程\"展示完整请求与模型返回，便于排查。")
        st.markdown("• 翻译前请确认 config.json 已配置阿里云 AccessKey，额度不足时会提示。")
        st.markdown("• 侧边栏快捷入口可在主页、手动编辑模式之间快速切换。")
        render_baidu_name_checker(usage_expander, key_prefix="enhanced_equity")
    st.sidebar.markdown("---")

    # 添加版权说明
    current_year = datetime.now().year
    st.sidebar.markdown(
        f'<h6>© {current_year} Noah 版权所有</h6>',
        unsafe_allow_html=True,
    )

# 提取JSON的辅助函数
def extract_json_from_text(text: str):
    """从任意文本中提取第一个合法的 JSON 对象"""
    # 尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 尝试匹配 ```json ... ``` 或 ``` ... ```
    json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试查找最外层的 {...}
    brace_match = re.search(r"({.*})", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    # 如果都失败，抛出错误并显示原始内容
    raise ValueError(f"无法从以下文本中提取 JSON:\n{text}")

# 翻译股权结构数据的函数
def translate_equity_data(data, translate_names=False):
    """
    翻译股权结构数据
    data: 包含main_company、shareholders和subsidiaries的字典
    translate_names: 是否翻译公司名称和股东名称
    """
    if not translate_names or not data:
        return data
    
    # 深拷贝数据以避免修改原始数据
    translated_data = json.loads(json.dumps(data))
    
    # 创建缓存字典来存储已翻译的内容，避免重复翻译和保持一致性
    translation_cache = {}
    
    # 辅助函数：翻译文本，如果已经翻译过则从缓存获取
    def translate_text(text):
        # 检查是否已经在缓存中
        if text in translation_cache:
            return translation_cache[text]
        
        # 如果不在缓存中，调用统一翻译服务（包含共享缓存与额度控制）
        try:
            translated_name = _ali_translate_text(text, 'zh', 'en')
            translation_cache[text] = translated_name
            return translated_name
        except QuotaExceededError:
            st.warning("当月翻译额度已用完，已跳过翻译。")
            translation_cache[text] = text
            return text
        except Exception as e:
            st.warning(f"⚠️ 翻译 '{text}' 时发生异常: {str(e)}")
            translation_cache[text] = text
            return text
    
    # 翻译主公司名称
    if "main_company" in translated_data:
        translated_data["main_company"] = translate_text(translated_data["main_company"])
    # 兼容core_company字段
    elif "core_company" in translated_data:
        translated_data["core_company"] = translate_text(translated_data["core_company"])
    
    # 翻译股东名称
    if "shareholders" in translated_data:
        for shareholder in translated_data["shareholders"]:
            if "name" in shareholder:
                shareholder["name"] = translate_text(shareholder["name"])
    
    # 翻译子公司名称
    if "subsidiaries" in translated_data:
        for subsidiary in translated_data["subsidiaries"]:
            if "name" in subsidiary:
                subsidiary["name"] = translate_text(subsidiary["name"])
    
    # 翻译实际控制人
    if "controller" in translated_data and translated_data["controller"]:
        translated_data["controller"] = translate_text(translated_data["controller"])
    
    # 翻译顶层实体名称
    if "top_level_entities" in translated_data:
        for entity in translated_data["top_level_entities"]:
            if "name" in entity:
                entity["name"] = translate_text(entity["name"])
    
    # 翻译控制关系中的实体名称
    if "control_relationships" in translated_data:
        for rel in translated_data["control_relationships"]:
            if "parent" in rel:
                rel["parent"] = translate_text(rel["parent"])
            if "child" in rel:
                rel["child"] = translate_text(rel["child"])
    
    # 翻译实体关系中的实体名称
    if "entity_relationships" in translated_data:
        for rel in translated_data["entity_relationships"]:
            if "parent" in rel:
                rel["parent"] = translate_text(rel["parent"])
            if "child" in rel:
                rel["child"] = translate_text(rel["child"])
    
    # 翻译所有实体名称
    if "all_entities" in translated_data:
        for entity in translated_data["all_entities"]:
            if "name" in entity:
                entity["name"] = translate_text(entity["name"])
    
    return translated_data

# 初始化会话状态
if 'mermaid_code' not in st.session_state:
    st.session_state.mermaid_code = ""

if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = {}

if 'json_data' not in st.session_state:
    st.session_state.json_data = ""

if 'use_real_api' not in st.session_state:
    st.session_state.use_real_api = False

if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

if 'translate_to_english' not in st.session_state:
    st.session_state.translate_to_english = False

# 设置页面配置
st.set_page_config(
    page_title="股权结构图表生成器",
    page_icon="📊",
    layout="wide"
)

# 自定义 CSS
st.markdown("""
<style>
    /* 主题变量 - 与主页保持一致 */
    :root {
        --primary-color: #0f4c81;
        --secondary-color: #17a2b8;
        --accent-color: rgba(255, 255, 255, 0.95);
        --text-color: #2c3e50;
        --light-text: #6c757d;
        --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        --transition: all 0.3s ease;
    }
    
    /* 侧边栏样式 - 基础容器样式 */
    [data-testid="stSidebar"] {
        background-color: var(--primary-color) !important; /* 使用主色调保持一致 */
        color: #ffffff !important;
        padding: 1rem 0.5rem;
        min-width: 250px !important;
        max-width: 280px !important;
    }
    
    /* 侧边栏文本统一样式 - 使用高优先级选择器 */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #e0e0e0 !important;
        font-size: 14px !important;
        font-weight: normal !important;
    }
    
    /* 侧边栏菜单项样式 */
    [data-testid="stSidebar"] .stButton button {
        background-color: transparent !important;
        color: #e0e0e0 !important;
        border: none !important;
        box-shadow: none !important;
        background-image: none !important;
        text-align: left !important;
        font-size: 14px !important;
    }
    
    /* 展开面板内容样式 - 使用更高优先级选择器 */
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
        color: #e0e0e0 !important !important;
        background-color: var(--primary-color) !important !important; /* 使用主色调保持一致 */
    }
    
    /* 通用后代选择器 - 确保覆盖所有子元素 */
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] * {
        color: #e0e0e0 !important !important;
        font-size: 14px !important !important;
        font-weight: normal !important !important;
    }
    
    /* 特定元素选择器 - 确保标题和段落也使用正确的字体大小 */
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] h1,
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] h2,
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] h3,
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] h4,
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] h5,
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] h6,
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] p {
        font-size: 14px !important !important;
        font-weight: normal !important !important;
        color: #e0e0e0 !important !important;
    }
    
    /* 确保按钮内的文本也有正确的字体大小 */
    [data-testid="stSidebar"] .stButton button > * {
        font-size: 14px !important !important;
    }
    
    /* 页面背景 - 改为白色透明 */
    body {
        background-color: var(--accent-color);
    }
    
    .main-container {
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* 上传容器 - 添加悬浮效果 */
    .upload-container {
        background-color: rgba(255, 255, 255, 0.9);
        border: 2px dashed var(--secondary-color);
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: var(--card-shadow);
        transition: var(--transition);
    }
    
    .upload-container:hover {
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
        transform: translateY(-3px);
    }
    
    /* 结果容器 - 添加悬浮效果 */
    .result-container {
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        box-shadow: var(--card-shadow);
        padding: 2rem;
        margin-top: 2rem;
        transition: var(--transition);
    }
    
    .result-container:hover {
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
        transform: translateY(-3px);
    }
    
    /* 按钮样式 - 改进主按钮，添加宽边框，确保不换行 */
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border: 2px solid var(--primary-color);
        padding: 0.75rem 1.5rem;
        font-size: 0.9375rem;
        cursor: pointer;
        border-radius: 8px;
        transition: var(--transition);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        white-space: nowrap;
        overflow: visible;
        min-width: auto;
    }
    
    .stButton>button:hover {
        background-color: #0c3d66;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        border-color: #0c3d66;
    }
    
    .stButton>button:focus {
        outline: 2px solid var(--secondary-color);
        box-shadow: 0 0 0 3px rgba(23, 162, 184, 0.25);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* 主按钮特殊样式 - 确保"开始分析"按钮不换行且边框加宽 */
    .stButton>button[type="primary"] {
        background-color: var(--secondary-color);
        border: 3px solid var(--secondary-color);
        padding: 0.8rem 2rem;
        font-weight: 600;
        min-width: 150px;
        font-size: 0.9375rem;
    }
    
    .stButton>button[type="primary"]:hover {
        background-color: white;
        color: var(--secondary-color);
        border-color: var(--secondary-color);
        box-shadow: 0 6px 15px rgba(23, 162, 184, 0.2);
    }
    
    /* 信息框样式 */
    .info-box {
        background-color: rgba(227, 242, 253, 0.9);
        border-left: 4px solid var(--secondary-color);
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        transition: var(--transition);
    }
    
    .info-box:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    /* 成功/错误/警告框样式 */
    .success-box, .error-box, .warning-box {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        transition: var(--transition);
    }
    
    .success-box {
        background-color: rgba(232, 245, 233, 0.9);
        border-left: 4px solid #4caf50;
    }
    
    .error-box {
        background-color: rgba(255, 235, 238, 0.9);
        border-left: 4px solid #f44336;
    }
    
    .warning-box {
        background-color: rgba(255, 255, 224, 0.9);
        border-left: 4px solid #ff9800;
    }
    
    /* 卡片样式 - 统一现代化风格 */
    .stExpander {
        border-radius: 15px !important;
        margin-bottom: 1rem;
        overflow: hidden;
        transition: var(--transition);
        border: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .stExpander:hover {
        box-shadow: var(--card-shadow);
    }
    
    .stExpanderDetails {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 0 0 15px 15px;
    }
    
    /* 标题样式 - 减小标题大小 */
    h1 {
        color: var(--text-color);
        font-size: 1.875rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.75rem !important;
    }
    
    h2, h3, h4, h5, h6 {
        color: var(--text-color);
    }
    
    /* 输入框样式 */
    .stTextInput>div>div>input {
        border-radius: 8px;
        border: 1px solid #ddd;
        transition: var(--transition);
    }
    
    .stTextInput>div>div>input:focus {
        border-color: var(--secondary-color);
        box-shadow: 0 0 0 2px rgba(23, 162, 184, 0.2);
    }
    
    /* 复选框样式 */
    .stCheckbox>label {
        color: var(--text-color);
        transition: var(--transition);
    }
    
    /* 功能块容器 - 统一现代化风格 */
    .feature-block {
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--card-shadow);
        transition: var(--transition);
        border: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .feature-block:hover {
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
        transform: translateY(-3px);
    }
</style>
""", unsafe_allow_html=True)

# 标题 - 减小字体大小，在标题内添加立体效果背景
st.markdown('<h1 style="font-size: 1.875rem; font-weight: 700; color: white; margin: 0 0 1rem 0; padding: 0.5rem 1rem; background: linear-gradient(135deg, #0f4c81 0%, #17a2b8 100%); border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">📊 股权结构图表生成器</h1>', unsafe_allow_html=True)

# 简介
st.markdown("""
本工具可以帮助您从图片中提取股权结构信息，并生成交互式的 Mermaid 图表。
支持全屏查看、缩放拖拽和文本编辑功能。
""")

# 文件上传区域
uploaded_file = st.file_uploader("📁 上传股权结构图", type=["png", "jpg", "jpeg"])

if uploaded_file:
    # 显示上传的图片预览
    st.image(uploaded_file, caption="上传的图片预览", use_container_width=True)

# 测试数据加载按钮 - 移除公司名称
if st.button("🧪 加载测试数据", type="secondary"):
    with st.spinner("正在加载测试数据..."):
        try:
            test_data_rel_path = Path("archive") / "examples_backup_20251001" / "translated_test_data.json"
            test_data_path = resolve_resource_path(test_data_rel_path)

            if not test_data_path.exists():
                raise FileNotFoundError(f"测试数据文件不存在: {test_data_path}")

            # 读取测试数据文件
            with open(test_data_path, "r", encoding="utf-8") as f:
                test_data = json.load(f)
                
            # 确保数据格式正确
            if "core_company" in test_data and "entity_relationships" in test_data:
                # 转换数据格式以匹配应用所需格式
                transformed_data = {
                    "main_company": test_data.get("core_company", "未知公司"),
                    "shareholders": test_data.get("shareholders", []),
                    "subsidiaries": test_data.get("subsidiaries", []),
                    "controller": test_data.get("controller", ""),
                    "top_level_entities": test_data.get("top_level_entities", []),
                    "entity_relationships": test_data.get("entity_relationships", []),
                    "control_relationships": test_data.get("control_relationships", []),
                    "all_entities": test_data.get("all_entities", [])
                }
                
                # 生成Mermaid代码
                mermaid_code = generate_mermaid_diagram(transformed_data)
                
                # 保存到会话状态
                st.session_state.mermaid_code = mermaid_code
                st.session_state.extracted_data = transformed_data
                st.session_state.json_data = json.dumps(transformed_data, ensure_ascii=False, indent=2)
                
                st.success("✅ 测试数据加载成功！")
                st.markdown("### 📈 股权结构图表")
                
                # 渲染Mermaid图表
                st_mermaid(st.session_state.mermaid_code)
            else:
                st.error("❌ 测试数据格式不正确，缺少必要字段")
        except FileNotFoundError as fnf_err:
            st.error(f"❌ 找不到测试数据文件 translated_test_data.json\n{fnf_err}")
        except json.JSONDecodeError:
            st.error("❌ 测试数据文件格式错误")
        except Exception as e:
            st.error(f"❌ 加载测试数据时出错: {str(e)}")

# API配置区域
with st.expander("⚙️ API配置", expanded=True):
    st.session_state.use_real_api = st.checkbox("使用阿里云通义千问API进行图片分析", value=st.session_state.use_real_api)
    
    if st.session_state.use_real_api:
        st.session_state.api_key = st.text_input("DashScope API密钥", value=st.session_state.api_key, type="password", placeholder="输入您的DashScope API密钥")
        
        # 显示API使用说明
        st.info("📝 提示: 使用阿里云通义千问视觉模型(qwen3-vl-plus)进行图片分析。如果API调用失败，系统将自动回退到模拟数据。")
    else:
        st.info("🔧 当前使用模拟数据模式。勾选上方选项可切换至真实API模式。")
    
    # 添加翻译选项
    st.divider()
    st.session_state.translate_to_english = st.checkbox("将中文股权信息翻译成英文", value=st.session_state.translate_to_english)
    
    if st.session_state.translate_to_english:
        st.info("🌐 提示: 启用翻译功能后，生成的图表将显示英文公司名称和股东名称。请确保已在config.json中配置好阿里云AccessKey或设置了相关环境变量。")
    
    # 检查翻译配置
    try:
        access_key_id, access_key_secret = None, None
        # 检查config.json
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 首先尝试alicloud_translator键（与test_config.py匹配）
                if 'alicloud_translator' in config and 'access_key_id' in config['alicloud_translator'] and 'access_key_secret' in config['alicloud_translator']:
                    access_key_id = config['alicloud_translator']['access_key_id']
                    access_key_secret = config['alicloud_translator']['access_key_secret']
                # 同时支持alicloud键作为兼容选项
                elif 'alicloud' in config and 'access_key_id' in config['alicloud'] and 'access_key_secret' in config['alicloud']:
                    access_key_id = config['alicloud']['access_key_id']
                    access_key_secret = config['alicloud']['access_key_secret']
        
        # 检查环境变量
        if not access_key_id or not access_key_secret:
            access_key_id = os.environ.get('ALICLOUD_ACCESS_KEY_ID')
            access_key_secret = os.environ.get('ALICLOUD_ACCESS_KEY_SECRET')
        
        if st.session_state.translate_to_english and not (access_key_id and access_key_secret):
            st.warning("⚠️ 未找到阿里云翻译API的AccessKey配置。翻译功能可能无法正常工作。请在config.json中配置或设置环境变量。")
    except Exception as e:
        st.warning(f"⚠️ 检查翻译配置时出错: {str(e)}")

# 分析按钮 - 移除columns布局避免换行，直接设置按钮样式
analyze_button = st.button("🔍 开始分析", type="primary", use_container_width=True)

# 使用阿里云通义千问视觉模型分析图片的函数
def analyze_image_with_llm(image_bytes, file_name=None):
    """
    使用阿里云通义千问视觉模型分析图片中的股权结构信息
    image_bytes: 图片文件字节内容
    file_name: 文件名（可选，用于生成不同的模拟数据）
    返回: 提取的股权结构数据字典
    """
    try:
        # 从会话状态获取API配置
        use_real_api = st.session_state.use_real_api
        api_key = st.session_state.api_key
        
        # 验证API配置是否有效
        if use_real_api:
            if not api_key:
                st.warning("⚠️ API密钥未设置，将使用模拟数据")
                use_real_api = False
            else:
                st.info("🔍 使用阿里云通义千问视觉模型分析图片...")
        
        if use_real_api:
            # 延迟导入，仅在使用真实API时导入dashscope，避免冷启动加载
            import dashscope
            from dashscope import MultiModalConversation
            # 设置DashScope API密钥
            dashscope.api_key = api_key
            
            # 将图片字节转换为base64编码，并添加适当的MIME类型前缀
            import base64
            image_base64 = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            
            # 构建请求消息
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的股权结构图分析助手，擅长从图片中提取公司股权关系信息。请严格按照要求的JSON格式输出，不要添加任何额外的解释或文本。特别注意识别所有层级的公司，包括中间层级！"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "请仔细分析这张股权结构图，并严格按照以下要求提取信息：\n"
                                "\n"
                                "1. 请从左到右、从上到下的顺序扫描图片，确保不遗漏任何实体，特别是中间层级的公司。\n"
                                "2. 识别图中所有的实体（公司、股东、个人等），包括所有层级的结构。\n"
                                "3. 提取实体名称和持股比例或出资比例（如果有）。\n"
                                "   - ✅ 实体名称必须完整保留图中显示的所有文字，包括括号内的全部内容（如\"(HKEX listed: 01931)\"、\"(JP registered)\"、\"(A/R debtor 1)\"、\"(A/R seller)\"等），不得省略、截断或简化。\n"
                                "   - 例如：\"IVD Medical Holding Limited (HKEX listed: 01931)\" 必须完整作为实体名称，不能只写 \"IVD Medical Holding Limited\"。\n"
                                "4. 重要要求：即使图片中信息不完整，也必须尝试提取所有可识别的信息。不要返回空数据！对于持股比例，若未标明但有股权关系，请标注为0.1。\n"
                                "5. 特别注意：请识别并保留图片中的所有换行信息，包括每行描述的公司关系。\n"
                                "6. 请特别关注括号内的内容，这些内容通常包含重要的股权关系或注释信息。\n"
                                "   - 括号内内容是实体身份/属性的关键标识，必须作为实体名称的一部分提取，不可剥离。\n"
                                "7. 请特别注意图中的虚线连接。虚线通常表示\"控制关系\"、\"关联关系\"或\"非直接持股但具有影响力\"。\n"
                                "   - 对于每条虚线，请在 control_relationships 字段中单独记录。\n"
                                "   - 必须标注 relationship_type（如 \"ultimate_control\"、\"collective_control\"、\"indirect_ownership\"、\"related_party\" 等），并尽可能保留图中标注的文字（如 \"ultimate control\"、\"Collective control\"）作为 description。\n"
                                "   - 虚线关系不涉及具体持股比例时，percentage 字段可留空或设为标准的文字。\n"
                                "   - 不要将虚线关系混入 entity_relationships，必须分开存储！\n"
                                "8. 必须确保返回格式严格为JSON，不要包含任何其他文本！\n"
                                "\n请将提取的信息严格按照以下JSON格式输出，只输出JSON，不要输出任何其他内容：\n"
                                "{\n"
                                "  \"core_company\": \"核心公司名称\",\n"
                                "  \"shareholders\": [\n"
                                "    {\n"
                                "      \"name\": \"股东名称\",\n"
                                "      \"percentage\": 持股比例数字\n"
                                "    },\n"
                                "    ...\n"
                                "  ],\n"
                                "  \"subsidiaries\": [\n"
                                "    {\n"
                                "      \"name\": \"子公司名称\",\n"
                                "      \"percentage\": 持股比例数字\n"
                                "    },\n"
                                "    ...\n"
                                "  ],\n"
                                "  \"controller\": \"实际控制人名称\",\n"
                                "  \"top_level_entities\": [\n"
                                "    {\n"
                                "      \"name\": \"最高层级实体1\",\n"
                                "      \"percentage\": 持股比例数字\n"
                                "    },\n"
                                "    ...\n"
                                "  ],\n"
                                "  \"entity_relationships\": [\n"
                                "    {\n"
                                "      \"parent\": \"上级公司名称\",\n"
                                "      \"child\": \"下级公司名称\",\n"
                                "      \"percentage\": 持股比例数字\n"
                                "    },\n"
                                "    ...\n"
                                "  ],\n"
                                "  \"control_relationships\": [\n"
                                "    {\n"
                                "      \"parent\": \"上级实体名称\",\n"
                                "      \"child\": \"下级实体名称\",\n"
                                "      \"relationship_type\": \"关系类型\",\n"
                                "      \"description\": \"关系描述\"\n"
                                "    },\n"
                                "    ...\n"
                                "  ],\n"
                                "  \"all_entities\": [\n"
                                "    {\n"
                                "      \"name\": \"实体名称\",\n"
                                "      \"type\": \"company或person\"\n"
                                "    },\n"
                                "    ...\n"
                                "  ]\n"
                                "}\n"
                                "\n特别注意：\n"
                                "- entity_relationships字段必须包含所有层级之间的股权关系，不能遗漏任何中间层级！\n"
                                "- control_relationships字段必须包含所有虚线连接的控制关系，不能混入entity_relationships！\n"
                                "- all_entities字段必须列出图中所有实体，包括最高层、中间层和底层！\n"
                                "- 对于股权结构图，必须识别并提取至少3-5个层级的公司关系，而不仅仅是顶层和底层！\n"
                                "- 当存在多层持股关系时，如'A持有B 100%, B持有C 95%'，请确保在entity_relationships中分别记录'A-B'和'B-C'的关系，而不是错误地记录为'A-C'。\n"
                                "\n⚠️ 强制规则：所有实体名称必须完整复制图中显示的原始文本，包括括号、空格、换行符、注册地、上市代码、标签等，禁止任何形式的简化或省略。\n"
                                "\n请确保你的回答只包含上述格式的JSON，不要有任何额外的开头、结尾或解释性文字。"
                            )
                        },
                        {
                            "type": "image",
                            "image": image_base64
                        }
                    ]
                }
            ]
            
            # 调用阿里云通义千问视觉模型
            response = MultiModalConversation.call(
                model='qwen3-vl-plus',
                messages=messages,
                temperature=0.01,  # 更低温度，减少自由发挥
                seed=12345         # 提高可重复性
            )
            
            # 检查响应状态
            if response.status_code != 200:
                raise Exception(f"API Error: {response.code} - {response.message}")
            
            # 获取模型返回的文本
            text_output = ""
            try:
                contents = response.output.choices[0].message.content
                for item in contents:
                    if item.get("text"):
                        text_output = item["text"].strip()
                        break
            except Exception as e:
                raise Exception(f"解析模型输出失败: {e}")
            
            # 安全提取 JSON
            extracted_data = extract_json_from_text(text_output)
            st.success("✅ 成功使用阿里云通义千问视觉模型分析图片")
            
            # 添加调试信息
            st.write("📊 原始API返回数据:")
            st.json(extracted_data)
            
            # 检查返回数据是否为空
            if not extracted_data or all(not v for v in extracted_data.values()):
                st.warning("⚠️ API返回的数据为空，请检查图片质量或内容是否清晰可见")
                # 返回一个基本的数据结构，但使用与API一致的键名
                # 这样后续处理逻辑可以保持统一
                extracted_data = {
                    "core_company": "未识别到公司",
                    "shareholders": [],
                    "subsidiaries": [],
                    "controller": "",
                    "top_level_entities": []
                }
            
            # 转换数据格式为应用所需的格式
            # 更健壮的格式转换，支持两种可能的返回格式
            transformed_data = {
                "main_company": extracted_data.get("core_company", "") or extracted_data.get("main_company", "未知公司"),
                "shareholders": [],
                "subsidiaries": [],
                "controller": extracted_data.get("controller", ""),
                "top_level_entities": extracted_data.get("top_level_entities", []),
                "entity_relationships": extracted_data.get("entity_relationships", []),
                "control_relationships": extracted_data.get("control_relationships", []),
                "all_entities": extracted_data.get("all_entities", [])
            }
            
            # 转换股东数据 - 支持两种可能的字段名
            shareholders_source = extracted_data.get("shareholders", [])
            if shareholders_source:
                for sh in shareholders_source:
                    try:
                        shareholder_data = {}
                        # 提取名称
                        if "name" in sh:
                            shareholder_data["name"] = sh["name"]
                        else:
                            st.warning(f"⚠️ 股东数据缺少name字段: {sh}")
                            continue
                        
                        # 处理百分比 - 支持ratio和percentage两种可能
                        if "ratio" in sh:
                            shareholder_data["percentage"] = float(sh["ratio"]) * 100  # 转换为百分比
                        elif "percentage" in sh:
                            shareholder_data["percentage"] = float(sh["percentage"])
                        else:
                            st.warning(f"⚠️ 股东{sh.get('name', '未知')}缺少持股比例信息")
                            shareholder_data["percentage"] = 0
                        
                        # 添加连接线类型信息（如果有）
                        if "connection_type" in sh:
                            shareholder_data["connection_type"] = sh["connection_type"]
                        
                        transformed_data["shareholders"].append(shareholder_data)
                    except Exception as e:
                        st.error(f"⚠️ 处理股东数据时出错: {e}")
            
            # 转换子公司数据 - 支持两种可能的字段名
            subsidiaries_source = extracted_data.get("subsidiaries", [])
            if subsidiaries_source:
                for sub in subsidiaries_source:
                    try:
                        subsidiary_data = {}
                        # 提取名称
                        if "name" in sub:
                            subsidiary_data["name"] = sub["name"]
                        else:
                            st.warning(f"⚠️ 子公司数据缺少name字段: {sub}")
                            continue
                        
                        # 处理百分比 - 支持ratio和percentage两种可能
                        if "ratio" in sub:
                            subsidiary_data["percentage"] = float(sub["ratio"]) * 100  # 转换为百分比
                        elif "percentage" in sub:
                            subsidiary_data["percentage"] = float(sub["percentage"])
                        else:
                            st.warning(f"⚠️ 子公司{sub.get('name', '未知')}缺少持股比例信息")
                            subsidiary_data["percentage"] = 0
                        
                        # 添加连接线类型信息（如果有）
                        if "connection_type" in sub:
                            subsidiary_data["connection_type"] = sub["connection_type"]
                        
                        transformed_data["subsidiaries"].append(subsidiary_data)
                    except Exception as e:
                        st.error(f"⚠️ 处理子公司数据时出错: {e}")
            
            # 统一的返回逻辑，无论子公司数据是否存在
            # 检查是否需要翻译
            if st.session_state.translate_to_english:
                st.info("🌐 正在翻译股权结构信息...")
                try:
                    transformed_data = translate_equity_data(transformed_data, translate_names=True)
                except Exception as e:
                    st.warning(f"⚠️ 翻译过程中出现错误，但将继续使用原始数据: {str(e)}")
            
            return transformed_data
        else:
            # 使用模拟数据
            st.info("⚠️ 使用模拟数据分析")
            
            # 根据文件名返回不同的模拟数据
            file_name_lower = "未知文件" if not file_name else file_name.lower()
            
            # 根据文件名返回不同的模拟数据
            if "nanfang" in file_name_lower:
                extracted_data = {
                    "main_company": "南方科技有限公司",
                    "shareholders": [
                        {"name": "张三", "percentage": 60.5, "connection_type": "solid"},
                        {"name": "李四", "percentage": 20.3, "connection_type": "solid"},
                        {"name": "王五", "percentage": 19.2, "connection_type": "dashed"}
                    ],
                    "subsidiaries": [
                        {"name": "南方电子科技有限公司", "percentage": 100, "connection_type": "solid"},
                        {"name": "南方创新中心", "percentage": 80, "connection_type": "solid"}
                    ],
                    "controller": "",
                    "top_level_entities": [
                        {"name": "张三", "type": "自然人", "control_type": "direct"}
                    ],
                }
            elif "test" in file_name_lower:
                extracted_data = {
                    "main_company": "测试公司",
                    "shareholders": [
                        {"name": "测试用户1", "percentage": 45.0, "connection_type": "solid"},
                        {"name": "测试用户2", "percentage": 30.0, "connection_type": "solid"},
                        {"name": "测试用户3", "percentage": 25.0, "connection_type": "dashed"}
                    ],
                    "subsidiaries": [
                        {"name": "测试子公司A", "percentage": 75, "connection_type": "solid"},
                        {"name": "测试子公司B", "percentage": 60, "connection_type": "solid"}
                    ],
                    "controller": "",
                    "top_level_entities": [
                        {"name": "测试用户1", "type": "自然人", "control_type": "direct"},
                        {"name": "测试用户2", "type": "自然人", "control_type": "direct"}
                    ],
                }
            else:
                # 默认数据
                extracted_data = {
                   "main_company": "深圳市美鹏健康管理有限公司 (Lessee)", 
                   "shareholders": [ 
                     { 
                       "name": "南通美富健康产业发展合伙企业 (有限合伙)", 
                       "percentage": 48.5 
                     }, 
                     { 
                       "name": "深圳美年大健康健康管理有限公司", 
                       "percentage": 43.9 
                     }, 
                     { 
                       "name": "Ms. Wang Ting", 
                       "percentage": 7.6 
                     } 
                   ], 
                   "subsidiaries": [], 
                   "controller": "", 
                   "top_level_entities": [ 
                     { 
                       "name": "MOF(财政部)", 
                       "percentage": 0.1 
                     }, 
                     { 
                       "name": "Mr. Yu Rong", 
                       "percentage": 10.53 
                     } 
                   ], 
                   "entity_relationships": [ 
                     { 
                       "parent": "MOF(财政部)", 
                       "child": "北京东富通达投资管理中心 (有限合伙)", 
                       "percentage": 0.1 
                     }, 
                     { 
                       "parent": "Mr. Yu Rong", 
                       "child": "美年大健康产业控股股份有限公司", 
                       "percentage": 10.53 
                     }, 
                     { 
                       "parent": "北京东富通达投资管理中心 (有限合伙)", 
                       "child": "南通美富健康产业发展合伙企业 (有限合伙)", 
                       "percentage": 80.8 
                     }, 
                     { 
                       "parent": "北京东富通达投资管理中心 (有限合伙)", 
                       "child": "深圳美年大健康健康管理有限公司", 
                       "percentage": 18.9 
                     }, 
                     { 
                       "parent": "美年大健康产业控股股份有限公司", 
                       "child": "深圳美年大健康健康管理有限公司", 
                       "percentage": 100.0 
                     }, 
                     { 
                       "parent": "南通美富健康产业发展合伙企业 (有限合伙)", 
                       "child": "深圳市美鹏健康管理有限公司 (Lessee)", 
                       "percentage": 48.5 
                     }, 
                     { 
                       "parent": "深圳美年大健康健康管理有限公司", 
                       "child": "深圳市美鹏健康管理有限公司 (Lessee)", 
                       "percentage": 43.9 
                     }, 
                     { 
                       "parent": "Ms. Wang Ting", 
                       "child": "深圳市美鹏健康管理有限公司 (Lessee)", 
                       "percentage": 7.6 
                     } 
                   ], 
                   "all_entities": [ 
                     { 
                       "name": "MOF(财政部)", 
                       "type": "company" 
                     }, 
                     { 
                       "name": "Mr. Yu Rong", 
                       "type": "person" 
                     }, 
                     { 
                       "name": "北京东富通达投资管理中心 (有限合伙)", 
                       "type": "company" 
                     }, 
                     { 
                       "name": "美年大健康产业控股股份有限公司", 
                       "type": "company" 
                     }, 
                     { 
                       "name": "南通美富健康产业发展合伙企业 (有限合伙)", 
                       "type": "company" 
                     }, 
                     { 
                       "name": "深圳美年大健康健康管理有限公司", 
                       "type": "company" 
                     }, 
                     { 
                       "name": "Ms. Wang Ting", 
                       "type": "person" 
                     }, 
                     { 
                       "name": "深圳市美鹏健康管理有限公司 (Lessee)", 
                       "type": "company" 
                     } 
                   ] 
                }
            
            # 检查是否需要翻译
            if st.session_state.translate_to_english:
                st.info("🌐 正在翻译股权结构信息...")
                try:
                    extracted_data = translate_equity_data(extracted_data, translate_names=True)
                except Exception as e:
                    st.warning(f"⚠️ 翻译模拟数据时出现错误，但将继续使用原始数据: {str(e)}")
        
        return extracted_data
        
    except Exception as e:
        st.error(f"❌ API调用失败: {str(e)}")
        # 出错时回退到模拟数据
        st.info("💡 正在回退到模拟数据...")
        
        # 默认模拟数据
        extracted_data = {
            "main_company": "桑果健康科技发展（上海）有限公司",
            "shareholders": [
                {"name": "田桑", "percentage": 51.3287, "connection_type": "solid"},
                {"name": "上海桑比科技合伙企业（有限合伙）", "percentage": 22.6713, "connection_type": "solid"},
                {"name": "上海鸿保信息技术中心（有限合伙）", "percentage": 20.0, "connection_type": "solid"},
                {"name": "上海时桑科技合伙企业（有限合伙）", "percentage": 6.0, "connection_type": "dashed"}
            ],
            "subsidiaries": [
                {"name": "桑果（上海）信息技术有限公司", "percentage": 100, "connection_type": "solid"},
                {"name": "成都双流桑果互联网医院有限公司", "percentage": 100, "connection_type": "solid"},
                {"name": "桑果健康科技发展（无锡）有限公司", "percentage": 70, "connection_type": "solid"},
                {"name": "海南桑果健康科技有限公司", "percentage": 60, "connection_type": "solid"},
                {"name": "上海柏青健康科技有限公司", "percentage": 5, "connection_type": "dashed"}
            ],
            "controller": "",
            "top_level_entities": [
                {"name": "田桑", "type": "自然人", "control_type": "direct"}
            ]
        }
        
        # 检查是否需要翻译
        if st.session_state.translate_to_english:
            try:
                extracted_data = translate_equity_data(extracted_data, translate_names=True)
            except Exception:
                st.warning("⚠️ 翻译失败，将使用原始中文数据")
        
        return extracted_data

# 分析逻辑
if analyze_button and uploaded_file:
    with st.spinner("正在分析图片..."):
        try:
            # 读取图片文件内容
            image_bytes = uploaded_file.read()
            
            # 调用大模型分析函数，传递文件名
            extracted_data = analyze_image_with_llm(image_bytes, uploaded_file.name)
            
            # 生成Mermaid代码
            mermaid_code = generate_mermaid_diagram(extracted_data)
            
            # 保存到会话状态
            st.session_state.mermaid_code = mermaid_code
            st.session_state.extracted_data = extracted_data
            st.session_state.json_data = json.dumps(extracted_data, ensure_ascii=False, indent=2)
            
            st.success("✅ 分析完成！")
            st.markdown("### 📈 股权结构图表")
            
            # 渲染Mermaid图表
            st_mermaid(st.session_state.mermaid_code)
            
        except Exception as e:
            st.error(f"❌ 分析过程中出现错误: {str(e)}")
            st.info("提示：请确保API连接正常，并检查图片质量。")
            # 出错时使用模拟数据作为备选
            st.session_state.extracted_data = {
               "main_company": "深圳市美鹏健康管理有限公司 (Lessee)", 
               "shareholders": [ 
                 { 
                   "name": "南通美富健康产业发展合伙企业 (有限合伙)", 
                   "percentage": 48.5 
                 }, 
                 { 
                   "name": "深圳美年大健康健康管理有限公司", 
                   "percentage": 43.9 
                 }, 
                 { 
                   "name": "Ms. Wang Ting", 
                   "percentage": 7.6 
                 } 
               ], 
               "subsidiaries": [], 
               "controller": "", 
               "top_level_entities": [ 
                 { 
                   "name": "MOF(财政部)", 
                   "percentage": 0.1 
                 }, 
                 { 
                   "name": "Mr. Yu Rong", 
                   "percentage": 10.53 
                 } 
               ], 
               "entity_relationships": [ 
                 { 
                   "parent": "MOF(财政部)", 
                   "child": "北京东富通达投资管理中心 (有限合伙)", 
                   "percentage": 0.1 
                 }, 
                 { 
                   "parent": "Mr. Yu Rong", 
                   "child": "美年大健康产业控股股份有限公司", 
                   "percentage": 10.53 
                 }, 
                 { 
                   "parent": "北京东富通达投资管理中心 (有限合伙)", 
                   "child": "南通美富健康产业发展合伙企业 (有限合伙)", 
                   "percentage": 80.8 
                 }, 
                 { 
                   "parent": "北京东富通达投资管理中心 (有限合伙)", 
                   "child": "深圳美年大健康健康管理有限公司", 
                   "percentage": 18.9 
                 }, 
                 { 
                   "parent": "美年大健康产业控股股份有限公司", 
                   "child": "深圳美年大健康健康管理有限公司", 
                   "percentage": 100.0 
                 }, 
                 { 
                   "parent": "南通美富健康产业发展合伙企业 (有限合伙)", 
                   "child": "深圳市美鹏健康管理有限公司 (Lessee)", 
                   "percentage": 48.5 
                 }, 
                 { 
                   "parent": "深圳美年大健康健康管理有限公司", 
                   "child": "深圳市美鹏健康管理有限公司 (Lessee)", 
                   "percentage": 43.9 
                 }, 
                 { 
                   "parent": "Ms. Wang Ting", 
                   "child": "深圳市美鹏健康管理有限公司 (Lessee)", 
                   "percentage": 7.6 
                 } 
               ], 
               "all_entities": [ 
                 { 
                   "name": "MOF(财政部)", 
                   "type": "company" 
                 }, 
                 { 
                   "name": "Mr. Yu Rong", 
                   "type": "person" 
                 }, 
                 { 
                   "name": "北京东富通达投资管理中心 (有限合伙)", 
                   "type": "company" 
                 }, 
                 { 
                   "name": "美年大健康产业控股股份有限公司", 
                   "type": "company" 
                 }, 
                 { 
                   "name": "南通美富健康产业发展合伙企业 (有限合伙)", 
                   "type": "company" 
                 }, 
                 { 
                   "name": "深圳美年大健康健康管理有限公司", 
                   "type": "company" 
                 }, 
                 { 
                   "name": "Ms. Wang Ting", 
                   "type": "person" 
                 }, 
                 { 
                   "name": "深圳市美鹏健康管理有限公司 (Lessee)", 
                   "type": "company" 
                 } 
               ] 
            }
            
            # 检查是否需要翻译
            if st.session_state.translate_to_english:
                try:
                    st.session_state.extracted_data = translate_equity_data(st.session_state.extracted_data, translate_names=True)
                except Exception:
                    st.warning("⚠️ 翻译失败，将使用原始中文数据")
            
            st.session_state.mermaid_code = generate_mermaid_diagram(st.session_state.extracted_data)
            st.session_state.json_data = json.dumps(st.session_state.extracted_data, ensure_ascii=False, indent=2)
            st.success("✅ 已使用模拟数据生成图表")
            st.markdown("### 📈 股权结构图表")
            
            # 渲染Mermaid图表
            st_mermaid(st.session_state.mermaid_code)

# 显示结果
if st.session_state.mermaid_code:
    # 显示图表容器
    st.markdown("<div class='result-container'>", unsafe_allow_html=True)
    
    # 图表操作按钮
    col_op1, col_op2, col_op3 = st.columns(3)
    with col_op1:
        # 全屏查看按钮 - 使用增强版HTML
        if st.button("🔍 全屏查看 (带编辑器)", type="primary", use_container_width=True):
            # 获取Mermaid代码内容
            mermaid_code_content = st.session_state.mermaid_code
            
            # 创建HTML模板，使用raw字符串避免转义问题
            html_template = r'''
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Mermaid 预览器（双击同步修改代码）</title>
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      height: 100vh;
      overflow: hidden;
    }
    .header {
      padding: 12px 20px;
      background: #f8f9fa;
      border-bottom: 1px solid #e0e0e0;
      font-size: 16px;
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }
    .controls {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .controls input {
      padding: 4px 8px;
      font-size: 14px;
      border: 1px solid #ccc;
      border-radius: 4px;
    }
    .controls button {
      padding: 4px 10px;
      font-size: 14px;
      cursor: pointer;
    }
    .container {
      display: flex;
      height: calc(100vh - 80px);
      overflow: hidden;
    }
    #editor {
      height: 100%;
      min-width: 300px;
      max-width: 70%;
      display: flex;
      flex-direction: column;
      background: #fff;
    }
    #preview-container {
      flex: 1;
      min-width: 300px;
      height: 100%;
      display: flex;
      flex-direction: column;
      background: white;
      overflow: hidden;
    }
    #editor textarea {
      flex: 1;
      padding: 14px;
      font-family: 'Consolas', monospace;
      font-size: 13px;
      line-height: 1.4;
      border: none;
      outline: none;
      resize: none;
      background: #fff;
      overflow: auto;
    }
    #preview {
      flex: 1;
      padding: 20px;
      overflow: hidden;
      display: flex;
      justify-content: center;
      align-items: center;
      position: relative;
      cursor: default;
    }
    #preview svg {
      max-width: 100%;
      max-height: 100%;
      cursor: pointer;
    }
    #preview svg text {
      cursor: pointer;
      user-select: none;
    }
    #preview svg text:hover {
      fill: #1976d2 !important;
      font-weight: bold !important;
    }
    #preview.dragging {
      cursor: grab;
    }
    #preview.dragging svg {
      cursor: grabbing !important;
    }
    #resizer {
      width: 6px;
      background: #e0e0e0;
      cursor: col-resize;
      user-select: none;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    #resizer:hover { background: #ccc; }
    #resizer::after {
      content: "⋮⋮";
      color: #999;
      font-size: 14px;
      writing-mode: vertical-rl;
    }
    .error {
      padding: 10px;
      color: #d32f2f;
      background: #ffebee;
      font-family: monospace;
      white-space: pre-wrap;
    }
    .fullscreen #editor,
    .fullscreen #resizer {
      display: none;
    }
    .fullscreen .container {
      height: calc(100vh - 60px);
    }
    .fullscreen #preview-container {
      position: relative;
    }
    .zoom-controls {
      position: absolute;
      bottom: 20px;
      right: 20px;
      background-color: white;
      border-radius: 25px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      padding: 5px;
      z-index: 1000; /* 提高层级确保在全屏模式下可见 */
    }
    .zoom-btn {
      background-color: #f8f9fa;
      border: none;
      border-radius: 50%;
      width: 35px;
      height: 35px;
      margin: 0 5px;
      font-size: 18px;
      cursor: pointer;
      transition: background-color 0.3s;
    }
    .zoom-btn:hover {
      background-color: #e9ecef;
    }
    .zoom-value {
      display: inline-block;
      line-height: 35px;
      padding: 0 10px;
      color: #495057;
      font-size: 14px;
    }
    .close-btn {
      background-color: #dc3545;
      color: white;
      border: none;
      padding: 4px 10px;
      font-size: 14px;
      cursor: pointer;
      border-radius: 4px;
    }
    .close-btn:hover {
      background-color: #c82333;
      color: white;
    }
  </style>
</head>
<body>
  <div class="header">
    📊 Mermaid 预览器（双击节点同步修改代码）
    <div class="controls">
        <input type="text" id="keywordInput" placeholder="输入关键词高亮">
        <button id="highlightBtn">高亮</button>
        <button id="clearBtn">清除高亮</button>
        <button id="fullscreenBtn">全屏预览</button>
        <button id="downloadPngBtn">下载PNG</button>
        <button class="close-btn" onclick="window.close()">关闭页面</button>
      </div>
  </div>
  <div class="container">
    <div id="editor">
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 14px; background: #f8f9fa; border-bottom: 1px solid #e0e0e0;">
        <span style="font-size: 12px; color: #666;">Mermaid 代码</span>
        <button id="copyCodeBtn" style="padding: 4px 8px; font-size: 12px; cursor: pointer;">复制代码</button>
      </div>
      <textarea id="source" spellcheck="false">CODE_PLACEHOLDER</textarea>
    </div>
    <div id="resizer"></div>
    <div id="preview-container">
      <div id="preview"></div>
      <div class="zoom-controls">
        <button class="zoom-btn" onclick="zoomDiagram(-0.1)">-</button>
        <span class="zoom-value" id="zoom-value">100%</span>
        <button class="zoom-btn" onclick="zoomDiagram(0.1)">+</button>
        <button class="zoom-btn" onclick="resetZoom()">⟲</button>
      </div>
    </div>
  </div>

  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';

    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'antiscript',
      flowchart: {
        useMaxWidth: false,
        htmlLabels: false,
        curve: 'linear'
      },
      fontFamily: '"Segoe UI", sans-serif'
    });

    const source = document.getElementById('source');
    const preview = document.getElementById('preview');
    const editor = document.getElementById('editor');
    const resizer = document.getElementById('resizer');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const keywordInput = document.getElementById('keywordInput');
    const highlightBtn = document.getElementById('highlightBtn');
    const clearBtn = document.getElementById('clearBtn');

    let currentSvgEl = null;
    let isFullscreen = false;
    let scale = 1;
    let translateX = 0;
    let translateY = 0;

    editor.style.width = '30%';

    // 工具函数
    function escapeRegExp(string) {
      // 简单的转义函数，避免复杂的正则表达式
      const specialChars = ['.', '*', '+', '?', '^', '$', '{', '}', '(', ')', '[', ']', '\\'];
      let result = string;
      for (const char of specialChars) {
        result = result.replace(new RegExp('\\' + char, 'g'), '\\' + char);
      }
      return result;
    }

    // 通过 nodeId + oldText 精准替换
    function updateMermaidCodeByNodeId(nodeId, oldText, newText) {
      const code = source.value;
      const escapedOld = escapeRegExp(oldText);
      const escapedNodeId = escapeRegExp(nodeId);
      
      // 构建简单的模式，避免复杂的正则表达式
      const patterns = [
        escapedNodeId + '\\$\\$\"' + escapedOld + '\"',
        escapedNodeId + '\\$\"' + escapedOld + '\\$',
        escapedNodeId + '\\{\"' + escapedOld + '\"\\}'
      ];

      for (const pattern of patterns) {
        try {
          const regex = new RegExp(pattern, 'g');
          const newCode = code.replace(regex, (match) => {
            return match.replace(escapedOld, newText);
          });
          if (newCode !== code) {
            source.value = newCode;
            render();
            return true;
          }
        } catch (e) {
          // 如果正则表达式失败，跳过
        }
      }

      // 宽松匹配 - 使用简单的字符串替换
      if (code.includes(escapedNodeId) && code.includes(escapedOld)) {
        let newCode = code;
        let replaced = false;
        // 尝试在包含nodeId的行中替换oldText
        const lines = code.split('\\n');
        for (let i = 0; i < lines.length; i++) {
          if (lines[i].includes(escapedNodeId) && lines[i].includes(escapedOld)) {
            // 只替换引号内的内容
            const parts = lines[i].split(/[\"\\']/);
            for (let j = 1; j < parts.length; j += 2) {
              if (parts[j].includes(oldText)) {
                parts[j] = parts[j].replace(oldText, newText);
                replaced = true;
                break;
              }
            }
            lines[i] = parts.join('"');
            if (replaced) break;
          }
        }
        newCode = lines.join('\\n');
        if (newCode !== code && replaced) {
          source.value = newCode;
          render();
          return true;
        }
      }

      return false;
    }

    // 通过全文本匹配
    function updateMermaidCodeByText(oldText, newText) {
      const code = source.value;
      // 统计oldText出现的次数
      const count = (code.match(new RegExp('"' + escapeRegExp(oldText) + '"', 'g')) || []).length;
      if (count !== 1) {
        return false;
      }

      // 简单的字符串替换
      const newCode = code.replace('"' + oldText + '"', '"' + newText + '"');
      if (newCode !== code) {
        source.value = newCode;
        render();
        return true;
      }
      return false;
    }

    // 渲染函数
    async function render() {
      const code = source.value.trim();
      preview.innerHTML = '';

      if (!code) {
        preview.textContent = '请输入 Mermaid 代码...';
        currentSvgEl = null;
        return;
      }

      try {
        const { svg: rawSvg } = await mermaid.render('chart', code);
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(rawSvg, 'image/svg+xml');
        currentSvgEl = svgDoc.documentElement;

        preview.innerHTML = '';
        preview.appendChild(currentSvgEl);

        applyTransform();

        // 绑定双击事件
        const texts = currentSvgEl.querySelectorAll('text');
        texts.forEach(text => {
          text.style.cursor = 'pointer';

          // 提取 nodeId
          let nodeId = '';
          let g = text.closest('g');
          if (g && g.id) {
            // 简化的nodeId提取，避免复杂的正则表达式
            const id = g.id;
            if (id.startsWith('flowchart-')) {
              // 移除'flowchart-'前缀和可能的数字后缀
              nodeId = id.replace('flowchart-', '').replace(/-[0-9]+$/, '');
            }
          }
          text.setAttribute('data-node-id', nodeId || 'unknown');
          text.setAttribute('data-original-text', text.textContent || '');

          const onDblClick = () => {
            const oldText = text.getAttribute('data-original-text') || text.textContent;
            const nodeId = text.getAttribute('data-node-id');
            const newText = prompt('请输入新节点文字：', oldText);
            if (newText === null || newText === oldText) return;

            // 更新 SVG
            text.textContent = newText;
            text.setAttribute('data-original-text', newText);
            const rect = text.closest('g')?.querySelector('rect');
            if (rect) {
              const x = parseFloat(rect.getAttribute('x')) || 0;
              const width = parseFloat(rect.getAttribute('width')) || 0;
              text.setAttribute('x', x + width / 2);
              text.setAttribute('text-anchor', 'middle');
            }

            // 尝试更新代码
            let updated = false;
            if (nodeId && nodeId !== 'unknown') {
              updated = updateMermaidCodeByNodeId(nodeId, oldText, newText);
            }
            if (!updated) {
              updated = updateMermaidCodeByText(oldText, newText);
            }
            if (!updated) {
              alert('未能自动更新代码，请手动修改左侧 Mermaid 内容。');
            }
          };

          text.removeEventListener('dblclick', onDblClick);
          text.addEventListener('dblclick', onDblClick);
        });

      } catch (e) {
        console.error(e);
        preview.innerHTML = '<div class="error">❌ ' + (e.message || e) + '</div>';
        currentSvgEl = null;
      }
    }

    function applyTransform() {
      if (currentSvgEl) {
        currentSvgEl.style.transformOrigin = '0 0';
        currentSvgEl.style.transform = 'scale(' + scale + ') translate(' + translateX + 'px, ' + translateY + 'px)';
        document.getElementById('zoom-value').textContent = Math.round(scale * 100) + '%';
      }
    }

    // 复制代码功能
    function copyCode() {
      const textarea = document.getElementById('source');
      textarea.select();
      textarea.setSelectionRange(0, 99999); // 兼容移动设备
      
      try {
        document.execCommand('copy');
        
        // 显示复制成功提示
        const originalText = copyCodeBtn.textContent;
        copyCodeBtn.textContent = '复制成功！';
        copyCodeBtn.style.backgroundColor = '#d4edda';
        copyCodeBtn.style.color = '#155724';
        copyCodeBtn.style.border = '1px solid #c3e6cb';
        
        setTimeout(() => {
          copyCodeBtn.textContent = originalText;
          copyCodeBtn.style.backgroundColor = '';
          copyCodeBtn.style.color = '';
          copyCodeBtn.style.border = '';
        }, 2000);
      } catch (err) {
        alert('复制失败，请手动复制代码');
        console.error('复制失败:', err);
      }
    }
    
    // 高亮函数 - 在代码区域查找文字
    function highlightKeyword(keyword) {
      const textarea = document.getElementById('source');
      
      if (!keyword.trim()) {
        // 如果关键字为空，清除高亮并显示提示
        clearHighlight();
        alert('请输入要查找的关键词');
        return;
      }
      
      // 清除之前的选择
      textarea.focus();
      
      // 获取文本内容
      const text = textarea.value;
      const keywordLower = keyword.toLowerCase();
      const textLower = text.toLowerCase();
      
      // 查找所有匹配项
      let matches = [];
      let pos = 0;
      while (pos < textLower.length) {
        const index = textLower.indexOf(keywordLower, pos);
        if (index === -1) break;
        matches.push({start: index, end: index + keyword.length});
        pos = index + 1;
      }
      
      if (matches.length === 0) {
        alert(`未找到关键词：${keyword}`);
        return;
      }
      
      // 高亮第一个匹配项
      textarea.setSelectionRange(matches[0].start, matches[0].end);
      
      // 滚动到可见区域
      textarea.scrollTop = Math.max(0, 
        (matches[0].start / text.length) * textarea.scrollHeight - textarea.clientHeight / 2);
      
      // 如果有多个匹配项，显示找到的数量
      if (matches.length > 1) {
        alert(`找到 ${matches.length} 处匹配，已选中第一个`);
      }
    }
    
    function clearHighlight() {
      const textarea = document.getElementById('source');
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    }

    // 拖拽平移逻辑
    let isDragging = false;
    let startX, startY, startTranslateX, startTranslateY;

    preview.addEventListener('mousedown', function(e) {
      // 移除全屏模式限制，允许在任何模式下拖拽
      if (e.target.tagName === 'text') return;

      isDragging = true;
      preview.classList.add('dragging');
      startX = e.clientX;
      startY = e.clientY;
      startTranslateX = translateX;
      startTranslateY = translateY;
      e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
      // 移除全屏模式限制，允许在任何模式下拖拽
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      translateX = startTranslateX + dx;
      translateY = startTranslateY + dy;
      applyTransform();
    });

    document.addEventListener('mouseup', function() {
      if (isDragging) {
        isDragging = false;
        preview.classList.remove('dragging');
      }
    });

    // 下载PNG功能
    function downloadPNG() {
      if (!currentSvgEl) {
        alert('没有可下载的图表，请先生成图表');
        return;
      }

      try {
        // 克隆SVG元素以避免修改原始视图
        const svgClone = currentSvgEl.cloneNode(true);
        
        // 移除可能导致问题的transform属性
        svgClone.removeAttribute('style');
        
        // 设置SVG尺寸
        const svgWidth = parseInt(svgClone.getAttribute('width') || '800');
        const svgHeight = parseInt(svgClone.getAttribute('height') || '600');
        svgClone.setAttribute('width', svgWidth);
        svgClone.setAttribute('height', svgHeight);
        
        // 创建内联SVG字符串
        const serializer = new XMLSerializer();
        const svgString = serializer.serializeToString(svgClone);
        
        // 创建Blob并转换为DataURL
        const blob = new Blob([svgString], {type: 'image/svg+xml'});
        const url = URL.createObjectURL(blob);
        
        // 创建Image对象加载SVG
        const img = new Image();
        img.onload = function() {
          // 创建Canvas
          const canvas = document.createElement('canvas');
          canvas.width = svgWidth;
          canvas.height = svgHeight;
          const ctx = canvas.getContext('2d');
          
          // 设置白色背景
          ctx.fillStyle = 'white';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          
          // 绘制图像
          ctx.drawImage(img, 0, 0);
          
          // 转换为PNG并下载
          canvas.toBlob(function(blob) {
            const downloadLink = document.createElement('a');
            downloadLink.download = '股权结构图_' + new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-') + '.png';
            downloadLink.href = URL.createObjectURL(blob);
            downloadLink.click();
            
            // 清理
            URL.revokeObjectURL(url);
            URL.revokeObjectURL(downloadLink.href);
          }, 'image/png');
        };
        
        img.onerror = function() {
          alert('图表转换失败，请重试');
          URL.revokeObjectURL(url);
        };
        
        img.crossOrigin = 'anonymous';
        img.src = url;
        
      } catch (error) {
        console.error('下载PNG失败:', error);
        alert('下载PNG失败，请重试');
      }
    }

    // 缩放函数
    function zoomDiagram(delta) {
      scale = Math.max(0.1, Math.min(3.0, scale + delta));
      applyTransform();
    }

    function resetZoom() {
      scale = 1;
      translateX = 0;
      translateY = 0;
      applyTransform();
    }

    // 事件绑定
    let timer;
    source.addEventListener('input', function() {
      clearTimeout(timer);
      timer = setTimeout(render, 400);
    });

    highlightBtn.addEventListener('click', function() {
      highlightKeyword(keywordInput.value);
    });

    clearBtn.addEventListener('click', function() {
      clearHighlight();
    });

    keywordInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') highlightKeyword(keywordInput.value);
    });

    // 复制代码按钮事件
    document.getElementById('copyCodeBtn').addEventListener('click', copyCode);

    // 下载PNG按钮事件
    document.getElementById('downloadPngBtn').addEventListener('click', downloadPNG);

    // 拖拽分割条
    let isResizing = false;
    resizer.addEventListener('mousedown', function(e) {
      isResizing = true;
      document.body.style.cursor = 'col-resize';
      e.preventDefault();
    });
    document.addEventListener('mousemove', function(e) {
      if (!isResizing) return;
      const containerRect = document.querySelector('.container').getBoundingClientRect();
      let leftPercent = ((e.clientX - containerRect.left) / containerRect.width) * 100;
      leftPercent = Math.max(10, Math.min(70, leftPercent));
      editor.style.width = leftPercent + '%';
      render();
    });
    document.addEventListener('mouseup', function() {
      isResizing = false;
      document.body.style.cursor = 'default';
    });

    // 全屏切换
    fullscreenBtn.addEventListener('click', function() {
      document.body.classList.toggle('fullscreen');
      isFullscreen = !isFullscreen;
      fullscreenBtn.textContent = isFullscreen ? '退出全屏' : '全屏预览';
      render();

      if (!isFullscreen) {
        translateX = 0;
        translateY = 0;
        scale = 1;
        applyTransform();
      }
    });

    // Ctrl + 滚轮缩放
    preview.addEventListener('wheel', function(e) {
      if (e.ctrlKey) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        scale = Math.max(0.2, Math.min(scale + delta, 3));
        applyTransform();
      }
    }, { passive: false });

    // 初始渲染
    render();
  </script>
</body>
</html>'''
            
            # 转换代码占位符
            html_content = html_template.replace("CODE_PLACEHOLDER", mermaid_code_content)
            
            # 保存到临时文件
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, 'equity_mermaid_preview.html')
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 在浏览器中打开
            webbrowser.open_new_tab(temp_file_path)
            
            # 显示操作提示
            st.info("🔍 已在新标签页打开全屏编辑器，可进行代码编辑和图表预览")
    
    with col_op2:
        # 下载Mermaid代码按钮
        if st.button("📥 下载Mermaid代码", use_container_width=True):
            st.download_button(
                label="保存Mermaid代码",
                data=st.session_state.mermaid_code,
                file_name="股权结构.mmd",
                mime="text/plain",
                use_container_width=True,
                key="download_mermaid"
            )
    
    with col_op3:
        # 这里曾经有复制代码到剪贴板按钮，已移除
        pass

    # 显示详细数据
    st.markdown("""<div style='background: linear-gradient(135deg, #0f4c81 0%, #17a2b8 100%); padding: 0.75rem 1rem; border-radius: 8px; color: white; margin-top: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);'>
    <span style='font-size: 1.5rem; font-weight: bold;'>📋 详细股权数据</span>
    </div>""", unsafe_allow_html=True)
    
    if st.session_state.extracted_data:
        # 首先定义main_company变量，确保在使用前已定义
        main_company = st.session_state.extracted_data.get("main_company", "") or st.session_state.extracted_data.get("core_company", "")
        
        # 第一层：显示实控人信息
        st.markdown("#### 👤 实际控制人")
        
        # 创建一个集合来存储已显示的实控人名称，避免重复显示
        displayed_controllers = set()
        has_controllers = False
        
        # 只处理controller字段作为实际控制人
        if "controller" in st.session_state.extracted_data and st.session_state.extracted_data["controller"]:
            controller = st.session_state.extracted_data["controller"]
            if controller not in displayed_controllers:
                displayed_controllers.add(controller)
                has_controllers = True
                
                # 首先检查实控人在control_relationships中是否有对应的关系描述
                control_description = None
                if "control_relationships" in st.session_state.extracted_data:
                    for rel in st.session_state.extracted_data["control_relationships"]:
                        # 查找实控人作为parent且指向主公司的关系
                        if rel.get("parent") == controller and rel.get("child") == main_company:
                            # 使用description字段，如果没有则使用relationship_type
                            control_description = rel.get("description", rel.get("relationship_type", ""))
                            break
                        # 或者查找实控人作为顶层控制人的任何关系
                        elif rel.get("parent") == controller and rel.get("relationship_type") in ["ultimate_control", "ultimate controller"]:
                            control_description = rel.get("description", rel.get("relationship_type", ""))
                            break
                
                # 如果有控制关系描述，显示描述而不是持股比例
                if control_description:
                    st.markdown(f"- **{controller}**: {control_description}")
                else:
                    # 如果没有控制关系描述，尝试查找controller的持股比例
                    ctrl_percentage = None
                    if "shareholders" in st.session_state.extracted_data:
                        for sh in st.session_state.extracted_data["shareholders"]:
                            if sh["name"] == controller:
                                ctrl_percentage = sh.get("percentage", 0)
                                # 如果持股比例是0.1且没有其他信息，不显示比例
                                if ctrl_percentage == 0.1 and not sh.get("description", ""):
                                    ctrl_percentage = None
                                break
                    
                    if ctrl_percentage is not None:
                        st.markdown(f"- **{controller}**: {ctrl_percentage}%")
                    else:
                        st.markdown(f"- **{controller}**")
        
        # 不再处理top_level_entities作为实控人显示，只在主要股东中显示
        
        # 如果没有实控人信息，显示提示
        if not has_controllers:
            st.markdown("- 未检测到实际控制人信息")
        
        # 第二层和第三层：主要股东和子公司
        col_data1, col_data2 = st.columns(2)
        
        with col_data1:
            st.markdown("#### 📈 主要股东")
            
            # 获取所有潜在的股东信息
            all_parents = {}
            # main_company已在前面定义，这里不再重复定义
            
            # 1. 从entity_relationships中提取所有parent实体和关系
            if "entity_relationships" in st.session_state.extracted_data:
                for relationship in st.session_state.extracted_data["entity_relationships"]:
                    parent = relationship.get("parent", "")
                    child = relationship.get("child", "")
                    percentage = relationship.get("percentage", 0)
                    
                    # 只添加有效的parent-child关系
                    if parent and child:
                        # 存储parent实体信息
                        if parent not in all_parents:
                            all_parents[parent] = []
                        all_parents[parent].append({
                            "child": child,
                            "percentage": percentage
                        })
            
            # 2. 从shareholders中提取直接持股信息，但只在entity_relationships中没有相同关系时添加
            if "shareholders" in st.session_state.extracted_data and main_company:
                for shareholder in st.session_state.extracted_data["shareholders"]:
                    name = shareholder.get("name", "")
                    percentage = shareholder.get("percentage", 0)
                    
                    if name:
                        # 检查entity_relationships中是否已经存在此股东与main_company的关系
                        relationship_exists = False
                        if "entity_relationships" in st.session_state.extracted_data:
                            for rel in st.session_state.extracted_data["entity_relationships"]:
                                if rel.get("parent") == name and rel.get("child") == main_company:
                                    relationship_exists = True
                                    break
                        
                        # 只有当关系不存在时才添加
                        if not relationship_exists:
                            if name not in all_parents:
                                all_parents[name] = []
                            # 检查是否已存在相同的main_company关系
                            exists_in_all_parents = any(item["child"] == main_company for item in all_parents[name])
                            if not exists_in_all_parents:
                                all_parents[name].append({
                                    "child": main_company,
                                    "percentage": percentage
                                })
            
            # 3. 过滤掉已经在实控人中显示的股东
            filtered_parents = {}
            for parent, relationships in all_parents.items():
                if parent not in displayed_controllers and parent != main_company:  # 过滤掉实控人和主公司本身
                    filtered_parents[parent] = relationships  # 保留所有关系，包括与主公司的关系
            
            # 4. 显示结果
            if filtered_parents:
                for parent, relationships in filtered_parents.items():
                    # 构建持股关系描述
                    relationships_text = []
                    for rel in relationships:
                        relationships_text.append(f"持有{rel['child']} {rel['percentage']}%")
                    
                    # 显示股东名称及其所有持股关系
                    st.markdown(f"- **{parent}**: {', '.join(relationships_text)}")
            else:
                st.markdown("- 未检测到主要股东信息")
        
        with col_data2:
            st.markdown("#### 🏢 子公司")
            if "subsidiaries" in st.session_state.extracted_data and st.session_state.extracted_data["subsidiaries"]:
                for subsidiary in st.session_state.extracted_data["subsidiaries"]:
                    st.markdown(f"- **{subsidiary['name']}**: {subsidiary['percentage']}%")
            else:
                st.markdown("- 未检测到子公司信息")
    
    # 显示JSON数据（可折叠）
    with st.expander("📄 查看JSON数据", expanded=False):
        st.code(st.session_state.json_data, language="json")
    
    st.markdown("</div>", unsafe_allow_html=True)

# 页脚
st.markdown("""
---
""")

# 主程序入口
if __name__ == "__main__":
    pass

