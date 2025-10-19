#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制移除 BOM 字符的脚本
"""

import os
import sys
import glob

def remove_bom_from_file(file_path):
    """从单个文件中移除 BOM"""
    try:
        # 读取文件内容
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 检查是否有 BOM
        if content.startswith(b'\xef\xbb\xbf'):
            # 移除 BOM
            content = content[3:]
            
            # 写回文件
            with open(file_path, 'wb') as f:
                f.write(content)
            
            print(f"✓ 已移除 BOM: {file_path}")
            return True
        else:
            print(f"✓ 无 BOM: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ 处理失败 {file_path}: {e}")
        return False

def remove_bom_from_all_python_files():
    """从所有 Python 文件中移除 BOM"""
    print("=== 强制移除所有 Python 文件的 BOM ===")
    
    # 查找所有 Python 文件
    python_files = []
    for root, dirs, files in os.walk('.'):
        # 跳过一些目录
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"找到 {len(python_files)} 个 Python 文件")
    
    removed_count = 0
    for file_path in python_files:
        if remove_bom_from_file(file_path):
            removed_count += 1
    
    print(f"\n=== 完成 ===")
    print(f"处理了 {len(python_files)} 个文件")
    print(f"移除了 {removed_count} 个 BOM")
    
    return removed_count > 0

if __name__ == "__main__":
    remove_bom_from_all_python_files()
