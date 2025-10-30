@echo off
setlocal enabledelayedexpansion

echo Building Equity Mermaid Tool with static file fix...

:: Get the directory where this script is located
set SCRIPT_DIR=%~dp0

:: Clean previous build
echo Cleaning previous build...
if exist "%SCRIPT_DIR%dist\equity_mermaid_tool_incremental" (
    rmdir /s /q "%SCRIPT_DIR%dist\equity_mermaid_tool_incremental"
)

:: Build the application
echo Building the application with PyInstaller...
py -m PyInstaller --clean equity_mermaid_incremental.spec

:: Check if build was successful
if exist "%SCRIPT_DIR%dist\equity_mermaid_tool_incremental\equity_mermaid_tool_incremental.exe" (
    echo Build completed successfully.
    
    :: Run the static file fix
echo Running static file fix...
call "%SCRIPT_DIR%scripts\fix_static_files.bat"
    
    echo.
    echo Build and fix completed. You can now run the application using:
    echo %SCRIPT_DIR%start_equity_mermaid_with_fix.bat
) else (
    echo Build failed. Please check the error messages above.
)

pause