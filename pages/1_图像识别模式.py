#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 图像识别模式

此页面直接运行src/main目录下的原始实现。
"""

import sys
import os
import streamlit as st
import time

# 确保可以导入src目录下的模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 显示加载提示
loading_placeholder = st.empty()
with loading_placeholder.container():
    st.info('🔍 正在加载图像识别模式，请耐心等待...')
    st.markdown("""
    <div style="text-align: center; margin: 20px 0;">
        <div style="display: inline-block; width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #0f4c81; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <p style="margin-top: 10px; color: #666;">正在初始化AI识别模块...</p>
    </div>
    <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """, unsafe_allow_html=True)

# 直接执行原始文件
# 这样可以确保所有的代码都在正确的上下文中运行
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'main', 'enhanced_equity_to_mermaid.py'))

# 使用exec直接执行文件内容，这样可以确保所有函数都在当前命名空间中定义
with open(file_path, 'r', encoding='utf-8-sig') as f:
    file_content = f.read()
    # 防御性移除可能残留的 BOM
    if file_content and file_content[0] == '\ufeff':
        file_content = file_content.lstrip('\ufeff')

# 清除加载提示
loading_placeholder.empty()

exec(file_content, globals())