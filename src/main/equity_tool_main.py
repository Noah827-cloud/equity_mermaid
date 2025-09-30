#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 主入口

此脚本提供一个简单的主页面，允许用户在图像识别和手动编辑两种功能之间进行切换。
"""

import os
import streamlit as st

# 设置页面配置
st.set_page_config(
    page_title="股权结构图生成工具",
    page_icon="📊",
    layout="wide"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-container {
        padding: 2rem;
        max-width: 1000px;
        margin: 0 auto;
    }
    .welcome-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    .welcome-box h1 {
        margin-bottom: 1rem;
        font-size: 2.5rem;
    }
    .feature-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 2rem;
        margin: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s, box-shadow 0.3s;
        border: 2px solid transparent;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
        border-color: #667eea;
    }
    .feature-card h3 {
        color: #333;
        margin-bottom: 1rem;
    }
    .feature-card p {
        color: #666;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        background-color: #667eea;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        border-radius: 5px;
        transition: background-color 0.3s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #5a67d8;
    }
    .divider {
        margin: 2rem 0;
        border: 0;
        height: 1px;
        background: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(102, 126, 234, 0.5), rgba(0, 0, 0, 0));
    }
</style>
""", unsafe_allow_html=True)

# 欢迎界面
with st.container():
    st.markdown('<div class="welcome-box">', unsafe_allow_html=True)
    st.title("📊 股权结构图生成工具")
    st.write("选择以下功能之一来开始使用：")
    st.markdown('</div>', unsafe_allow_html=True)

# 功能选择卡片
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("📷 图像识别模式")
    st.write("上传股权结构图，自动识别公司、股东和子公司关系，生成交互式Mermaid图表。")
    st.write("适用于已有纸质或图片形式的股权结构图需要数字化的场景。")
    if st.button("打开图像识别模式"):
        st.session_state["mode"] = "image"
        # 使用Streamlit的方式启动另一个应用
        st.info("即将打开图像识别模式，请手动复制以下链接在浏览器中打开：")
        st.code("http://localhost:8501", language="plaintext")
        st.warning("或者您也可以直接运行以下命令来启动图像识别模式：")
        st.code(".venv\\Scripts\\streamlit.exe run src\\main\\enhanced_equity_to_mermaid.py", language="powershell")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.subheader("📝 手动编辑模式")
    st.write("手动添加公司名称、股东关系、子公司和持股比例，生成交互式Mermaid图表。")
    st.write("适用于需要从零开始创建股权结构图或对现有结构进行精确编辑的场景。")
    if st.button("打开手动编辑模式"):
        st.session_state["mode"] = "manual"
        # 使用Streamlit的方式启动另一个应用
        st.info("即将打开手动编辑模式，请手动复制以下链接在浏览器中打开：")
        st.code("http://localhost:8503", language="plaintext")
        st.warning("请运行以下命令来启动手动编辑模式：")
        st.code(".venv\\Scripts\\streamlit.exe run src\\main\\manual_equity_editor.py", language="powershell")
    st.markdown('</div>', unsafe_allow_html=True)

# 分隔线
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# 功能说明
with st.expander("ℹ️ 功能说明与使用指南"):
    st.markdown("""
    ### 图像识别模式
    1. 上传清晰的股权结构图（支持PNG、JPG、JPEG格式）
    2. 系统自动识别图中的公司、股东和子公司关系
    3. 自动生成JSON数据和交互式Mermaid图表
    4. 可编辑识别结果并下载生成的图表
    
    ### 手动编辑模式
    1. 设置核心公司名称
    2. 添加顶级实体/股东及其持股比例
    3. 添加子公司及其持股比例
    4. 定义实体间的股权关系和控制关系
    5. 生成交互式Mermaid图表
    6. 可下载JSON数据和Mermaid代码
    
    ### 注意事项
    - 两种模式生成的JSON数据格式完全一致，可以互相转换使用
    - 图表样式保持一致，使用相同的颜色编码（如子公司使用深蓝色边框）
    - 生成的图表支持全屏编辑模式
    """)

# 版权信息
st.markdown("---")
st.markdown("© 2023 股权结构图生成工具 - 版本 V2.1")