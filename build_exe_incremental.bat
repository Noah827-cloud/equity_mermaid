@echo off
chcp 65001 >nul
setlocal

set "PYTHON=C:\Users\z001syzk\AppData\Local\anaconda3\python.exe"
set "SPEC=equity_mermaid_incremental.spec"
set "DIST_DIR=dist\equity_mermaid_tool_incremental"
set "APP_DIR=%DIST_DIR%\app"
set "PATCH_DIR=dist\patches"
set "RUNTIME_DIR=%DIST_DIR%\runtime"
set "SNAPSHOT_FILE=%DIST_DIR%\.runtime_snapshot.json"
set "RUNTIME_FLAG=%DIST_DIR%\.runtime_changed.flag"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not exist "%PYTHON%" (
    echo [ERROR] Python interpreter not found at %PYTHON%.
    exit /b 1
)

set "MODE=%~1"
if /I "%MODE%"=="PATCH" goto PATCH_ONLY

call :FULL_BUILD
goto END

:FULL_BUILD
echo ========================================
echo [Incremental Build] Full bundle workflow
echo ========================================
echo.

if not exist "%SPEC%" (
    echo [ERROR] Spec file %SPEC% is missing.
    exit /b 1
)

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
echo [2/4] Running preflight checks...
if exist "check_all.py" (
    call "%PYTHON%" "check_all.py"
    if errorlevel 1 (
        echo [ERROR] check_all.py reported issues. Resolve them before rebuilding.
        exit /b 1
    )
) else (
    echo [INFO] check_all.py not found, skipping.
)

echo.
echo [3/4] Verifying PyInstaller availability...
call "%PYTHON%" -c "import PyInstaller, sys; print('PyInstaller version:', PyInstaller.__version__)"
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    call "%PYTHON%" -m pip install --upgrade pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        exit /b 1
    )
)

echo.
echo [4/4] Building incremental distribution...
call "%PYTHON%" -m PyInstaller "%SPEC%" --noconfirm
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
        echo [WARN] App folder not found under %DIST_DIR%.
    )
    if exist "%RUNTIME_DIR%" (
        for %%I in ("%RUNTIME_DIR%") do echo         runtime folder: %%~fI
    ) else (
        echo [WARN] Runtime folder not found under %DIST_DIR%.
    )
) else (
    echo [WARN] Build folder %DIST_DIR% does not exist.
)

if exist "scripts\verify_streamlit_static.py" (
    echo.
    echo [Post] Verifying Streamlit static file paths...
    call "%PYTHON%" "scripts\verify_streamlit_static.py" "%DIST_DIR%"
    if errorlevel 1 (
        echo [ERROR] Streamlit static file verification failed.
        exit /b 1
    )
)

if exist "scripts\verify_package_content.py" (
    echo.
    echo [Post] Verifying distribution contents...
    call "%PYTHON%" "scripts\verify_package_content.py" "%DIST_DIR%" --exe "equity_mermaid_tool_incremental.exe"
    if errorlevel 1 (
        echo [WARN] Distribution verification reported issues. Review the output above.
    )
)

if exist "scripts\runtime_bootloader_guard.py" if exist "%DIST_DIR%" (
    echo.
    echo [Post] Checking runtime / bootloader snapshot...
    call "%PYTHON%" "scripts\runtime_bootloader_guard.py" --dist "%DIST_DIR%" --exe "equity_mermaid_tool_incremental.exe" --runtime-dir "runtime" --snapshot "%SNAPSHOT_FILE%" --flag "%RUNTIME_FLAG%"
)

echo.
echo To create a patch package from the latest build, run:
echo     build_exe_incremental.bat patch [version_label]
echo.
exit /b 0

:PATCH_ONLY
shift
set "PATCH_VERSION=%~1"

if not exist "%APP_DIR%" (
    echo [ERROR] App folder not found. Run a full build first.
    exit /b 1
)

if exist "%RUNTIME_FLAG%" (
    echo ========================================
    echo [WARN] Runtime/bootloader drift detected.
    echo         A full installer is required; aborting patch creation.
    echo ========================================
    exit /b 1
)

set "BASELINE_VERSION="
if exist "%APP_DIR%\version.txt" (
    set /p BASELINE_VERSION=<"%APP_DIR%\version.txt"
    if defined BASELINE_VERSION (
        echo [INFO] Current baseline version: %BASELINE_VERSION%
    ) else (
        echo [WARN] version.txt is empty, baseline version unknown.
    )
) else (
    echo [WARN] version.txt not found, baseline version unknown.
)

if defined PATCH_VERSION (
    >"%APP_DIR%\version.txt" echo %PATCH_VERSION%
    if errorlevel 1 (
        echo [WARN] Failed to write version.txt into app folder.
    ) else (
        echo [INFO] version.txt updated with "%PATCH_VERSION%".
    )
)

for /f "usebackq tokens=*" %%I in (`powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"`) do set "PATCH_STAMP=%%I"
set "PATCH_NAME=equity_mermaid_patch_%PATCH_STAMP%"
set "PATCH_ROOT=%PATCH_DIR%\%PATCH_NAME%"
set "PATCH_WORK=%PATCH_ROOT%\payload"

if exist "%PATCH_ROOT%" rd /s /q "%PATCH_ROOT%"
mkdir "%PATCH_WORK%\app" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Cannot create %PATCH_WORK%.
    exit /b 1
)

echo ========================================
echo [Incremental Build] Patch packaging
echo ========================================
echo.

echo [1/5] Copying app payload...
robocopy "%APP_DIR%" "%PATCH_WORK%\app" /E /NFL /NDL /NJH /NJS /NC /NS >nul
if errorlevel 8 (
    echo [ERROR] robocopy failed while copying app payload.
    rd /s /q "%PATCH_ROOT%"
    exit /b 1
)

if defined BASELINE_VERSION (
    >"%PATCH_WORK%\required_baseline.txt" echo %BASELINE_VERSION%
    echo [INFO] Created required_baseline.txt with version: %BASELINE_VERSION%
) else (
    >"%PATCH_WORK%\required_baseline.txt" echo UNKNOWN
    echo [WARN] Created required_baseline.txt with UNKNOWN version.
)

echo [2/5] Generating patch archive...
powershell -NoProfile -Command "Compress-Archive -Path '%PATCH_WORK%\app','%PATCH_WORK%\required_baseline.txt' -DestinationPath '%PATCH_ROOT%\%PATCH_NAME%.zip' -Force" >nul
if not exist "%PATCH_ROOT%\%PATCH_NAME%.zip" (
    echo [ERROR] Failed to create patch archive.
    rd /s /q "%PATCH_ROOT%"
    exit /b 1
)

echo [3/5] Generating SHA256 checksum...
powershell -NoProfile -Command "$hash = (Get-FileHash -Path '%PATCH_ROOT%\%PATCH_NAME%.zip' -Algorithm SHA256).Hash; $hash | Out-File -FilePath '%PATCH_ROOT%\%PATCH_NAME%.zip.sha256' -Encoding ASCII -NoNewline"
if exist "%PATCH_ROOT%\%PATCH_NAME%.zip.sha256" (
    for /f "usebackq tokens=*" %%H in ("%PATCH_ROOT%\%PATCH_NAME%.zip.sha256") do (
        echo [INFO] SHA256: %%H
    )
) else (
    echo [WARN] Failed to generate SHA256 checksum.
)

echo [4/5] Copying update helper script...
if exist "scripts\apply_incremental_patch.bat" (
    copy /Y "scripts\apply_incremental_patch.bat" "%PATCH_ROOT%\" >nul
) else (
    echo [WARN] scripts\apply_incremental_patch.bat not found. Patch will not include helper script.
)

echo [5/5] Cleaning up temporary files...
rd /s /q "%PATCH_WORK%"

echo.
echo ========================================
echo [OK] Patch created successfully!
echo ========================================
echo Location: %PATCH_ROOT%\%PATCH_NAME%.zip
if defined BASELINE_VERSION (
    echo Baseline: %BASELINE_VERSION%
)
if defined PATCH_VERSION (
    echo Target  : %PATCH_VERSION%
)
echo.
echo Files to distribute:
echo   - %PATCH_NAME%.zip
echo   - %PATCH_NAME%.zip.sha256 (checksum)
echo   - apply_incremental_patch.bat (helper script)
echo.
echo [IMPORTANT] Users must have baseline version %BASELINE_VERSION% installed.
echo.
exit /b 0

:END
endlocal
