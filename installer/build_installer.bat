@echo off
REM =============================================
REM Equity Mermaid Tool - Installer Builder
REM =============================================
echo.
echo Building installer package...
echo.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

REM Step 1: Check if Inno Setup is installed
echo [Step 1/4] Checking Inno Setup installation...
echo.

set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe

if not exist "%INNO_PATH%" (
    echo [ERROR] Inno Setup not found!
    echo.
    echo Expected location: C:\Program Files ^(x86^)\Inno Setup 6\
    echo.
    echo Please install Inno Setup from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo After installation, run this script again.
    echo.
    pause
    exit /b 1
)

echo [OK] Inno Setup found: %INNO_PATH%
echo.

REM Step 2: Check if packaged files exist
echo [Step 2/4] Checking packaged files...
echo.

set "DIST_ROOT=%PROJECT_ROOT%\dist_slim\equity_mermaid_tool_incremental"
set "DIST_EXE=%PROJECT_ROOT%\dist_slim\equity_mermaid_tool_incremental.exe"

if not exist "%DIST_EXE%" (
    echo [ERROR] Packaged exe file not found!
    echo.
    echo Please run build_exe_slim.bat ^(or the slim build workflow^) first.
    echo Expected path: %DIST_EXE%
    echo.
    pause
    exit /b 1
)

if not exist "%DIST_ROOT%\app\" (
    echo [ERROR] app directory not found!
    echo.
    echo The slim build should produce an app\ directory with bundled resources.
    echo Expected path: %DIST_ROOT%\app\
    echo.
    pause
    exit /b 1
)

echo [OK] Packaged files found
echo.

REM Step 3: Create output directory
echo [Step 3/4] Preparing output directory...
echo.

if not exist "..\installer_output\" (
    mkdir "..\installer_output"
    echo [OK] Created output directory: installer_output\
) else (
    echo [OK] Output directory exists: installer_output\
)
echo.

REM Step 4: Compile installer
echo [Step 4/4] Compiling installer...
echo.
echo This may take a few minutes, please wait...
echo.

"%INNO_PATH%" "equity_mermaid_setup.iss"

if %errorlevel% equ 0 (
    echo.
    echo =============================================
    echo SUCCESS! Installer package created!
    echo =============================================
    echo.
    
    REM Find and display the generated installer
    for %%F in (..\installer_output\EquityMermaidTool_Setup_*.exe) do (
        echo Package location: %%F
        echo File size: %%~zF bytes
        echo.
    )
    
    echo Next steps:
    echo   1. Test the installer on a clean system
    echo   2. Test installation process
    echo   3. Test uninstallation
    echo   4. Distribute to users
    echo.
    
    echo Installer features:
    echo   - Auto install to Program Files
    echo   - Start menu shortcuts
    echo   - Optional desktop shortcut
    echo   - Complete uninstall support
    echo   - Modern installation wizard
    echo.
    
    REM Ask to open output directory
    echo Open output directory? (Y/N)
    set /p OPEN_DIR=
    if /i "%OPEN_DIR%"=="Y" (
        start explorer "%PROJECT_ROOT%\installer_output"
    )
    
) else (
    echo.
    echo =============================================
    echo ERROR! Installer build failed!
    echo =============================================
    echo.
    echo Possible causes:
    echo   1. Inno Setup configuration file has errors
    echo   2. Source file paths are incorrect
    echo   3. Insufficient disk space
    echo.
    echo Please check the error messages above.
    echo.
)

echo.
echo Press any key to exit...
pause >nul

popd >nul
