@echo off

:: 股权结构可视化工具启动脚本
:: 此脚本用于启动推荐的main_page.py主入口

echo 正在启动股权结构可视化工具...
echo 使用推荐的主入口: main_page.py
echo. 

python -m streamlit run main_page.py

:: 保持窗口打开，以便查看错误信息
pause