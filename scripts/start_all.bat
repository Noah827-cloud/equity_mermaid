@echo off
cls
echo ===============================================================================
echo                    股权结构图生成工具 - 启动脚本
 echo ===============================================================================
echo.
echo 1. 启动主界面
 echo 2. 启动图像识别模式
 echo 3. 启动手动编辑模式
 echo 4. 退出
 echo.

set /p choice=请选择功能 (1-4): 

if %choice%==1 (
    echo 正在启动主界面...
    python -m streamlit run src\main\equity_tool_main.py
) else if %choice%==2 (
    echo 正在启动图像识别模式...
    python -m streamlit run src\main\enhanced_equity_to_mermaid.py
) else if %choice%==3 (
    echo 正在启动手动编辑模式...
    python -m streamlit run src\main\manual_equity_editor.py
) else if %choice%==4 (
    echo 退出程序...
    exit
) else (
    echo 无效的选择，请重新运行脚本。
    pause
    exit
)

pause