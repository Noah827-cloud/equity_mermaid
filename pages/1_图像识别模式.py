#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 图像识别模式

此页面导入并渲染图像识别模式的主要功能。
"""

import sys
import os

# 确保可以导入src目录下的模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入并执行render_page函数（优化：避免exec，提升启动速度）
from src.main.enhanced_equity_to_mermaid import render_page

# 渲染页面
render_page()