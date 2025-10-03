#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 全新主页设计

现代化商务风格界面，提供直观的功能导航和用户体验。
"""

import streamlit as st
from datetime import datetime

# 使用session_state控制侧边栏状态
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'collapsed'

# 页面配置
st.set_page_config(
    page_title="股权结构图生成工具 - 智能分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state  # 使用session_state控制侧边栏状态
)

# 简化的自定义样式
st.markdown("""
<style>
    /* 主题变量 */
    :root {
        --primary-color: #0f4c81;
        --secondary-color: #17a2b8;
        --accent-color: #f8f9fa;
        --text-color: #2c3e50;
        --light-text: #6c757d;
        --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    
    /* 页面背景 */
    body {
        background-color: var(--accent-color);
    }
    
    /* 容器样式 */
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
    
    /* 导航栏 */
    .navbar {
        background: white;
        padding: 1rem 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: var(--card-shadow);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .navbar .logo {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--primary-color);
    }
    
    /* 英雄区域 */
    .hero {
        background: linear-gradient(135deg, var(--primary-color) 0%, #1e3a8a 100%);
        color: white;
        border-radius: 15px;
        padding: 4rem 2rem;
        margin-bottom: 2.5rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    .hero h1 {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    
    .hero p {
        font-size: 1.2rem;
        margin-bottom: 2rem;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* 功能卡片 */
    .feature-card {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        box-shadow: var(--card-shadow);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 1.5rem;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.12);
    }
    
    .feature-card .icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        color: var(--primary-color);
    }
    
    .feature-card h3 {
        color: var(--text-color);
        margin-bottom: 1rem;
        font-size: 1.3rem;
    }
    
    .feature-card p {
        color: var(--light-text);
        margin-bottom: 1.5rem;
    }
    
    /* 优势区块 */
    .advantages {
        background: white;
        border-radius: 15px;
        padding: 2.5rem;
        margin-bottom: 2.5rem;
        box-shadow: var(--card-shadow);
    }
    
    .advantage-section {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        justify-content: center;
    }
    
    .advantage-item {
        background: var(--accent-color);
        border-radius: 10px;
        padding: 1.5rem;
        width: calc(25% - 20px);
        min-width: 250px;
        text-align: center;
        transition: transform 0.3s ease;
    }
    
    .advantage-item:hover {
        transform: translateY(-5px);
    }
    
    .advantage-icon {
        font-size: 2.5rem;
        color: var(--primary-color);
        margin-bottom: 1rem;
    }
    
    .advantage-item h4 {
        color: var(--text-color);
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    
    .advantage-item p {
        color: var(--light-text);
        margin: 0;
        font-size: 0.95rem;
    }
    
    /* 页脚 */
    .footer {
        background: var(--primary-color);
        color: white;
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
    }
    
    /* 隐藏Streamlit默认元素，但保留侧边栏相关的功能 */
    .css-17eq0hr, .css-z09l0h {
        display: none;
    }
    
    /* 移除可能干扰侧边栏的样式 */
    /* 侧边栏样式增强 */
    [data-testid="stSidebar"] {
        background-color: white;
        padding: 1rem;
    }
    
    /* 侧边栏按钮样式 */
    [data-testid="stSidebar"] button {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        text-align: left;
        transition: all 0.3s ease;
    }
    
    [data-testid="stSidebar"] button:hover {
        background-color: var(--accent-color);
        border-color: var(--primary-color);
    }
    
    /* 响应式设计 */
    @media (max-width: 768px) {
        .advantage-item {
            width: 100%;
        }
    }
</style>
""", unsafe_allow_html=True)

# 主要内容容器
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 顶部平台名称
st.markdown("""
<div style="background: rgba(255, 255, 255, 0.8); padding: 0.5rem 1.5rem; border-radius: 8px; box-shadow: rgba(0, 0, 0, 0.1) 0px 4px 15px; margin-bottom: 2rem; width: 100%;">
    <div style="display: flex; align-items: center; line-height: 1;">
        <span style="font-size: 1.5rem; margin-right: 0.5rem;">📊</span>
        <h1 style="color: #0f4c81; font-size: 1.3rem; font-weight: 700; margin: 0; line-height: 1.2;">股权结构智能分析平台</h1>
    </div>
</div>
""", unsafe_allow_html=True)

# 英雄区域
st.markdown("""
<div class="hero">
    <h1>智能股权结构分析与可视化</h1>
    <p>一站式解决方案，让复杂的股权关系变得清晰可见，助力投资决策与公司治理</p>
</div>
""", unsafe_allow_html=True)

# 功能区块 - 使用Streamlit原生布局代替复杂HTML
st.markdown("<h2 style='text-align: center; color: var(--primary-color); margin-bottom: 2rem;'>核心功能</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: var(--light-text); margin-bottom: 2.5rem; max-width: 600px; margin-left: auto; margin-right: auto;'>我们提供两种主要工作模式，满足不同场景下的股权结构分析需求</p>", unsafe_allow_html=True)

# 使用Streamlit的columns来创建功能卡片
col1, col2, col3 = st.columns(3)

with col1:
    # 为图像识别模式卡片添加超链接
    st.markdown("""
    <a href="/图像识别模式" 
       style="display: block; text-decoration: none; color: inherit; transition: transform 0.3s ease;">
    <div class="feature-card">
        <div class="icon">📷</div>
        <h3>图像识别模式</h3>
        <p>上传现有股权结构图，AI自动识别公司、股东及持股关系，快速生成结构化数据</p>
    </div>
    </a>
    """, unsafe_allow_html=True)

with col2:
    # 为手动编辑模式卡片添加超链接
    st.markdown("""
    <a href="/手动编辑模式" 
       style="display: block; text-decoration: none; color: inherit; transition: transform 0.3s ease;">
    <div class="feature-card">
        <div class="icon">📝</div>
        <h3>手动编辑模式</h3>
        <p>灵活创建和编辑复杂股权关系，精确设置持股比例、控制关系，构建完整股权网络</p>
    </div>
    </a>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="icon">📊</div>
        <h3>可视化图表</h3>
        <p>一键生成交互式股权结构图，支持缩放、拖拽、全屏查看，直观展示复杂关系</p>
    </div>
    """, unsafe_allow_html=True)

# 优势区块 - 使用更简单的HTML结构
st.markdown("<h2 style='text-align: center; color: var(--primary-color); margin-bottom: 1rem;'>平台优势</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: var(--light-text); margin-bottom: 2rem; max-width: 800px; margin-left: auto; margin-right: auto;'>我们的工具专为金融专业人士、投资顾问和企业管理层设计</p>", unsafe_allow_html=True)

# 创建优势区块的四个列
adv1, adv2, adv3, adv4 = st.columns(4)

with adv1:
    st.markdown("""
    <div style='background: #f8f9fa; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <div style='font-size: 2.5rem; color: #0f4c81; margin-bottom: 1rem;'>⚡</div>
        <h4 style='color: #2c3e50; margin-bottom: 0.5rem; font-weight: 600;'>高效便捷</h4>
        <p style='color: #6c757d; margin: 0; font-size: 0.95rem;'>从图像识别到图表生成，全流程自动化，大幅提升工作效率</p>
    </div>
    """, unsafe_allow_html=True)

with adv2:
    st.markdown("""
    <div style='background: #f8f9fa; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <div style='font-size: 2.5rem; color: #0f4c81; margin-bottom: 1rem;'>🎯</div>
        <h4 style='color: #2c3e50; margin-bottom: 0.5rem; font-weight: 600;'>精准识别</h4>
        <p style='color: #6c757d; margin: 0; font-size: 0.95rem;'>先进的图像识别算法，确保股权关系数据的准确性</p>
    </div>
    """, unsafe_allow_html=True)

with adv3:
    st.markdown("""
    <div style='background: #f8f9fa; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <div style='font-size: 2.5rem; color: #0f4c81; margin-bottom: 1rem;'>🔄</div>
        <h4 style='color: #2c3e50; margin-bottom: 0.5rem; font-weight: 600;'>灵活编辑</h4>
        <p style='color: #6c757d; margin: 0; font-size: 0.95rem;'>支持多维度调整，满足各种复杂股权结构的编辑需求</p>
    </div>
    """, unsafe_allow_html=True)

with adv4:
    st.markdown("""
    <div style='background: #f8f9fa; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <div style='font-size: 2.5rem; color: #0f4c81; margin-bottom: 1rem;'>📱</div>
        <h4 style='color: #2c3e50; margin-bottom: 0.5rem; font-weight: 600;'>响应式设计</h4>
        <p style='color: #6c757d; margin: 0; font-size: 0.95rem;'>适配各种设备屏幕，随时随地查看和编辑股权结构</p>
    </div>
    """, unsafe_allow_html=True)

# 页脚
current_year = datetime.now().year
st.markdown(f"""
<div class="footer">
    <div style="font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem;">股权结构智能分析平台</div>
    <p>© {current_year} Noah 版权所有 | 专业的股权结构可视化解决方案</p>
</div>
""", unsafe_allow_html=True)

# 关闭主容器
st.markdown('</div>', unsafe_allow_html=True)

# 自定义侧边栏 - 只保留使用提示部分
with st.sidebar:
    # 使用提示部分
    st.subheader("📌 使用提示", anchor=False)
    st.markdown("• 图像识别模式适合快速数字化现有股权图")
    st.markdown("• 手动编辑模式适合从零构建或精细调整")
    st.markdown("• 两种模式生成的数据格式完全兼容")