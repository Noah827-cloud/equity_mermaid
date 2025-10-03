#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 主入口

重新设计的简洁商务风格主页，使用Streamlit侧边栏导航，优化用户体验。
"""

import os
import streamlit as st

# 设置页面配置 - 使用商务风格的页面设置
st.set_page_config(
    page_title="股权结构图生成工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义商务风格CSS
st.markdown("""
<style>
    /* 整体容器样式 */
    .main-content {
        padding: 2rem;
        background-color: #f5f7fa;
        min-height: 100vh;
    }
    
    /* 标题样式 */
    .title-section {
        background: white;
        padding: 2rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        margin-bottom: 2rem;
    }
    
    .title-section h1 {
        color: #2c3e50;
        font-size: 2.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .title-section p {
        color: #7f8c8d;
        font-size: 1.1rem;
    }
    
    /* 内容卡片样式 */
    .content-card {
        background: white;
        padding: 2rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
    }
    
    .content-card h2 {
        color: #34495e;
        font-size: 1.5rem;
        margin-bottom: 1rem;
        font-weight: 500;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    
    /* 步骤卡片样式 */
    .step-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 6px;
        border-left: 4px solid #3498db;
        margin-bottom: 1rem;
    }
    
    .step-card h3 {
        color: #2c3e50;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    
    /* 按钮样式 */
    .stButton>button {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        font-weight: 500;
        border-radius: 4px;
        transition: background-color 0.3s, transform 0.1s;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .stButton>button:hover {
        background-color: #2980b9;
        transform: translateY(-1px);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #2c3e50;
        color: white;
    }
    
    [data-testid="stSidebar"] .sidebar-header {
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    [data-testid="stSidebar"] .sidebar-header h2 {
        color: white;
        font-size: 1.5rem;
        margin: 0;
    }
    
    [data-testid="stSidebar"] .sidebar-section {
        margin-bottom: 1.5rem;
        padding: 0 1rem;
    }
    
    [data-testid="stSidebar"] h3 {
        color: #ecf0f1;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    [data-testid="stSidebar"] .sidebar-button {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 0.75rem 1rem;
        width: 100%;
        text-align: left;
        font-size: 1rem;
        border-radius: 4px;
        margin-bottom: 0.5rem;
        transition: background-color 0.3s;
    }
    
    [data-testid="stSidebar"] .sidebar-button:hover {
        background-color: #2980b9;
    }
    
    /* 代码块样式 */
    .code-block {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 4px;
        border-left: 3px solid #6c757d;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        margin: 1rem 0;
    }
    
    /* 页脚样式 */
    .footer {
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #dee2e6;
        color: #6c757d;
        font-size: 0.9rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# 创建侧边栏导航
with st.sidebar:
    st.markdown("<div class='sidebar-header'><h2>📊 股权结构图生成工具</h2></div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-section'><h3>功能模块</h3></div>", unsafe_allow_html=True)
    
    # 侧边栏按钮样式通过CSS设置，这里只提供文本和链接
    st.write("## 快速导航")
    
    # 选择当前页面
    selected_page = st.selectbox(
        "请选择功能模块:",
        ["首页介绍", "图像识别模式", "手动编辑模式", "使用指南"],
        index=0,
        format_func=lambda x: x
    )
    
    st.markdown("---")
    st.write("## 快速启动")
    
    # 图像识别模式启动按钮
    if st.button("启动图像识别模式"):
        st.session_state["page"] = "image"
        st.success("正在启动图像识别模式...")
        st.info("请在浏览器中访问: http://localhost:8501")
        st.info("提示: 此按钮仅显示信息，请在新终端中运行上述命令启动服务")
    
    # 手动编辑模式启动按钮
    if st.button("启动手动编辑模式"):
        st.session_state["page"] = "manual"
        st.success("正在启动手动编辑模式...")
        st.info("请在浏览器中访问: http://localhost:8503")
        st.info("提示: 此按钮仅显示信息，请在新终端中运行上述命令启动服务")
    
    st.markdown("---")
    st.write("© 2023 股权结构图生成工具")
    st.write("版本: V2.1")

# 主内容区域
st.markdown("<div class='main-content'>", unsafe_allow_html=True)

# 根据选择显示不同内容
if selected_page == "首页介绍" or "page" not in st.session_state:
    with st.container():
        st.markdown("<div class='title-section'>", unsafe_allow_html=True)
        st.title("股权结构图生成工具")
        st.write("专业的股权结构可视化解决方案，支持图像识别和手动编辑两种工作模式")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 主要功能介绍
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.header("主要功能")
        st.write("本工具提供两种核心功能模式，满足不同场景下的股权结构图生成需求：")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📷 图像识别模式")
            st.write("上传现有股权结构图，系统自动识别公司、股东和持股比例，快速生成数字化图表。")
            if st.button("了解更多 - 图像识别"):
                selected_page = "图像识别模式"
        
        with col2:
            st.subheader("📝 手动编辑模式")
            st.write("从零开始创建或精确编辑股权结构，灵活定义公司关系、持股比例和控制关系。")
            if st.button("了解更多 - 手动编辑"):
                selected_page = "手动编辑模式"
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 产品特点
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.header("产品特点")
        
        features = [
            {"title": "交互式图表", "desc": "生成的Mermaid图表支持交互操作，可缩放、平移和全屏查看"},
            {"title": "数据一致性", "desc": "两种模式生成的JSON数据格式完全一致，支持互相转换使用"},
            {"title": "图表导出", "desc": "支持将生成的股权结构图导出为多种格式，便于报告和演示使用"},
            {"title": "批量处理", "desc": "支持批量上传和处理多个股权结构图，提高工作效率"},
        ]
        
        for i in range(0, len(features), 2):
            cols = st.columns(2)
            for j in range(min(2, len(features) - i)):
                with cols[j]:
                    st.markdown(f"<div class='step-card'><h3>{features[i+j]['title']}</h3><p>{features[i+j]['desc']}</p></div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "图像识别模式":
    st.markdown("<div class='title-section'>", unsafe_allow_html=True)
    st.title("图像识别模式")
    st.write("自动识别现有股权结构图，快速生成数字化图表")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.header("工作流程")
    
    steps = [
        {"title": "1. 上传图像", "desc": "上传清晰的股权结构图，支持PNG、JPG、JPEG等常见格式"},
        {"title": "2. 自动识别", "desc": "系统自动识别图中的公司名称、股东关系和持股比例"},
        {"title": "3. 数据处理", "desc": "将识别结果转换为结构化JSON数据，便于后续编辑和分析"},
        {"title": "4. 图表生成", "desc": "基于识别数据自动生成交互式Mermaid股权结构图"},
        {"title": "5. 编辑优化", "desc": "可在生成的基础上进行手动编辑和优化，修正识别误差"},
        {"title": "6. 导出保存", "desc": "将最终的图表和数据导出保存，用于报告和演示"},
    ]
    
    for step in steps:
        st.markdown(f"<div class='step-card'><h3>{step['title']}</h3><p>{step['desc']}</p></div>", unsafe_allow_html=True)
    
    st.header("启动方式")
    st.write("点击左侧导航栏中的 '启动图像识别模式' 按钮，或使用以下命令在终端中启动：")
    st.code(".venv\\Scripts\\streamlit.exe run src\\main\\enhanced_equity_to_mermaid.py", language="powershell")
    st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "手动编辑模式":
    st.markdown("<div class='title-section'>", unsafe_allow_html=True)
    st.title("手动编辑模式")
    st.write("从零开始创建或精确编辑股权结构，满足复杂场景需求")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.header("工作流程")
    
    steps = [
        {"title": "1. 设置核心公司", "desc": "输入核心公司名称，作为股权结构图的中心节点"},
        {"title": "2. 添加顶级实体", "desc": "添加直接持有核心公司股权的顶级实体/股东"},
        {"title": "3. 定义子公司", "desc": "添加核心公司控制的子公司及其持股比例"},
        {"title": "4. 设置股权关系", "desc": "定义实体之间的股权持有关系和具体比例"},
        {"title": "5. 确定控制关系", "desc": "明确标注公司间的控制关系和控制路径"},
        {"title": "6. 生成与导出", "desc": "生成完整的股权结构图并导出为所需格式"},
    ]
    
    for step in steps:
        st.markdown(f"<div class='step-card'><h3>{step['title']}</h3><p>{step['desc']}</p></div>", unsafe_allow_html=True)
    
    st.header("启动方式")
    st.write("点击左侧导航栏中的 '启动手动编辑模式' 按钮，或使用以下命令在终端中启动：")
    st.code(".venv\\Scripts\\streamlit.exe run src\\main\\manual_equity_editor.py", language="powershell")
    st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "使用指南":
    st.markdown("<div class='title-section'>", unsafe_allow_html=True)
    st.title("使用指南")
    st.write("详细了解如何有效使用股权结构图生成工具")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.header("系统要求")
    st.write("使用本工具前，请确保您的系统满足以下要求：")
    
    requirements = [
        "Python 3.7 或更高版本",
        "Streamlit 1.10 或更高版本",
        "推荐使用Chrome、Firefox或Edge最新版本浏览器",
        "对于图像识别模式，建议上传分辨率不低于1024x768的清晰图像"
    ]
    
    for req in requirements:
        st.markdown(f"• {req}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.header("常见问题")
    
    with st.expander("如何提高图像识别准确率？"):
        st.write("1. 确保上传的图像清晰，无模糊或扭曲")
        st.write("2. 尽量使用光线均匀、对比度适中的图像")
        st.write("3. 对于复杂图表，可考虑分段拍摄后合并处理")
        st.write("4. 识别后仔细检查并修正任何识别误差")
    
    with st.expander("如何处理大型复杂的股权结构？"):
        st.write("1. 可以先创建主要结构，再逐步添加细节")
        st.write("2. 利用分组功能将相关实体归类，提高图表可读性")
        st.write("3. 对于超大型结构，可考虑分层次展示")
    
    with st.expander("生成的图表可以导出哪些格式？"):
        st.write("1. Mermaid代码 - 可嵌入各种支持Mermaid的文档系统")
        st.write("2. JSON数据 - 便于程序处理和二次开发")
        st.write("3. 通过浏览器打印功能可导出为PDF或图像格式")
    st.markdown("</div>", unsafe_allow_html=True)

# 页脚
st.markdown("<div class='footer'>© 2023 股权结构图生成工具 - 版本 V2.1</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)  # 关闭main-content容器