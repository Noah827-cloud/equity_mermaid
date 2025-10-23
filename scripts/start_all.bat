@echo off
chcp 65001 >nul
cls
echo ===============================================================================
echo                    股权结构图生成工具 - 启动脚本
echo ===============================================================================
echo.
echo 1. 启动主界面(推荐) (端口: 8504)
echo 2. 启动图像识别模式 (端口: 8501)
echo 3. 启动手动编辑模式 (端口: 8502)
echo 4. 退出
echo.

set /p choice=请选择功能 (1-4): 

if %choice%==1 (
    echo 正在启动主界面(推荐)...
    "C:\Users\z001syzk\AppData\Local\Programs\Python\Python313\python.exe" -m streamlit run main_page.py --server.port=8504
) else if %choice%==2 (
    echo 正在启动图像识别模式...
    "C:\Users\z001syzk\AppData\Local\Programs\Python\Python313\python.exe" -m streamlit run pages\1_图像识别模式.py --server.port=8501
) else if %choice%==3 (
    echo 正在启动手动编辑模式...
    "C:\Users\z001syzk\AppData\Local\Programs\Python\Python313\python.exe" -m streamlit run pages\2_手动编辑模式.py --server.port=8502
) else if %choice%==4 (
    echo 退出程序...
    exit
) else (
    echo 无效的选择，请重新运行脚本。
    pause
    exit
)

pause