# run_st.py
import os
import sys
from dotenv import load_dotenv
import streamlit.web.bootstrap as st_boot
import streamlit.config

# 添加当前目录到Python路径，确保能找到src模块
sys.path.insert(0, os.path.dirname(__file__))

# 导入uvx_helper模块
from src.utils import uvx_helper

# 加载.env文件中的环境变量
load_dotenv()

# 打印使用的UVX路径
print(f"使用的UVX路径: {uvx_helper.get_uvx_path()}")

# 设置环境变量，确保Streamlit使用正确的端口
os.environ['STREAMLIT_SERVER_PORT'] = '8501'
os.environ['STREAMLIT_SERVER_ADDRESS'] = '127.0.0.1'
os.environ['STREAMLIT_GLOBAL_DEVELOPMENTMODE'] = 'false'

# 直接修改Streamlit配置
streamlit.config.set_option('server.port', 8501)
streamlit.config.set_option('server.address', '127.0.0.1')
streamlit.config.set_option('server.headless', True)
streamlit.config.set_option('global.developmentMode', False)
streamlit.config.set_option('server.runOnSave', False)
streamlit.config.set_option('server.enableStaticServing', True)

if __name__ == '__main__':
    # 使用绝对路径指向main_page.py
    real_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_page.py')
    
    # 强制使用8501端口，禁用开发模式，并设置相关参数
    st_boot.run(
        real_script,
        False,
        ['--server.port', '8501',
         '--server.address', '127.0.0.1',
         '--server.headless=true',
         '--global.developmentMode=false',
         '--server.runOnSave=false',  # 禁用文件保存时自动重启
         '--server.enableStaticServing=true'],  # 启用静态文件服务
        {}  # 空的flag_options
    )