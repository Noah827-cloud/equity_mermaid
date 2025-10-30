@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PATCH_FILE=%~1"
set "TARGET_ROOT=%~2"

if not defined PATCH_FILE (
    for %%F in ("%SCRIPT_DIR%equity_mermaid_patch_*.zip") do (
        set "PATCH_FILE=%%~fF"
        goto PATCH_FOUND
    )
)
goto PATCH_FOUND

:PATCH_FOUND
if not defined TARGET_ROOT (
    set "TARGET_ROOT=%SCRIPT_DIR%"
)

for %%I in ("%TARGET_ROOT%") do set "TARGET_ROOT=%%~fI"
set "APP_DIR=%TARGET_ROOT%app"
set "TEMP_DIR=%TARGET_ROOT%_patch_tmp"

if not defined PATCH_FILE (
    echo [ERROR] Patch archive not specified. Provide the zip path as the first argument.
    echo         Example: apply_incremental_patch.bat equity_mermaid_patch_20250101_120000.zip
    exit /b 1
)

if not exist "%PATCH_FILE%" (
    echo [ERROR] Cannot find patch archive:
    echo         %PATCH_FILE%
    exit /b 1
)

if not exist "%APP_DIR%" (
    echo [ERROR] Target app folder not found:
    echo         %APP_DIR%
    echo Ensure this script lives next to the installed app (the folder containing app\ and runtime\).
    echo You can also pass the install directory as the second argument.
    exit /b 1
)

if exist "%TEMP_DIR%" (
    rd /s /q "%TEMP_DIR%"
)
mkdir "%TEMP_DIR%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to create temporary directory:
    echo         %TEMP_DIR%
    exit /b 1
)

echo ========================================
echo [Incremental Update] Applying patch
echo ========================================
echo Patch file : %PATCH_FILE%
echo Target root: %TARGET_ROOT%
echo.

REM P1: SHA256 校验
set "SHA256_FILE=%PATCH_FILE%.sha256"
if exist "%SHA256_FILE%" (
    echo [1/7] Verifying patch integrity (SHA256)...
    for /f "usebackq tokens=*" %%H in ("%SHA256_FILE%") do set "EXPECTED_HASH=%%H"
    
    for /f "skip=1 tokens=*" %%H in ('certutil -hashfile "%PATCH_FILE%" SHA256') do (
        if not defined ACTUAL_HASH set "ACTUAL_HASH=%%H"
    )
    
    REM 移除空格
    set "ACTUAL_HASH=%ACTUAL_HASH: =%"
    set "EXPECTED_HASH=%EXPECTED_HASH: =%"
    
    if /I "%ACTUAL_HASH%"=="%EXPECTED_HASH%" (
        echo [OK] SHA256 checksum verified.
    ) else (
        echo [ERROR] SHA256 mismatch! Patch file may be corrupted.
        echo Expected: %EXPECTED_HASH%
        echo Actual  : %ACTUAL_HASH%
        exit /b 1
    )
) else (
    echo [1/7] Verifying patch integrity...
    echo [WARN] SHA256 checksum file not found, skipping integrity check.
)

echo [2/7] Unpacking archive...
powershell -NoProfile -Command "Expand-Archive -LiteralPath '%PATCH_FILE%' -DestinationPath '%TEMP_DIR%' -Force" >nul
if errorlevel 1 (
    echo [ERROR] Failed to extract patch archive.
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)

if not exist "%TEMP_DIR%\app" (
    echo [ERROR] Patch archive is missing the expected app\ payload.
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)

REM P0: 版本匹配验证
echo [3/7] Verifying version compatibility...
set "CURRENT_VERSION="
set "REQUIRED_BASELINE="

if exist "%APP_DIR%\version.txt" (
    set /p CURRENT_VERSION=<"%APP_DIR%\version.txt"
)

if exist "%TEMP_DIR%\required_baseline.txt" (
    set /p REQUIRED_BASELINE=<"%TEMP_DIR%\required_baseline.txt"
    
    if defined REQUIRED_BASELINE (
        if "%REQUIRED_BASELINE%"=="UNKNOWN" (
            echo [WARN] Patch baseline version is UNKNOWN, skipping version check.
        ) else if defined CURRENT_VERSION (
            if "%CURRENT_VERSION%"=="%REQUIRED_BASELINE%" (
                echo [OK] Version match: %CURRENT_VERSION%
            ) else (
                echo [ERROR] Version mismatch!
                echo   Current installed : %CURRENT_VERSION%
                echo   Required baseline : %REQUIRED_BASELINE%
                echo.
                echo This patch cannot be applied to your current version.
                echo Please install the correct baseline version first.
                rd /s /q "%TEMP_DIR%"
                exit /b 1
            )
        ) else (
            echo [WARN] Current version.txt not found, cannot verify compatibility.
            echo Required baseline: %REQUIRED_BASELINE%
            choice /C YN /M "Continue anyway (not recommended)?"
            if errorlevel 2 (
                rd /s /q "%TEMP_DIR%"
                exit /b 1
            )
        )
    )
) else (
    echo [WARN] Patch does not include required_baseline.txt, skipping version check.
)

REM P1: 创建备份
echo [4/7] Creating backup...
for /f "usebackq tokens=*" %%I in (`powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"`) do set "BACKUP_STAMP=%%I"
set "BACKUP_DIR=%TARGET_ROOT%app_backup_%BACKUP_STAMP%"

robocopy "%APP_DIR%" "%BACKUP_DIR%" /E /NFL /NDL /NJH /NJS /NC /NS >nul
if errorlevel 8 (
    echo [ERROR] Failed to create backup.
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)
echo [OK] Backup created at: %BACKUP_DIR%

echo [5/7] Applying patch...
robocopy "%TEMP_DIR%\app" "%APP_DIR%" /E /NFL /NDL /NJH /NJS /NP /NC /NS >nul
if errorlevel 8 (
    echo [ERROR] robocopy reported a failure while applying the patch.
    echo.
    echo [ROLLBACK] Attempting to restore from backup...
    robocopy "%BACKUP_DIR%" "%APP_DIR%" /E /MIR /NFL /NDL /NJH /NJS /NP /NC /NS >nul
    if errorlevel 8 (
        echo [ERROR] Rollback failed! Manual recovery required.
        echo Backup location: %BACKUP_DIR%
    ) else (
        echo [OK] Rollback completed successfully.
    )
    rd /s /q "%TEMP_DIR%"
    exit /b 1
)
echo [OK] Patch applied successfully.

echo [6/7] Verifying installation...
set "NEW_VERSION="
if exist "%APP_DIR%\version.txt" (
    set /p NEW_VERSION=<"%APP_DIR%\version.txt"
    if defined NEW_VERSION (
        echo [OK] New version: %NEW_VERSION%
    )
)

echo [7/7] Cleaning up...
rd /s /q "%TEMP_DIR%"

echo.
echo ========================================
echo [SUCCESS] Patch applied successfully!
echo ========================================
if defined CURRENT_VERSION (
    echo Previous version: %CURRENT_VERSION%
)
if defined NEW_VERSION (
    echo Current version : %NEW_VERSION%
)
echo Backup location : %BACKUP_DIR%
echo.
echo [IMPORTANT] Restart the application to load the new code.
echo.
echo To rollback if needed, run:
echo   robocopy "%BACKUP_DIR%" "%APP_DIR%" /E /MIR
echo.
exit /b 0
