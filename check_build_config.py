#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包配置验证脚本
检查所有必要的文件和依赖是否正确配置
"""

import os
import sys

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"OK {description}: {file_path}")
        return True
    else:
        print(f"ERROR {description}: {file_path} (Missing)")
        return False

def check_directory_exists(dir_path, description):
    """检查目录是否存在"""
    if os.path.exists(dir_path):
        print(f"OK {description}: {dir_path}")
        return True
    else:
        print(f"ERROR {description}: {dir_path} (Missing)")
        return False

def main():
    print("=" * 50)
    print("Equity Structure Tool - Build Config Check")
    print("=" * 50)
    
    all_good = True
    
    # 检查核心文件
    print("\n[1] Check Core Files:")
    core_files = [
        ("equity_mermaid.spec", "PyInstaller Config File"),
        ("run_st.py", "Main Startup File"),
        ("requirements.txt", "Dependencies Config"),
        ("main_page.py", "Main Page File"),
        ("check_dependencies.py", "Dependencies Check Script"),
    ]
    
    for file_path, description in core_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    # 检查工具模块文件
    print("\n[2] Check Utils Module Files:")
    utils_files = [
        ("src/utils/visjs_equity_chart.py", "visjs Chart Generator"),
        ("src/utils/icon_integration.py", "Icon Integration Tool"),
        ("src/utils/uvx_helper.py", "UVX Helper Tool"),
        ("src/utils/state_persistence.py", "State Persistence Tool"),
        ("src/utils/excel_smart_importer.py", "Excel Smart Importer"),
    ]
    
    for file_path, description in utils_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    # 检查SVG图标资源
    print("\n[3] Check SVG Icon Resources:")
    svg_files = [
        "src/assets/icons/ant-design_picture-outlined.svg",
        "src/assets/icons/ant-design_picture-twotone.svg", 
        "src/assets/icons/clarity_picture-solid.svg",
        "src/assets/icons/icon-park_edit-one.svg",
        "src/assets/icons/icon-park_upload-picture.svg",
        "src/assets/icons/ix_start-data-analysis.svg",
        "src/assets/icons/mynaui_edit-one-solid.svg",
        "src/assets/icons/streamline-sharp_edit-pdf-remix.svg",
        "src/assets/icons/streamline-sharp_edit-pdf-solid.svg",
    ]
    
    for svg_file in svg_files:
        if not check_file_exists(svg_file, f"SVG Icon: {os.path.basename(svg_file)}"):
            all_good = False
    
    # 检查目录结构
    print("\n[4] Check Directory Structure:")
    directories = [
        ("src", "Source Code Directory"),
        ("src/utils", "Utils Module Directory"),
        ("src/assets", "Assets Directory"),
        ("src/assets/icons", "Icons Directory"),
        ("pages", "Pages Directory"),
        ("scripts", "Scripts Directory"),
    ]
    
    for dir_path, description in directories:
        if not check_directory_exists(dir_path, description):
            all_good = False
    
    # 检查Python环境
    print("\n[5] Check Python Environment:")
    try:
        import streamlit
        print(f"OK Streamlit: {streamlit.__version__}")
    except ImportError:
        print("ERROR Streamlit: Not Installed")
        all_good = False
    
    try:
        import dashscope
        print(f"OK Dashscope: Installed")
    except ImportError:
        print("ERROR Dashscope: Not Installed")
        all_good = False
    
    try:
        import PyInstaller
        print(f"OK PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR PyInstaller: Not Installed")
        all_good = False
    
    # 总结
    print("\n" + "=" * 50)
    if all_good:
        print("SUCCESS: All Checks Passed! Ready to Build.")
        print("\nBuild Commands:")
        print("   python -m PyInstaller equity_mermaid.spec")
        print("\nOr use batch script:")
        print("   build_exe.bat")
    else:
        print("WARNING: Issues Found, Please Fix Before Building.")
    print("=" * 50)

if __name__ == "__main__":
    main()
