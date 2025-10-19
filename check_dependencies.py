#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖检查脚本
用于验证项目所需的所有依赖是否正确安装
"""

import sys
import importlib.util

# 定义所需的依赖及其最低版本
REQUIRED_PACKAGES = {
    'streamlit': '1.32.0',
    'streamlit_mermaid': '0.2.0',
    'dashscope': '1.10.0',
    'requests': '2.31.0',
    'pandas': '2.0.0',
    'openpyxl': '3.1.0',
    'pyarrow': '10.0.0',
    'dotenv': '1.0.0',
    'cryptography': '42.0.0',
    'PIL': '10.0.0',  # Pillow
    'typing_extensions': '4.5.0',
}

# 标准库模块（无需检查版本）
STDLIB_MODULES = [
    'os', 'sys', 'json', 're', 'time', 'datetime', 'pathlib',
    'subprocess', 'tempfile', 'webbrowser', 'base64', 'hashlib',
    'hmac', 'uuid', 'urllib', 'logging', 'argparse', 'shutil'
]

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

def check_stdlib_module(module_name):
    """检查标准库模块是否可用"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        print(f"⚠ 标准库模块 {module_name} 不可用")
        return False

def main():
    print("=" * 60)
    print("股权结构可视化工具 - 依赖检查")
    print("=" * 60)
    print()
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"Python 版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version < (3, 8):
        print("⚠ 警告: 建议使用Python 3.8或更高版本")
    print()
    
    # 检查第三方包
    print("检查第三方依赖包...")
    print("-" * 60)
    all_installed = True
    for package, min_version in REQUIRED_PACKAGES.items():
        if not check_package(package, min_version):
            all_installed = False
    
    print()
    print("-" * 60)
    
    # 检查标准库模块
    print("\n检查标准库模块...")
    print("-" * 60)
    stdlib_ok = True
    for module in STDLIB_MODULES:
        if not check_stdlib_module(module):
            stdlib_ok = False
    
    if stdlib_ok:
        print("✓ 所有标准库模块正常")
    
    print()
    print("=" * 60)
    
    # 输出总结
    if all_installed and stdlib_ok:
        print("✓ 所有依赖检查通过！可以进行打包。")
        return 0
    else:
        print("✗ 部分依赖未满足，请安装缺失的包：")
        print("   pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())

