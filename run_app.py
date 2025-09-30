import os
import sys
import subprocess
import traceback

# 设置当前工作目录为EXE所在目录
sys.path.append(os.path.dirname(os.path.abspath(sys.executable)))
current_dir = os.path.dirname(os.path.abspath(sys.executable))
os.chdir(current_dir)

print(f"当前工作目录: {current_dir}")

# 检查manual_equity_editor.py是否存在
app_file = os.path.join(current_dir, 'manual_equity_editor.py')
if os.path.exists(app_file):
    print(f"找到应用文件: {app_file}")
else:
    print(f"错误: 未找到应用文件 {app_file}")
    input("按Enter键退出...")
    sys.exit(1)

try:
    print("正在启动Streamlit应用...")
    
    # 使用subprocess调用系统中的streamlit命令
    # 这样可以避免打包时的依赖问题
    streamlit_cmd = [
        'streamlit', 
        'run', 
        app_file,
        '--server.port=8504',
        '--server.address=localhost'
    ]
    
    print(f"请访问 http://localhost:8504")
    print("注意：请勿关闭此窗口")
    
    # 执行streamlit命令
    process = subprocess.Popen(
        streamlit_cmd,
        shell=True,  # 使用shell=True来确保命令可以在Windows上正确执行
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
    
    # 检查错误
    stderr = process.stderr.read()
    if stderr:
        print(f"错误: {stderr}")
    
    # 等待进程结束
    process.wait()
    
except Exception as e:
    print(f"启动应用时出错: {str(e)}")
    print("错误详情:")
    print(traceback.format_exc())
    
    # 如果是找不到streamlit命令的错误，给出提示
    if "'streamlit' 不是内部或外部命令" in str(e):
        print("\n错误: 系统中未安装Streamlit或Streamlit不在PATH环境变量中")
        print("请确保已安装Streamlit: pip install streamlit")
    
    input("按Enter键退出...")
    sys.exit(1)

input("按Enter键退出...")