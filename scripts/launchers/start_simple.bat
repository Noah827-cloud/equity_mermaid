@echo off
setlocal enabledelayedexpansion

echo Starting Equity Mermaid Tool...

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