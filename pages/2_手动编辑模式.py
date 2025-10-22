#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 手动编辑模式

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
    st.info('📊 正在加载手动编辑模式，请耐心等待...')
    st.markdown("""
    <div style="text-align: center; margin: 20px 0;">
        <div style="display: inline-block; width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #0f4c81; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <p style="margin-top: 10px; color: #666;">正在初始化编辑模块...</p>
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
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'main', 'manual_equity_editor.py'))

# 使用exec直接执行文件内容，这样可以确保所有函数都在当前命名空间中定义
def safe_read_file_with_bom_removal(file_path):
    """安全读取文件并移除所有可能的 BOM 字符"""
    try:
        # 方法1: 尝试用 utf-8-sig 读取（自动处理BOM）
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        print(f"[OK] 使用 utf-8-sig 成功读取: {file_path}")
    except UnicodeDecodeError:
        # 方法2: 用二进制方式读取并手动移除BOM
        with open(file_path, 'rb') as f:
            raw_content = f.read()
            if raw_content.startswith(b'\xef\xbb\xbf'):
                raw_content = raw_content[3:]  # 移除BOM
                print(f"[OK] 检测到并移除了 BOM: {file_path}")
            content = raw_content.decode('utf-8')
        print(f"[OK] 使用二进制方式成功读取: {file_path}")
    except Exception as e:
        print(f"[ERROR] 读取文件失败: {file_path}, 错误: {e}")
        raise
    
    # 防御性移除可能残留的 BOM 字符
    if content and content[0] == '\ufeff':
        content = content.lstrip('\ufeff')
        print(f"[OK] 移除了残留的 BOM 字符: {file_path}")
    
    return content

# 读取并执行文件
file_content = safe_read_file_with_bom_removal(file_path)

# 清除加载提示
loading_placeholder.empty()

exec(file_content, globals())