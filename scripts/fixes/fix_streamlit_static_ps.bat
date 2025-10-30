@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Streamlit Static File Path Fix Script (PowerShell)
echo ========================================
echo.

set "dist_dir=dist\equity_mermaid_tool_incremental"
set "streamlit_static_dir=%dist_dir%\streamlit\static"
set "app_streamlit_static_dir=%dist_dir%\app\streamlit\static"

echo Checking directories...
if not exist "%streamlit_static_dir%" (
    echo Creating directory: %streamlit_static_dir%
    mkdir "%streamlit_static_dir%"
)

echo Copying static files using PowerShell...
powershell -Command "try { Copy-Item -Path '%app_streamlit_static_dir%\*' -Destination '%streamlit_static_dir%' -Recurse -Force; Write-Host 'SUCCESS: Static files copied successfully.' -ForegroundColor Green } catch { Write-Host 'ERROR: Failed to copy static files.' -ForegroundColor Red; Write-Host $_.Exception.Message -ForegroundColor Red; exit 1 }"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Streamlit should now be able to find its static files.
) else (
    echo.
    echo Failed to copy static files. Please try running this script as administrator.
)

echo.
echo Fix completed. You can now run the application.
pause