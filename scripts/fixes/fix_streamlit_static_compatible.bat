@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo Streamlit静态文件修复工具 (增量更新兼容版)
echo ========================================

set "SCRIPT_DIR=%~dp0"
set "DIST_DIR=%SCRIPT_DIR%dist\equity_mermaid_tool_incremental"

set "SOURCE_DIR=%DIST_DIR%\app\streamlit\static"
set "TARGET_DIR=%DIST_DIR%\streamlit\static"

echo 源目录: %SOURCE_DIR%
echo 目标目录: %TARGET_DIR%
echo.

REM 检查源目录是否存在
if not exist "%SOURCE_DIR%" (
    echo [ERROR] 源目录不存在: %SOURCE_DIR%
    echo 请确保已正确打包应用程序。
    exit /b 1
)

REM 创建目标目录（如果不存在）
if not exist "%TARGET_DIR%" (
    echo [INFO] 创建目标目录...
    mkdir "%TARGET_DIR%" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] 无法创建目标目录: %TARGET_DIR%
        exit /b 1
    )
)

REM 复制静态文件
echo [INFO] 复制Streamlit静态文件...
powershell -NoProfile -Command "& { try { Copy-Item -Path '%SOURCE_DIR%\*' -Destination '%TARGET_DIR%' -Recurse -Force; Write-Host '[OK] 静态文件复制成功' -ForegroundColor Green; exit 0 } catch { Write-Host '[ERROR] 复制失败:' $_.Exception.Message -ForegroundColor Red; exit 1 } }"

if errorlevel 1 (
    echo [ERROR] 静态文件复制失败
    exit /b 1
)

REM 验证关键文件是否存在
if not exist "%TARGET_DIR%\index.html" (
    echo [ERROR] 关键文件缺失: index.html
    exit /b 1
)

echo.
echo [SUCCESS] Streamlit静态文件修复完成!
echo.
echo 此修复与增量更新系统兼容。
echo 如果应用了新的增量更新，请重新运行此脚本。
echo.
pause