@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Streamlit Static File Path Fix Script (No Admin)
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

echo Copying static files from app/streamlit/static to streamlit/static...
xcopy "%app_streamlit_static_dir%\*" "%streamlit_static_dir%\" /E /Y /Q

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Static files copied successfully.
    echo Streamlit should now be able to find its static files.
) else (
    echo.
    echo ERROR: Failed to copy static files.
    echo Error code: %ERRORLEVEL%
)

echo.
echo Fix completed. You can now run the application.
pause