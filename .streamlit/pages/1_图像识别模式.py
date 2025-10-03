import os
import re
import tempfile
import webbrowser
import base64
import json
import streamlit as st
import requests
from streamlit_mermaid import st_mermaid
import dashscope
from dashscope import MultiModalConversation
from dotenv import load_dotenv
# 导入翻译模块
from src.utils.alicloud_translator import translate_with_alicloud
# 导入Mermaid生成功能
from src.utils.mermaid_function import generate_mermaid_from_data as generate_mermaid_diagram

# 加载环境变量
load_dotenv()

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
    # 翻译公司名称
    if translate_names:
        # 翻译公司名称
        if "companyName" in data and data["companyName"]:
            translated_name = translate_with_alicloud(data["companyName"], target_language="en")
            data["companyName"] = translated_name
    
    # 翻译股东
    if "shareholders" in data:
        for shareholder in data["shareholders"]:
            if translate_names and "name" in shareholder and shareholder["name"]:
                translated_name = translate_with_alicloud(shareholder["name"], target_language="en")
                shareholder["name"] = translated_name
    
    # 翻译子公司
    if "subsidiaries" in data:
        for subsidiary in data["subsidiaries"]:
            if "companyName" in subsidiary and subsidiary["companyName"]:
                if translate_names:
                    translated_name = translate_with_alicloud(subsidiary["companyName"], target_language="en")
                    subsidiary["companyName"] = translated_name
            # 递归翻译子公司的股东
            if "shareholders" in subsidiary:
                for shareholder in subsidiary["shareholders"]:
                    if translate_names and "name" in shareholder and shareholder["name"]:
                        translated_name = translate_with_alicloud(shareholder["name"], target_language="en")
                        shareholder["name"] = translated_name
            # 递归翻译子公司的子公司
            if "subsidiaries" in subsidiary:
                translate_equity_data(subsidiary, translate_names)
    
    return data

# 设置页面配置
st.set_page_config(
    page_title="股权结构图像识别工具",
    page_icon="📷",
    layout="wide"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-container {
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    .section-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    }
    .stButton>button {
        background-color: #667eea;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        border-radius: 5px;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #5a67d8;
    }
    .image-container {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 300px;
    }
    .divider {
        margin: 2rem 0;
        border: 0;
        height: 1px;
        background: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(102, 126, 234, 0.5), rgba(0, 0, 0, 0));
    }
</style>
""", unsafe_allow_html=True)

# 标题和说明
st.title("📷 股权结构图像识别工具")
st.write("上传一张股权结构图，系统将自动识别并生成交互式Mermaid图表。")

# 图像上传区域
with st.container():
    uploaded_file = st.file_uploader("选择一张股权结构图", type=["png", "jpg", "jpeg"])
    
    # 显示上传的图像
    if uploaded_file is not None:
        st.image(uploaded_file, caption="上传的股权结构图", use_column_width=True)
        
        # 识别按钮
        if st.button("识别股权结构"):
            # 这里是图像识别的逻辑
            # 由于实际的图像识别可能需要复杂的AI模型
            # 这里使用示例数据进行演示
            
            st.info("正在识别图像中的股权结构，请稍候...")
            
            # 示例数据
            example_data = {
                "companyName": "核心公司",
                "shareholders": [
                    {"name": "股东A", "percentage": 45},
                    {"name": "股东B", "percentage": 30},
                    {"name": "股东C", "percentage": 25}
                ],
                "subsidiaries": [
                    {
                        "companyName": "子公司1",
                        "shareholders": [
                            {"name": "核心公司", "percentage": 60},
                            {"name": "外部股东D", "percentage": 40}
                        ],
                        "subsidiaries": []
                    },
                    {
                        "companyName": "子公司2",
                        "shareholders": [
                            {"name": "核心公司", "percentage": 80}
                        ],
                        "subsidiaries": [
                            {
                                "companyName": "孙公司",
                                "shareholders": [
                                    {"name": "子公司2", "percentage": 75}
                                ],
                                "subsidiaries": []
                            }
                        ]
                    }
                ]
            }
            
            # 存储结果到会话状态
            st.session_state["equity_data"] = example_data
            st.session_state["json_text"] = json.dumps(example_data, ensure_ascii=False, indent=2)
            
            st.success("股权结构识别完成！")

# 分隔线
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# 显示识别结果和编辑区域
if "equity_data" in st.session_state:
    st.subheader("📝 识别结果编辑")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 股权结构JSON")
        # 提供JSON编辑功能
        json_text = st.text_area("您可以在此处编辑JSON数据", value=st.session_state["json_text"], height=400)
        
        # 更新按钮
        if st.button("更新数据"):
            try:
                # 尝试解析JSON
                updated_data = json.loads(json_text)
                st.session_state["equity_data"] = updated_data
                st.session_state["json_text"] = json.dumps(updated_data, ensure_ascii=False, indent=2)
                st.success("数据已更新！")
            except json.JSONDecodeError as e:
                st.error(f"JSON格式错误: {str(e)}")
    
    with col2:
        st.markdown("### 生成的Mermaid图表")
        
        # 生成Mermaid代码并显示
        mermaid_code = generate_mermaid_diagram(st.session_state["equity_data"])
        st.code(mermaid_code, language="mermaid")
        
        # 使用streamlit-mermaid渲染图表
        try:
            st_mermaid(mermaid_code)
        except Exception as e:
            st.error(f"图表渲染失败: {str(e)}")
    
    # 下载区域
    st.markdown("### 📥 下载")
    
    # JSON下载
    st.download_button(
        label="下载股权结构JSON",
        data=json.dumps(st.session_state["equity_data"], ensure_ascii=False, indent=2),
        file_name="equity_structure.json",
        mime="application/json"
    )
    
    # Mermaid代码下载
    st.download_button(
        label="下载Mermaid代码",
        data=mermaid_code,
        file_name="equity_structure.mermaid",
        mime="text/plain"
    )

# 底部信息
st.markdown("---")
st.markdown("© 2023 股权结构图生成工具 - 图像识别模式")