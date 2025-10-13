#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 优化版主页设计

优化内容：
1. 性能优化 - 减少外部依赖
2. 响应式设计 - 移动端适配
3. 代码结构 - 模块化设计
4. 用户体验 - 加载状态和错误处理
"""

import streamlit as st
from datetime import datetime
import os

# 配置类
class ThemeConfig:
    PRIMARY_COLOR = "#0f4c81"
    SECONDARY_COLOR = "#17a2b8"
    ACCENT_COLOR = "#f8f9fa"
    TEXT_COLOR = "#2c3e50"
    LIGHT_TEXT = "#6c757d"
    CARD_SHADOW = "0 4px 20px rgba(0, 0, 0, 0.08)"

# 页面配置
st.set_page_config(
    page_title="股权结构图生成工具 - 智能分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 优化的CSS样式 - 减少外部依赖，添加响应式设计
st.markdown(f"""
<style>
    /* 主题变量 */
    :root {{
        --primary-color: {ThemeConfig.PRIMARY_COLOR};
        --secondary-color: {ThemeConfig.SECONDARY_COLOR};
        --accent-color: {ThemeConfig.ACCENT_COLOR};
        --text-color: {ThemeConfig.TEXT_COLOR};
        --light-text: {ThemeConfig.LIGHT_TEXT};
        --card-shadow: {ThemeConfig.CARD_SHADOW};
    }}
    
    /* 页面背景 */
    body {{
        background-color: var(--accent-color);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}
    
    /* 容器样式 */
    .main-container {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }}
    
    /* 英雄区域 - 响应式优化 */
    .hero {{
        background: linear-gradient(135deg, var(--primary-color) 0%, #1e3a8a 100%);
        color: white;
        border-radius: 15px;
        padding: 3rem 2rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }}
    
    .hero h1 {{
        font-size: 2.5rem;
        margin-bottom: 1rem;
        font-weight: 700;
    }}
    
    .hero p {{
        font-size: 1.2rem;
        margin-bottom: 2rem;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }}
    
    /* 功能卡片 - 优化悬停效果 */
    .feature-card {{
        background: white;
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        box-shadow: var(--card-shadow);
        transition: all 0.3s ease;
        margin-bottom: 1.5rem;
        cursor: pointer;
        border: 2px solid transparent;
    }}
    
    .feature-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        border-color: var(--primary-color);
    }}
    
    .feature-card .icon {{
        font-size: 3rem;
        margin-bottom: 1rem;
        color: var(--primary-color);
    }}
    
    .feature-card h3 {{
        color: var(--text-color);
        margin-bottom: 1rem;
        font-size: 1.3rem;
    }}
    
    .feature-card p {{
        color: var(--light-text);
        margin-bottom: 1.5rem;
        line-height: 1.6;
    }}
    
    /* 优势区块 - 响应式布局 */
    .advantage-item {{
        background: var(--accent-color);
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        transition: transform 0.3s ease;
        margin-bottom: 1rem;
    }}
    
    .advantage-item:hover {{
        transform: translateY(-3px);
    }}
    
    .advantage-icon {{
        font-size: 2.5rem;
        color: var(--primary-color);
        margin-bottom: 1rem;
    }}
    
    /* 页脚 */
    .footer {{
        background: var(--primary-color);
        color: white;
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        margin-top: 3rem;
    }}
    
    /* 侧边栏样式优化 */
    [data-testid="stSidebar"] {{
        background-color: var(--primary-color) !important;
        color: #ffffff !important;
        padding: 1rem 0.5rem;
        min-width: 250px !important;
        max-width: 280px !important;
    }}
    
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{
        color: #4fc3f7 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    [data-testid="stSidebar"] .stButton button {{
        background: transparent !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
        margin: 0.25rem 0;
        font-weight: 600;
        transition: all 0.3s ease;
    }}
    
    [data-testid="stSidebar"] .stButton button:hover {{
        background: rgba(255, 255, 255, 0.1) !important;
        transform: translateX(4px);
    }}
    
    /* 移动端响应式设计 */
    @media (max-width: 768px) {{
        .hero {{
            padding: 2rem 1rem;
        }}
        
        .hero h1 {{
            font-size: 1.8rem;
        }}
        
        .hero p {{
            font-size: 1rem;
        }}
        
        .feature-card {{
            padding: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .advantage-item {{
            padding: 1rem;
        }}
        
        .main-container {{
            padding: 10px;
        }}
    }}
    
    /* 加载状态样式 */
    .loading-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }}
    
    /* 隐藏默认导航 */
    [data-testid="stSidebarNav"],
    [data-testid="stSidebar"] [href*="main_page"],
    [data-testid="stSidebar"] [href*="1_图像识别模式"],
    [data-testid="stSidebar"] [href*="2_手动编辑模式"] {{
        display: none !important;
    }}
</style>
""", unsafe_allow_html=True)

# 主要内容容器
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 英雄区域
st.markdown("""
<div class="hero">
    <h1>智能股权结构分析与可视化</h1>
    <p>一站式解决方案，让复杂的股权关系变得清晰可见，助力投资决策与公司治理</p>
</div>
""", unsafe_allow_html=True)

# 功能区块
st.markdown("<h2 style='text-align: center; color: var(--primary-color); margin-bottom: 2rem;'>核心功能</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: var(--light-text); margin-bottom: 2.5rem; max-width: 600px; margin-left: auto; margin-right: auto;'>我们提供两种主要工作模式，满足不同场景下的股权结构分析需求</p>", unsafe_allow_html=True)

# 使用Streamlit的columns来创建功能卡片
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="icon">🔍</div>
        <h3>图像识别模式</h3>
        <p>上传现有股权结构图，AI自动识别公司、股东及持股关系，快速生成结构化数据</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="icon">📊</div>
        <h3>手动编辑模式</h3>
        <p>灵活创建和编辑复杂股权关系，精确设置持股比例、控制关系，构建完整股权网络</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="icon">📈</div>
        <h3>可视化图表</h3>
        <p>一键生成交互式股权结构图，支持缩放、拖拽、全屏查看，直观展示复杂关系</p>
    </div>
    """, unsafe_allow_html=True)

# 优势区块
st.markdown("<h2 style='text-align: center; color: var(--primary-color); margin-bottom: 1rem;'>平台优势</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: var(--light-text); margin-bottom: 2rem; max-width: 800px; margin-left: auto; margin-right: auto;'>我们的工具专为金融专业人士、投资顾问和企业管理层设计</p>", unsafe_allow_html=True)

# 创建优势区块的四个列
adv1, adv2, adv3, adv4 = st.columns(4)

with adv1:
    st.markdown("""
    <div class="advantage-item">
        <div class="advantage-icon">⚡</div>
        <h4 style='color: var(--text-color); margin-bottom: 0.5rem; font-weight: 600;'>高效便捷</h4>
        <p style='color: var(--light-text); margin: 0; font-size: 0.95rem;'>从图像识别到图表生成，全流程自动化，大幅提升工作效率</p>
    </div>
    """, unsafe_allow_html=True)

with adv2:
    st.markdown("""
    <div class="advantage-item">
        <div class="advantage-icon">🎯</div>
        <h4 style='color: var(--text-color); margin-bottom: 0.5rem; font-weight: 600;'>精准识别</h4>
        <p style='color: var(--light-text); margin: 0; font-size: 0.95rem;'>先进的图像识别算法，确保股权关系数据的准确性</p>
    </div>
    """, unsafe_allow_html=True)

with adv3:
    st.markdown("""
    <div class="advantage-item">
        <div class="advantage-icon">🔄</div>
        <h4 style='color: var(--text-color); margin-bottom: 0.5rem; font-weight: 600;'>灵活编辑</h4>
        <p style='color: var(--light-text); margin: 0; font-size: 0.95rem;'>支持多维度调整，满足各种复杂股权结构的编辑需求</p>
    </div>
    """, unsafe_allow_html=True)

with adv4:
    st.markdown("""
    <div class="advantage-item">
        <div class="advantage-icon">📱</div>
        <h4 style='color: var(--text-color); margin-bottom: 0.5rem; font-weight: 600;'>响应式设计</h4>
        <p style='color: var(--light-text); margin: 0; font-size: 0.95rem;'>适配各种设备屏幕，随时随地查看和编辑股权结构</p>
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

# 优化的侧边栏
with st.sidebar:
    st.sidebar.title("股权分析平台") 
    st.sidebar.subheader("功能导航") 
    
    # 导航按钮 - 添加错误处理
    if st.sidebar.button("🔍 图像识别模式", help="使用AI识别股权结构图", use_container_width=True):
        try:
            st.switch_page("pages/1_图像识别模式.py")
        except Exception as e:
            st.error(f"页面跳转失败: {str(e)}")
        
    if st.sidebar.button("📊 手动编辑模式", help="手动创建和编辑股权结构", use_container_width=True):
        try:
            st.switch_page("pages/2_手动编辑模式.py")
        except Exception as e:
            st.error(f"页面跳转失败: {str(e)}")
    
    # 使用说明
    with st.expander("ℹ️ 使用说明", expanded=False):
        st.write("## 图像识别模式")
        st.write("1. 上传股权结构相关图片")
        st.write("2. 系统自动识别图片中的股权信息")
        st.write("3. 查看并确认识别结果")
        st.write("4. 生成股权结构图")
        st.write("\n## 手动编辑模式")
        st.write("1. 输入或粘贴股权结构数据")
        st.write("2. 手动调整和编辑股权关系")
        st.write("3. 预览股权结构图")
        st.write("4. 保存并导出结果")
    
    st.sidebar.markdown("---")
    
    # 系统状态信息
    with st.expander("📊 系统状态", expanded=False):
        st.metric("Python版本", "3.13.7")
        st.metric("Streamlit版本", "1.50.0")
        st.metric("运行状态", "正常")
    
    # 版权说明
    st.sidebar.markdown(
        '<h6>Made in &nbsp<img src="https://streamlit.io/images/brand/streamlit-mark-color.png" alt="Streamlit logo" height="16">&nbsp by <a href="https://github.com/Noah827-cloud/equity_mermaid" style="color: white;">@Noah</a></h6>',
        unsafe_allow_html=True,
    )
