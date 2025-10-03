import os
import sys
import subprocess
import traceback

# 设置当前工作目录
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(current_dir)

print(f"当前工作目录: {current_dir}")

# 定义应用程序配置
def get_app_config():
    return {
        1: {
            'name': '主界面(推荐)',
            'file': os.path.join(current_dir, 'main_page.py'),
            'port': 8504
        },
        2: {
            'name': '图像识别模式', 
            'file': os.path.join(current_dir, 'src', 'main', 'enhanced_equity_to_mermaid.py'),
            'port': 8501
        },
        3: {
            'name': '手动编辑模式',
            'file': os.path.join(current_dir, 'src', 'main', 'manual_equity_editor.py'),
            'port': 8503
        }
    }

# 显示菜单并获取用户选择
def get_user_choice():
    print("\n请选择要启动的模块:")
    print("1. 主界面(推荐) (端口: 8504)")
    print("2. 图像识别模式 (端口: 8501)")
    print("3. 手动编辑模式 (端口: 8503)")
    print("4. 退出")
    
    try:
        choice = int(input("\n请输入选择 (1-4): "))
        return choice
    except ValueError:
        print("无效输入，请输入数字")
        return None

# 启动Streamlit应用
def start_streamlit_app(app_config):
    app_name = app_config['name']
    app_file = app_config['file']
    port = app_config['port']
    
    # 检查应用文件是否存在
    if not os.path.exists(app_file):
        print(f"错误: 未找到应用文件 {app_file}")
        return False
    
    print(f"正在启动{app_name}...")
    print(f"应用文件: {app_file}")
    print(f"端口: {port}")
    
    # 构建streamlit命令
    streamlit_cmd = [
        'streamlit', 
        'run', 
        app_file,
        f'--server.port={port}',
        '--server.address=localhost'
    ]
    
    print(f"\n请访问 http://localhost:{port}")
    print("注意：请勿关闭此窗口")
    print("按 Ctrl+C 停止服务")
    print("\n" + "-"*50)
    
    try:
        # 执行streamlit命令
        process = subprocess.Popen(
            streamlit_cmd,
            shell=True,  # 在Windows上使用shell=True
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 实时输出Streamlit的日志
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # 检查是否有错误
        stderr = process.stderr.read()
        if stderr:
            print(f"错误输出: {stderr}")
        
        return True
    except Exception as e:
        print(f"启动应用时发生错误: {str(e)}")
        traceback.print_exc()
        return False

# 主函数
def main():
    app_configs = get_app_config()
    
    while True:
        choice = get_user_choice()
        if choice is None:
            continue
        
        if choice == 4:
            print("退出程序...")
            break
        elif choice in app_configs:
            start_streamlit_app(app_configs[choice])
            input("\n按Enter键返回菜单...")
        else:
            print("无效的选择，请重新输入")

if __name__ == "__main__":
    main()