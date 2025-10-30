@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 获取脚本所在目录（适用于分发场景）
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

:: 应用程序目录（脚本所在目录）
set APP_DIR=%SCRIPT_DIR%

:: 可执行文件路径
set EXE_PATH=%APP_DIR%\equity_mermaid_tool_incremental.exe

:: 解析命令行参数
set SKIP_FIX=false
if "%1"=="--skip-fix" (
    set SKIP_FIX=true
    echo 参数检测: 跳过静态文件修复
)

echo ========================================
echo 股权结构图工具 - 分发版启动脚本
echo ========================================
echo 脚本目录: %SCRIPT_DIR%
echo 应用目录: %APP_DIR%
echo 可执行文件: %EXE_PATH%
echo 跳过修复: %SKIP_FIX%
echo ========================================

:: 检查可执行文件是否存在
if not exist "%EXE_PATH%" (
    echo 错误: 找不到可执行文件 %EXE_PATH%
    echo 请确保 equity_mermaid_tool_incremental.exe 在脚本所在目录中
    pause
    exit /b 1
)

:: 检查静态文件目录是否存在
set STATIC_DIR=%APP_DIR%\static
if not exist "%STATIC_DIR%" (
    echo 警告: 找不到静态文件目录 %STATIC_DIR%
    echo 将创建基础静态文件目录结构...
    if not exist "%STATIC_DIR%" mkdir "%STATIC_DIR%"
)

:: 检查streamlit配置目录
set STREAMLIT_DIR=%APP_DIR%\.streamlit
if not exist "%STREAMLIT_DIR%" (
    echo 警告: 找不到Streamlit配置目录 %STREAMLIT_DIR%
    echo 将创建基础Streamlit配置目录...
    if not exist "%STREAMLIT_DIR%" mkdir "%STREAMLIT_DIR%"
)

:: 静态文件修复逻辑（简化版，适用于分发场景）
if "%SKIP_FIX%"=="false" (
    echo.
    echo ========================================
    echo 静态文件修复
    echo ========================================
    
    :: 检查index.html是否存在
    set INDEX_PATH=%STATIC_DIR%\index.html
    if not exist "%INDEX_PATH%" (
        echo 创建基础index.html文件...
        (
            echo ^<!DOCTYPE html^>
            echo ^<html^>
            echo ^<head^>
            echo     ^<meta charset="UTF-8"^>
            echo     ^<title^>股权结构图工具^</title^>
            echo ^</head^>
            echo ^<body^>
            echo     ^<h1^>股权结构图工具正在加载...^</h1^>
            echo     ^<p^>如果页面长时间未加载，请检查应用程序是否正常运行。^</p^>
            echo ^</body^>
            echo ^</html^>
        ) > "%INDEX_PATH%"
        echo 基础index.html文件已创建
    ) else (
        echo index.html文件已存在，跳过创建
    )
    
    :: 检查streamlit配置文件
    set CONFIG_PATH=%STREAMLIT_DIR%\config.toml
    if not exist "%CONFIG_PATH%" (
        echo 创建基础Streamlit配置文件...
        (
            echo [server]
            echo port = 8504
            echo address = "127.0.0.1"
            echo.
            echo [browser]
            echo gatherUsageStats = false
        ) > "%CONFIG_PATH%"
        echo 基础Streamlit配置文件已创建
    ) else (
        echo Streamlit配置文件已存在，跳过创建
    )
    
    echo 静态文件修复完成
) else (
    echo 跳过静态文件修复（根据用户参数）
)

:: 启动应用程序
echo.
echo ========================================
echo 启动应用程序
echo ========================================
echo 正在启动: %EXE_PATH%
echo.

:: 启动应用程序并捕获退出代码
"%EXE_PATH%"
set EXIT_CODE=%ERRORLEVEL%

echo.
echo 应用程序已退出，退出代码: %EXIT_CODE%

:: 根据退出代码提供不同的提示
if %EXIT_CODE% neq 0 (
    echo.
    echo ========================================
    echo 故障排除提示
    echo ========================================
    echo 如果应用程序无法正常启动，请尝试以下步骤：
    echo 1. 确保系统满足最低要求
    echo 2. 检查是否有防病毒软件阻止应用程序运行
    echo 3. 尝试以管理员身份运行此脚本
    echo 4. 使用 --skip-fix 参数跳过静态文件修复
    echo.
    echo 按任意键退出...
    pause >nul
) else (
    echo 应用程序正常退出
)

exit /b %EXIT_CODE%