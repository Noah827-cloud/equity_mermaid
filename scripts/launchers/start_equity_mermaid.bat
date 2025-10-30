@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Equity Mermaid Tool - Unified Launcher
echo ========================================
echo.

:: Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%dist\equity_mermaid_tool_incremental

:: Check if the application directory exists
if not exist "%APP_DIR%" (
    echo [ERROR] Application directory not found at %APP_DIR%
    echo Please run the build script first.
    pause
    exit /b 1
)

:: Check if the executable exists
if not exist "%APP_DIR%\equity_mermaid_tool_incremental.exe" (
    echo [ERROR] Application executable not found at %APP_DIR%\equity_mermaid_tool_incremental.exe
    pause
    exit /b 1
)

:: Check for command line arguments
set "SKIP_FIX=%~1"
if /I "%SKIP_FIX%"=="--skip-fix" goto START_APP

:: Apply enhanced static file fix
echo [1/2] Applying enhanced static file fix...
call :ENHANCED_STATIC_FIX
if errorlevel 1 (
    echo [ERROR] Static file fix failed.
    pause
    exit /b 1
)

:START_APP
echo [2/2] Starting the application...
start "" "%APP_DIR%\equity_mermaid_tool_incremental.exe"

echo.
echo ========================================
echo [SUCCESS] Application started successfully!
echo ========================================
echo The console window can be closed now.
echo.
timeout /t 3 >nul
exit /b 0

:ENHANCED_STATIC_FIX
echo [Static Fix] Attempting enhanced static file fix...
if exist "scripts\verify_streamlit_static.py" (
    call "%PYTHON%" "scripts\verify_streamlit_static.py" "%APP_DIR%"
    if not errorlevel 1 (
        echo [Static Fix] Enhanced static file fix completed successfully.
        goto :EOF
    )
    echo [Static Fix] Enhanced fix failed, falling back to basic fix...
) else (
    echo [Static Fix] verify_streamlit_static.py not found, using basic fix...
)

:: Basic static file fix as fallback
if not exist "%APP_DIR%\streamlit\static" (
    echo [Static Fix] Creating streamlit static directory...
    mkdir "%APP_DIR%\streamlit\static" >nul 2>&1
)

if not exist "%APP_DIR%\streamlit\static\index.html" (
    echo [Static Fix] Creating basic index.html file...
    echo ^<!DOCTYPE html^> > "%APP_DIR%\streamlit\static\index.html"
    echo ^<html^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^<head^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^<title^>Streamlit Static File^</title^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^</head^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^<body^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^<h1^>Streamlit Static File^</h1^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^</body^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^</html^> >> "%APP_DIR%\streamlit\static\index.html"
    echo [Static Fix] Basic static file fix completed.
) else (
    echo [Static Fix] Static files already exist, no action needed.
)
goto :EOF