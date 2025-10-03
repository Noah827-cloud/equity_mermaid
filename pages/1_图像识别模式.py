#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 图像识别模式

此页面直接运行src/main目录下的原始实现。
"""

import sys
import os

# 确保可以导入src目录下的模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 直接执行原始文件
# 这样可以确保所有的代码都在正确的上下文中运行
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'main', 'enhanced_equity_to_mermaid.py'))

# 使用exec直接执行文件内容，这样可以确保所有函数都在当前命名空间中定义
with open(file_path, 'r', encoding='utf-8') as f:
    file_content = f.read()

exec(file_content, globals())