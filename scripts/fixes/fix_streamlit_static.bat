@echo off
REM Manual fix script for Streamlit static file path issue in incremental bundle
REM This script creates a junction link from streamlit/static to app/streamlit/static

setlocal enabledelayedexpansion

echo ========================================
echo Streamlit Static File Path Fix Script
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires administrator privileges to create junction links.
    echo Please run this script as administrator.
    pause
    exit /b 1
)

REM Set the distribution directory
set DIST_DIR=dist\equity_mermaid_tool_incremental

REM Check if the distribution directory exists
if not exist "%DIST_DIR%" (
    echo ERROR: Distribution directory not found: %DIST_DIR%
    echo Please run the incremental build first.
    pause
    exit /b 1
)

REM Check if app/streamlit/static exists
set APP_STATIC_DIR=%DIST_DIR%\app\streamlit\static
if not exist "%APP_STATIC_DIR%" (
    echo ERROR: Streamlit static files not found at %APP_STATIC_DIR%
    echo Please ensure the build completed successfully.
    pause
    exit /b 1
)

REM Check if index.html exists
if not exist "%APP_STATIC_DIR%\index.html" (
    echo ERROR: index.html not found at %APP_STATIC_DIR%
    echo Please ensure the build completed successfully.
    pause
    exit /b 1
)

REM Create the streamlit directory if it doesn't exist
set STREAMLIT_DIR=%DIST_DIR%\streamlit
if not exist "%STREAMLIT_DIR%" (
    echo Creating directory: %STREAMLIT_DIR%
    mkdir "%STREAMLIT_DIR%"
)

REM Remove existing static directory if it exists (but is not a junction)
set STATIC_DIR=%STREAMLIT_DIR%\static
if exist "%STATIC_DIR%" (
    if not exist "%STATIC_DIR%\junction" (
        echo Removing existing directory: %STATIC_DIR%
        rmdir /s /q "%STATIC_DIR%"
    )
)

REM Create the junction link
echo Creating junction link from %STATIC_DIR% to %APP_STATIC_DIR%
mklink /J "%STATIC_DIR%" "%APP_STATIC_DIR%"

if %errorLevel% neq 0 (
    echo ERROR: Failed to create junction link.
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS: Junction link created successfully!
echo ========================================
echo.
echo The Streamlit static file path issue has been fixed.
echo You can now run the incremental bundle without errors.
echo.
pause
exit /b 0