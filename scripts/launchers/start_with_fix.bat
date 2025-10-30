@echo off
setlocal enabledelayedexpansion

echo Starting Equity Mermaid Tool with static file fix...

:: Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%dist\equity_mermaid_tool_incremental

:: Check if the application directory exists
if not exist "%APP_DIR%" (
    echo Error: Application directory not found at %APP_DIR%
    echo Please run the build script first.
    pause
    exit /b 1
)

:: Fix Streamlit static files
echo Fixing Streamlit static files...
call "%SCRIPT_DIR%scripts\fix_static_files.bat"

:: Check if the executable exists
if not exist "%APP_DIR%\equity_mermaid_tool_incremental.exe" (
    echo Error: Application executable not found at %APP_DIR%\equity_mermaid_tool_incremental.exe
    pause
    exit /b 1
)

:: Start the application
echo Starting the application...
start "" "%APP_DIR%\equity_mermaid_tool_incremental.exe"

echo Application started. The console window can be closed now.
timeout /t 3 >nul