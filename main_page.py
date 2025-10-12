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
    st.session_state.sidebar_state = 'expanded'  # 默认展开侧边栏

# 页面配置
st.set_page_config(
    page_title="股权结构图生成工具 - 智能分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state  # 使用session_state控制侧边栏状态
)

# 简化的自定义样式 - 集成FontAwesome图标库
st.markdown("""
<style>
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');
    
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
    
    /* 隐藏 sidebar header 上的 keyboard 提示 */ 
    [data-testid="stSidebar"] .streamlit-expanderHeader button div {
        display: none !important; 
    } 
    /* Sidebar 整体背景色与宽度 */ 
    [data-testid="stSidebar"] {
        background-color: var(--primary-color) !important; /* 使用主色调保持一致 */ 
        color: #ffffff !important;            /* 白色字体 */ 
        padding: 1rem 0.5rem;
        min-width: 250px !important;          /* 最小宽度 */ 
        max-width: 280px !important;          /* 最大宽度 */ 
    } 
    /* Sidebar 标题美化 */ 
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #4fc3f7 !important;   /* 天蓝色标题 */ 
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    } 
    /* Sidebar 菜单项样式 */ 
    [data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        background-color: transparent !important;
        color: white !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0.5rem 1rem !important;
        margin: 0.25rem 0;
        font-weight: 600;
        box-shadow: none !important;
        background-image: none !important;
        transition: all 0.3s ease-in-out;
    } 
    /* 鼠标悬停效果 */ 
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        transform: translateX(4px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    } 
    /* Sidebar 内文字统一 */ 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #e0e0e0 !important;
        font-size: 14px;
    }
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

# 文件顶部添加import语句
import streamlit.components.v1 as components

# 在CSS样式定义之后，主要内容之前添加particles.js组件
# 主要内容容器
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 添加particles.js背景动画 - 使用components.html
components.html("""
<!DOCTYPE html>
<html>
<head>
  <style>
    /* 关键样式：使用fixed定位和适当的z-index */
    body { margin: 0; padding: 0; }
    #particles-js {
      position: fixed;
      width: 100%;
      height: 100%;
      top: 0;
      left: 0;
      z-index: -1;
      background-color: transparent;
    }
  </style>
</head>
<body>
  <div id="particles-js"></div>
  <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
  <script>
    particlesJS("particles-js", {
      "particles": {
        "number": {
          "value": 80,
          "density": {
            "enable": true,
            "value_area": 800
          }
        },
        "color": {
          "value": "#0f4c81"
        },
        "shape": {
          "type": "circle"
        },
        "opacity": {
          "value": 0.5,
          "random": true
        },
        "size": {
          "value": 4,
          "random": true
        },
        "line_linked": {
          "enable": true,
          "distance": 200,
          "color": "#0f4c81",
          "opacity": 0.3,
          "width": 1
        },
        "move": {
          "enable": true,
          "speed": 1,
          "direction": "none",
          "random": false,
          "straight": false,
          "out_mode": "out",
          "bounce": false
        }
      },
      "interactivity": {
        "detect_on": "canvas",
        "events": {
          "onhover": {
            "enable": true,
            "mode": "grab"
          },
          "onclick": {
            "enable": true,
            "mode": "push"
          }
        },
        "modes": {
          "grab": {
            "distance": 200,
            "line_linked": {
              "opacity": 0.5
            }
          },
          "push": {
            "particles_nb": 4
          }
        }
      },
      "retina_detect": true
    });
  </script>
</body>
</html>
""", height=50)

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
        <div class="icon"><i class="fas fa-camera"></i></div>
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
        <div class="icon"><i class="fas fa-edit"></i></div>
        <h3>手动编辑模式</h3>
        <p>灵活创建和编辑复杂股权关系，精确设置持股比例、控制关系，构建完整股权网络</p>
    </div>
    </a>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="icon"><i class="fas fa-chart-pie"></i></div>
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
        <div style='font-size: 2.5rem; color: #0f4c81; margin-bottom: 1rem;'><i class="fas fa-bolt"></i></div>
        <h4 style='color: #2c3e50; margin-bottom: 0.5rem; font-weight: 600;'>高效便捷</h4>
        <p style='color: #6c757d; margin: 0; font-size: 0.95rem;'>从图像识别到图表生成，全流程自动化，大幅提升工作效率</p>
    </div>
    """, unsafe_allow_html=True)

with adv2:
    st.markdown("""
    <div style='background: #f8f9fa; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <div style='font-size: 2.5rem; color: #0f4c81; margin-bottom: 1rem;'><i class="fas fa-bullseye"></i></div>
        <h4 style='color: #2c3e50; margin-bottom: 0.5rem; font-weight: 600;'>精准识别</h4>
        <p style='color: #6c757d; margin: 0; font-size: 0.95rem;'>先进的图像识别算法，确保股权关系数据的准确性</p>
    </div>
    """, unsafe_allow_html=True)

with adv3:
    st.markdown("""
    <div style='background: #f8f9fa; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <div style='font-size: 2.5rem; color: #0f4c81; margin-bottom: 1rem;'><i class="fas fa-sync-alt"></i></div>
        <h4 style='color: #2c3e50; margin-bottom: 0.5rem; font-weight: 600;'>灵活编辑</h4>
        <p style='color: #6c757d; margin: 0; font-size: 0.95rem;'>支持多维度调整，满足各种复杂股权结构的编辑需求</p>
    </div>
    """, unsafe_allow_html=True)

with adv4:
    st.markdown("""
    <div style='background: #f8f9fa; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <div style='font-size: 2.5rem; color: #0f4c81; margin-bottom: 1rem;'><i class="fas fa-mobile-alt"></i></div>
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

# 自定义侧边栏 - 按照test_main_page.py的样式，但使用实际页面导航
with st.sidebar:
    # 侧边栏标题按照test_main_page.py的样式
    st.sidebar.title("股权分析平台") 
    
    st.sidebar.subheader("功能导航") 
    
    # 导航按钮，使用Unicode图标
    if st.sidebar.button("🔍 图像识别模式", help="使用AI识别股权结构图", use_container_width=True):
        # 使用正确的相对路径
        st.switch_page("pages/1_图像识别模式.py")
        
    if st.sidebar.button("📊 手动编辑模式", help="手动创建和编辑股权结构", use_container_width=True):
        # 使用正确的相对路径
        st.switch_page("pages/2_手动编辑模式.py")
    
    # 使用简洁的展开面板替代详细的使用说明
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

    # 添加版权说明
    st.sidebar.markdown(
        '<h6>Made in &nbsp<img src="https://streamlit.io/images/brand/streamlit-mark-color.png" alt="Streamlit logo" height="16">&nbsp by <a href="https://github.com/Noah827-cloud/equity_mermaid" style="color: white;">@Noah</a></h6>',
        unsafe_allow_html=True,
    )