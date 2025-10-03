#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构图生成工具 - 统一启动脚本

此脚本提供一个简单的命令行界面，用于启动不同的功能模块。
"""

import os
import sys
import subprocess
import platform

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def clear_screen():
    """清除屏幕"""
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

def print_banner():
    """打印程序横幅"""
    banner = """
    ===============================================================================
                        股权结构图生成工具
    ===============================================================================
    """
    print(banner)

def show_menu():
    """显示菜单选项"""
    print("\n请选择要启动的功能模块:")
    print("1. 主界面 (端口: 8504)")
    print("2. 图像识别模式 (端口: 8501)")
    print("3. 手动编辑模式 (端口: 8503)")
    print("4. 启动所有模块 (需要多个终端窗口)")
    print("5. 退出")

def get_user_choice():
    """获取用户选择"""
    while True:
        try:
            choice = int(input("\n请输入选择 (1-5): "))
            if 1 <= choice <= 5:
                return choice
            else:
                print("无效的选择，请输入1-5之间的数字")
        except ValueError:
            print("无效输入，请输入数字")

def run_streamlit_app(app_name, file_path, port):
    """运行Streamlit应用"""
    print(f"\n正在启动{app_name}...")
    print(f"应用文件: {file_path}")
    print(f"端口: {port}")
    print(f"\n请访问 http://localhost:{port}")
    print("注意：此窗口将被锁定，请在浏览器中访问上述地址")
    print("按 Ctrl+C 停止服务")
    print("\n" + "-"*50)
    
    # 构建命令
    cmd = [sys.executable, '-m', 'streamlit', 'run', file_path, f'--server.port={port}']
    
    try:
        # 执行命令
        subprocess.run(cmd, cwd=ROOT_DIR)
    except KeyboardInterrupt:
        print(f"\n{app_name}已停止")

def start_all_apps():
    """启动所有应用（通过新的终端窗口）"""
    print("\n将通过新的终端窗口启动所有模块...")
    
    apps = [
        ("主界面", "main_page.py", 8504),
        ("图像识别模式", "src/main/enhanced_equity_to_mermaid.py", 8501),
        ("手动编辑模式", "src/main/manual_equity_editor.py", 8503)
    ]
    
    if platform.system() == 'Windows':
        # Windows系统使用start命令
        for name, file_path, port in apps:
            full_path = os.path.join(ROOT_DIR, file_path)
            cmd = f'start cmd /k "echo 正在启动{name}... & python -m streamlit run {full_path} --server.port={port}"'
            subprocess.Popen(cmd, shell=True)
    else:
        # macOS和Linux使用open或xterm
        for name, file_path, port in apps:
            full_path = os.path.join(ROOT_DIR, file_path)
            if platform.system() == 'Darwin':  # macOS
                cmd = ['open', '-a', 'Terminal', 'python', '-m', 'streamlit', 'run', full_path, f'--server.port={port}']
            else:  # Linux
                cmd = ['xterm', '-e', 'python', '-m', 'streamlit', 'run', full_path, f'--server.port={port}']
            subprocess.Popen(cmd)
    
    print("\n所有模块已开始启动，请查看新打开的终端窗口")
    input("\n按Enter键返回菜单...")

def main():
    """主函数"""
    apps = {
        1: ("主界面", "main_page.py", 8504),
        2: ("图像识别模式", "src/main/enhanced_equity_to_mermaid.py", 8501),
        3: ("手动编辑模式", "src/main/manual_equity_editor.py", 8503)
    }
    
    while True:
        clear_screen()
        print_banner()
        show_menu()
        choice = get_user_choice()
        
        if choice == 5:
            print("\n感谢使用股权结构图生成工具，再见！")
            break
        elif choice == 4:
            start_all_apps()
        elif choice in apps:
            name, file_path, port = apps[choice]
            full_path = os.path.join(ROOT_DIR, file_path)
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                print(f"\n错误: 未找到应用文件 {full_path}")
                input("按Enter键返回菜单...")
                continue
            
            run_streamlit_app(name, full_path, port)
            input("\n按Enter键返回菜单...")

if __name__ == "__main__":
    main()