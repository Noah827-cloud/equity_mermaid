@echo off
echo ========================================
echo 股权结构可视化工具 - 智能打包脚本
echo ========================================
echo.

echo [1/4] 检查Python环境...
C:\Users\z001syzk\AppData\Local\anaconda3\python.exe --version
if %errorlevel% neq 0 (
    echo ❌ 错误: Python环境未找到
    echo 请确保Anaconda已正确安装
    pause
    exit /b 1
)
echo ✅ Python环境正常

echo.
echo [2/4] 运行综合检查...
C:\Users\z001syzk\AppData\Local\anaconda3\python.exe check_all.py
if %errorlevel% neq 0 (
    echo ❌ 综合检查失败，请修复问题后再打包
    echo.
    echo 常见解决方案:
    echo 1. 安装缺失依赖: pip install -r requirements.txt
    echo 2. 检查文件结构是否完整
    echo 3. 确保所有工具模块文件存在
    pause
    exit /b 1
)
echo ✅ 综合检查通过

echo.
echo [3/4] 检查PyInstaller...
C:\Users\z001syzk\AppData\Local\anaconda3\python.exe -c "import PyInstaller; print('PyInstaller版本:', PyInstaller.__version__)"
if %errorlevel% neq 0 (
    echo ⚠️ PyInstaller未安装，正在安装...
    C:\Users\z001syzk\AppData\Local\anaconda3\python.exe -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ❌ PyInstaller安装失败
        pause
        exit /b 1
    )
)
echo ✅ PyInstaller就绪

echo.
echo [4/4] 开始打包...
echo 使用配置文件: equity_mermaid.spec
echo 输出目录: dist\equity_mermaid_tool_fixed
echo.

C:\Users\z001syzk\AppData\Local\anaconda3\python.exe -m PyInstaller equity_mermaid.spec --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo 🎉 打包成功！
    echo ========================================
    echo.
    echo 📦 输出文件: dist\equity_mermaid_tool_fixed\equity_mermaid_tool.exe
    echo.
    
    echo 验证打包结果...
    if exist "dist\equity_mermaid_tool_fixed\equity_mermaid_tool.exe" (
        echo ✅ 主程序文件存在
        for %%I in ("dist\equity_mermaid_tool_fixed\equity_mermaid_tool.exe") do echo    文件大小: %%~zI 字节
    ) else (
        echo ❌ 主程序文件不存在
    )
    
    echo 检查关键模块...
    if exist "dist\equity_mermaid_tool_fixed\src\utils\visjs_equity_chart.py" (
        echo ✅ visjs图表模块已包含
    ) else (
        echo ❌ visjs图表模块未包含
    )
    
    if exist "dist\equity_mermaid_tool_fixed\src\utils\state_persistence.py" (
        echo ✅ 状态持久化模块已包含
    ) else (
        echo ❌ 状态持久化模块未包含
    )
    
    if exist "dist\equity_mermaid_tool_fixed\src\utils\excel_smart_importer.py" (
        echo ✅ Excel智能导入模块已包含
    ) else (
        echo ❌ Excel智能导入模块未包含
    )
    
    if exist "dist\equity_mermaid_tool_fixed\src\assets\icons\" (
        echo ✅ SVG图标资源已包含
    ) else (
        echo ❌ SVG图标资源未包含
    )
    
    echo.
    echo 🔧 修复protobuf DLL问题...
    C:\Users\z001syzk\AppData\Local\anaconda3\python.exe fix_protobuf_issue.py
    if %errorlevel% equ 0 (
        echo ✅ protobuf DLL修复完成
    ) else (
        echo ⚠️ protobuf DLL修复失败，但exe文件已生成
    )
    
    echo.
    echo 📋 打包后建议测试:
    echo    1. 双击运行 equity_mermaid_tool.exe
    echo    2. 测试主界面启动
    echo    3. 测试图像识别模式
    echo    4. 测试手动编辑模式
    echo    5. 测试Excel导入功能
    echo    6. 测试图表生成和导出
    echo.
    
) else (
    echo.
    echo ========================================
    echo ❌ 打包失败！
    echo ========================================
    echo.
    echo 请检查以下可能的问题:
    echo 1. 依赖包是否完整安装
    echo 2. equity_mermaid.spec配置是否正确
    echo 3. 文件路径是否存在
    echo 4. 磁盘空间是否充足
    echo.
    echo 建议重新运行: python check_all.py
    echo.
)

echo 按任意键退出...
pause
