@echo off
setlocal enabledelayedexpansion

echo Fixing Streamlit static files...

:: Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set APP_DIR=%PROJECT_DIR%\dist\equity_mermaid_tool_incremental

:: Check if the application directory exists
if not exist "%APP_DIR%" (
    echo Error: Application directory not found at %APP_DIR%
    pause
    exit /b 1
)

:: Create the streamlit static directory if it doesn't exist
if not exist "%APP_DIR%\streamlit\static" (
    echo Creating streamlit static directory...
    mkdir "%APP_DIR%\streamlit\static"
)

:: Check if index.html exists in the static directory
if not exist "%APP_DIR%\streamlit\static\index.html" (
    echo Creating index.html file...
    echo ^<!DOCTYPE html^> > "%APP_DIR%\streamlit\static\index.html"
    echo ^<html^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^<head^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^<title^>Streamlit Static File^</title^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^</head^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^<body^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^<h1^>Streamlit Static File^</h1^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^</body^> >> "%APP_DIR%\streamlit\static\index.html"
    echo ^</html^> >> "%APP_DIR%\streamlit\static\index.html"
)

echo Streamlit static files fixed successfully.
pause