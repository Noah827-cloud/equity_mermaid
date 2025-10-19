#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合检查脚本
结合依赖检查和打包配置检查，提供完整的打包前验证
"""

import os
import sys
import importlib.util

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"✗ {description}: {file_path} (缺失)")
        return False

def check_directory_exists(dir_path, description):
    """检查目录是否存在"""
    if os.path.exists(dir_path):
        print(f"✓ {description}: {dir_path}")
        return True
    else:
        print(f"✗ {description}: {dir_path} (缺失)")
        return False

def check_package(package_name, min_version=None):
    """检查单个包是否安装"""
    try:
        # 特殊处理：某些包的import名称与pip包名不同
        import_mapping = {
            'dotenv': 'dotenv',  # python-dotenv包，但import时用dotenv
            'PIL': 'PIL',  # Pillow包，但import时用PIL
        }
        import_name = import_mapping.get(package_name, package_name)
        
        module = importlib.import_module(import_name)
        
        if min_version and hasattr(module, '__version__'):
            version = module.__version__
            print(f"✓ {package_name}: {version} (需要 >= {min_version})")
        else:
            print(f"✓ {package_name}: 已安装")
        return True
    except ImportError:
        print(f"✗ {package_name}: 未安装 (需要 >= {min_version})")
        return False
    except Exception as e:
        print(f"⚠ {package_name}: 检查时出错 - {e}")
        return False

def main():
    print("=" * 70)
    print("股权结构可视化工具 - 综合检查")
    print("=" * 70)
    print()
    
    all_good = True
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"Python 版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version < (3, 8):
        print("⚠ 警告: 建议使用Python 3.8或更高版本")
    print()
    
    # 第一部分：检查依赖包
    print("【第一部分】检查Python依赖包")
    print("-" * 50)
    
    REQUIRED_PACKAGES = {
        'streamlit': '1.32.0',
        'streamlit_mermaid': '0.2.0',
        'dashscope': '1.10.0',
        'requests': '2.31.0',
        'pandas': '2.0.0',
        'openpyxl': '3.1.0',
        'dotenv': '1.0.0',
        'cryptography': '42.0.0',
        'PIL': '10.0.0',  # Pillow
        'typing_extensions': '4.5.0',
    }
    
    for package, min_version in REQUIRED_PACKAGES.items():
        if not check_package(package, min_version):
            all_good = False
    
    print()
    
    # 第二部分：检查核心文件
    print("【第二部分】检查核心文件")
    print("-" * 50)
    
    core_files = [
        ("equity_mermaid.spec", "PyInstaller配置文件"),
        ("run_st.py", "主启动文件"),
        ("requirements.txt", "依赖配置文件"),
        ("main_page.py", "主页面文件"),
        ("check_dependencies.py", "依赖检查脚本"),
    ]
    
    for file_path, description in core_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    print()
    
    # 第三部分：检查工具模块
    print("【第三部分】检查工具模块文件")
    print("-" * 50)
    
    utils_files = [
        ("src/utils/visjs_equity_chart.py", "visjs图表生成器"),
        ("src/utils/icon_integration.py", "图标集成工具"),
        ("src/utils/uvx_helper.py", "UVX辅助工具"),
        ("src/utils/state_persistence.py", "状态持久化工具"),
        ("src/utils/excel_smart_importer.py", "Excel智能导入工具"),
        ("src/utils/ai_equity_analyzer.py", "AI股权分析器"),
        ("src/utils/alicloud_translator.py", "阿里云翻译工具"),
        ("src/utils/config_encryptor.py", "配置加密工具"),
        ("src/utils/equity_llm_analyzer.py", "股权LLM分析器"),
        ("src/utils/mermaid_function.py", "Mermaid函数工具"),
    ]
    
    for file_path, description in utils_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    print()
    
    # 第四部分：检查目录结构
    print("【第四部分】检查目录结构")
    print("-" * 50)
    
    directories = [
        ("src", "源代码目录"),
        ("src/utils", "工具模块目录"),
        ("src/assets", "资源目录"),
        ("src/assets/icons", "图标目录"),
        ("pages", "页面目录"),
        ("scripts", "脚本目录"),
    ]
    
    for dir_path, description in directories:
        if not check_directory_exists(dir_path, description):
            all_good = False
    
    print()
    
    # 第五部分：检查SVG图标资源
    print("【第五部分】检查SVG图标资源")
    print("-" * 50)
    
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
    
    svg_count = 0
    for svg_file in svg_files:
        if check_file_exists(svg_file, f"SVG图标: {os.path.basename(svg_file)}"):
            svg_count += 1
        else:
            all_good = False
    
    print(f"SVG图标统计: {svg_count}/{len(svg_files)} 个文件存在")
    print()
    
    # 总结
    print("=" * 70)
    if all_good:
        print("🎉 所有检查通过！可以进行打包。")
        print()
        print("📦 打包命令:")
        print("   python -m PyInstaller equity_mermaid.spec --noconfirm")
        print()
        print("📋 打包后建议测试:")
        print("   - 主界面启动")
        print("   - 图像识别模式")
        print("   - 手动编辑模式")
        print("   - Excel导入功能")
        print("   - 图表生成和导出")
        return 0
    else:
        print("❌ 发现问题，请修复后再进行打包。")
        print()
        print("🔧 修复建议:")
        print("   1. 安装缺失的依赖: pip install -r requirements.txt")
        print("   2. 检查缺失的文件和目录")
        print("   3. 确保所有工具模块文件存在")
        return 1

if __name__ == "__main__":
    sys.exit(main())
