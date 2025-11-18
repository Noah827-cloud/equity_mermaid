@echo off
chcp 65001 >nul
setlocal

REM Check if patch mode is requested
set "MODE=%~1"
if /I "%MODE%"=="PATCH" (
    echo [INFO] Forwarding patch request to build_exe_incremental.bat...
    call build_exe_incremental.bat patch %2
    exit /b %ERRORLEVEL%
)

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "SPEC=equity_mermaid_slim.spec"
set "DIST_DIR=dist\equity_mermaid_tool_incremental"
set "APP_DIR=%DIST_DIR%\app"
set "PATCH_DIR=dist\patches"
set "RUNTIME_DIR=%DIST_DIR%\runtime"
set "SNAPSHOT_FILE=%DIST_DIR%\.runtime_snapshot.json"
set "RUNTIME_FLAG=%DIST_DIR%\.runtime_changed.flag"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not exist "%PYTHON%" (
    echo [ERROR] Slim virtualenv python not found: %PYTHON%
    exit /b 1
)

if not exist "%SPEC%" (
    echo [ERROR] Spec file %SPEC% missing.
    exit /b 1
)

echo ========================================
echo [Slim Incremental Build] Full workflow
echo ========================================
echo.

echo [1/4] Sync runtime data into spec definitions...
if exist "scripts\sync_utils_to_spec.py" (
    call "%PYTHON%" "scripts\sync_utils_to_spec.py"
    if errorlevel 1 (
        echo [WARN] sync_utils_to_spec.py failed, retrying with --auto...
        call "%PYTHON%" "scripts\sync_utils_to_spec.py" --auto
        if errorlevel 1 (
            echo [ERROR] sync_utils_to_spec.py failed.
            exit /b 1
        )
    )
) else (
    echo [INFO] scripts\sync_utils_to_spec.py not found, skipping.
)

echo.
echo [2/4] Running preflight checks (slim env)...
if exist "check_all.py" (
    call "%PYTHON%" "check_all.py"
    if errorlevel 1 (
        echo [ERROR] check_all.py reported issues.
        exit /b 1
    )
) else (
    echo [INFO] check_all.py not found, skipping.
)

echo.
echo [3/4] Verifying PyInstaller...
call "%PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller into slim env...
    call "%PYTHON%" -m pip install --upgrade pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        exit /b 1
    )
)

echo.
echo [Cleanup] Removing previous dist/build outputs...
if exist "%DIST_DIR%" rd /s /q "%DIST_DIR%"
if exist "build\equity_mermaid_tool_incremental" rd /s /q "build\equity_mermaid_tool_incremental"

echo.
echo [4/4] Building slim incremental distribution...
call "%PYTHON%" -m PyInstaller "%SPEC%" --noconfirm --clean
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

if exist "fix_protobuf_issue.py" (
    echo.
    echo [Post] Running protobuf fix script...
    call "%PYTHON%" "fix_protobuf_issue.py"
)

echo.
if exist "%DIST_DIR%" (
    echo [OK] Build output ready: %DIST_DIR%
    if exist "%APP_DIR%" (
        for %%I in ("%APP_DIR%") do echo         app folder: %%~fI
    ) else (
        echo [WARN] app folder missing under %DIST_DIR%.
    )
    if exist "%RUNTIME_DIR%" (
        for %%I in ("%RUNTIME_DIR%") do echo         runtime folder: %%~fI
    ) else (
        echo [WARN] runtime folder missing under %DIST_DIR%.
    )
) else (
    echo [WARN] Build folder %DIST_DIR% does not exist.
)

if exist "scripts\verify_streamlit_static.py" (
    echo.
    echo [Post] Verifying Streamlit static file paths...
    call "%PYTHON%" "scripts\verify_streamlit_static.py" "%DIST_DIR%"
    if errorlevel 1 (
        echo [ERROR] Streamlit static verification failed.
        exit /b 1
    )
)

if exist "scripts\verify_package_content.py" (
    echo.
    echo [Post] Verifying distribution contents...
    call "%PYTHON%" "scripts\verify_package_content.py" "%DIST_DIR%" --exe "equity_mermaid_tool_incremental.exe"
)

if exist "scripts\runtime_bootloader_guard.py" if exist "%DIST_DIR%" (
    echo.
    echo [Post] Recording runtime snapshot...
    call "%PYTHON%" "scripts\runtime_bootloader_guard.py" --dist "%DIST_DIR%" --exe "equity_mermaid_tool_incremental.exe" --runtime-dir "runtime" --snapshot "%SNAPSHOT_FILE%" --flag "%RUNTIME_FLAG%"
)

echo.
echo ========================================
echo Ready to create patch with either:
echo     build_exe_slim.bat patch ^<version_label^>
echo     build_exe_incremental.bat patch ^<version_label^>
echo (Both use the same dist layout.)
echo ========================================
echo.
endlocal
