@echo off
echo ========================================
echo 股权结构可视化工具 - EXE打包脚本
echo ========================================

echo 检查Python环境...
C:\Users\z001syzk\AppData\Local\anaconda3\python.exe --version
if %errorlevel% neq 0 (
    echo 错误: Python环境未找到
    pause
    exit /b 1
)

echo 检查PyInstaller...
C:\Users\z001syzk\AppData\Local\anaconda3\python.exe -c "import PyInstaller; print('PyInstaller版本:', PyInstaller.__version__)"
if %errorlevel% neq 0 (
    echo 错误: PyInstaller未安装
    echo 正在安装PyInstaller...
    C:\Users\z001syzk\AppData\Local\anaconda3\python.exe -m pip install pyinstaller
)

echo 检查依赖文件...
if not exist "equity_mermaid.spec" (
    echo 错误: equity_mermaid.spec文件不存在
    pause
    exit /b 1
)

if not exist "run_st.py" (
    echo 错误: run_st.py文件不存在
    pause
    exit /b 1
)

echo 检查新增的visjs相关文件...
if not exist "src\utils\visjs_equity_chart.py" (
    echo 错误: visjs_equity_chart.py文件不存在
    pause
    exit /b 1
)

if not exist "src\utils\icon_integration.py" (
    echo 错误: icon_integration.py文件不存在
    pause
    exit /b 1
)

if not exist "src\utils\uvx_helper.py" (
    echo 错误: uvx_helper.py文件不存在
    pause
    exit /b 1
)

echo 检查SVG图标资源...
if not exist "src\assets\icons\" (
    echo 错误: SVG图标目录不存在
    pause
    exit /b 1
)

echo 开始打包...
echo 使用配置文件: equity_mermaid.spec
echo 输出目录: dist\equity_mermaid_tool_fixed

C:\Users\z001syzk\AppData\Local\anaconda3\python.exe -m PyInstaller equity_mermaid.spec --noconfirm

if %errorlevel% equ 0 (
    echo ========================================
    echo 打包成功！
    echo 输出文件: dist\equity_mermaid_tool_fixed\equity_mermaid_tool.exe
    echo ========================================
    
    echo 检查输出文件...
    if exist "dist\equity_mermaid_tool_fixed\equity_mermaid_tool.exe" (
        echo ✅ 主程序文件存在
        dir "dist\equity_mermaid_tool_fixed\equity_mermaid_tool.exe"
    ) else (
        echo ❌ 主程序文件不存在
    )
    
    echo 检查visjs相关文件...
    if exist "dist\equity_mermaid_tool_fixed\src\utils\visjs_equity_chart.py" (
        echo ✅ visjs_equity_chart.py已包含
    ) else (
        echo ❌ visjs_equity_chart.py未包含
    )
    
    if exist "dist\equity_mermaid_tool_fixed\src\assets\icons\" (
        echo ✅ SVG图标资源已包含
        dir "dist\equity_mermaid_tool_fixed\src\assets\icons\"
    ) else (
        echo ❌ SVG图标资源未包含
    )
    
) else (
    echo ========================================
    echo 打包失败！
    echo 请检查错误信息并修复问题
    echo ========================================
)

echo 按任意键退出...
pause
