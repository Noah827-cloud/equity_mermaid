import os
import sys
import subprocess
import traceback

# 设置当前工作目录
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(current_dir)

print(f"当前工作目录: {current_dir}")

# 直接启动主界面(main_page.py)
def start_main_page():
    app_name = '主界面(推荐)'
    app_file = os.path.join(current_dir, 'main_page.py')
    port = 8504
    
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
    # 直接启动主界面，不再提供菜单选择
    start_main_page()

if __name__ == "__main__":
    main()