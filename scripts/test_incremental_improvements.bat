@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo 增量更新改进测试脚本
echo ========================================
echo.

set "PYTHON=C:\Users\z001syzk\AppData\Local\anaconda3\python.exe"
set "TEST_DIST=dist\equity_mermaid_tool_incremental"
set "TEST_APP=%TEST_DIST%\app"
set "TEST_PATCH_DIR=dist\patches"

REM 检查是否已构建
if not exist "%TEST_DIST%" (
    echo [ERROR] 请先运行 build_exe_incremental.bat 构建应用
    exit /b 1
)

echo ========================================
echo 测试 1: P0 - 基线版本匹配验证
echo ========================================
echo.

REM 保存原始版本
if exist "%TEST_APP%\version.txt" (
    copy "%TEST_APP%\version.txt" "%TEST_APP%\version.txt.bak" >nul
    echo [1.1] 原始版本文件已备份
) else (
    echo v1.0.0 > "%TEST_APP%\version.txt"
    echo [1.1] 创建测试版本文件: v1.0.0
)

REM 创建测试补丁
echo [1.2] 创建测试补丁（基线: 当前版本）...
call build_exe_incremental.bat patch TEST_v1.1.0 >nul 2>&1
if errorlevel 1 (
    echo [FAIL] 补丁创建失败
    goto RESTORE_VERSION
)
echo [OK] 补丁创建成功

REM 查找最新补丁
for /f "delims=" %%D in ('dir /b /ad /o-d "%TEST_PATCH_DIR%\equity_mermaid_patch_*" 2^>nul') do (
    set "LATEST_PATCH=%%D"
    goto FOUND_PATCH
)
:FOUND_PATCH

if not defined LATEST_PATCH (
    echo [FAIL] 未找到测试补丁
    goto RESTORE_VERSION
)

set "PATCH_FILE=%TEST_PATCH_DIR%\%LATEST_PATCH%\%LATEST_PATCH%.zip"
if not exist "%PATCH_FILE%" (
    echo [FAIL] 补丁文件不存在: %PATCH_FILE%
    goto RESTORE_VERSION
)

REM 检查 required_baseline.txt 是否在补丁中
powershell -NoProfile -Command "Expand-Archive -LiteralPath '%PATCH_FILE%' -DestinationPath '%TEST_PATCH_DIR%\temp_extract' -Force" >nul 2>&1
if exist "%TEST_PATCH_DIR%\temp_extract\required_baseline.txt" (
    echo [OK] required_baseline.txt 存在于补丁包中
    type "%TEST_PATCH_DIR%\temp_extract\required_baseline.txt"
) else (
    echo [FAIL] required_baseline.txt 不存在于补丁包中
)
rd /s /q "%TEST_PATCH_DIR%\temp_extract" 2>nul

echo.
echo ========================================
echo 测试 2: P0 - 运行时守卫（无 mtime）
echo ========================================
echo.

REM 运行运行时守卫
if exist "scripts\runtime_bootloader_guard.py" (
    echo [2.1] 运行运行时守卫检查...
    "%PYTHON%" "scripts\runtime_bootloader_guard.py" ^
        --dist "%TEST_DIST%" ^
        --exe "equity_mermaid_tool_incremental.exe" ^
        --runtime-dir "runtime" ^
        --snapshot "%TEST_DIST%\.runtime_snapshot.json" ^
        --flag "%TEST_DIST%\.runtime_changed.flag"
    
    if errorlevel 1 (
        echo [WARN] 运行时守卫执行失败
    ) else (
        echo [OK] 运行时守卫执行成功
    )
    
    REM 检查快照文件格式
    if exist "%TEST_DIST%\.runtime_snapshot.json" (
        echo [2.2] 检查快照文件格式...
        findstr /C:"mtime" "%TEST_DIST%\.runtime_snapshot.json" >nul
        if errorlevel 1 (
            echo [OK] 快照文件不包含 mtime 字段（已移除）
        ) else (
            echo [FAIL] 快照文件仍包含 mtime 字段
        )
    )
) else (
    echo [SKIP] scripts\runtime_bootloader_guard.py 不存在
)

echo.
echo ========================================
echo 测试 3: P1 - SHA256 校验文件
echo ========================================
echo.

REM 检查 SHA256 文件是否生成
set "SHA256_FILE=%PATCH_FILE%.sha256"
if exist "%SHA256_FILE%" (
    echo [OK] SHA256 校验文件已生成
    echo [3.1] 校验值:
    type "%SHA256_FILE%"
    echo.
    
    REM 验证 SHA256 格式
    for /f "usebackq tokens=*" %%H in ("%SHA256_FILE%") do (
        set "HASH_VALUE=%%H"
    )
    set "HASH_LEN=0"
    call :strlen HASH_VALUE HASH_LEN
    
    if !HASH_LEN! EQU 64 (
        echo [OK] SHA256 哈希长度正确（64字符）
    ) else (
        echo [FAIL] SHA256 哈希长度错误（期望64，实际!HASH_LEN!）
    )
) else (
    echo [FAIL] SHA256 校验文件未生成
)

echo.
echo ========================================
echo 测试 4: 补丁包完整性
echo ========================================
echo.

REM 解压并检查补丁包内容
set "EXTRACT_DIR=%TEST_PATCH_DIR%\test_extract"
if exist "%EXTRACT_DIR%" rd /s /q "%EXTRACT_DIR%"
mkdir "%EXTRACT_DIR%" >nul 2>&1

powershell -NoProfile -Command "Expand-Archive -LiteralPath '%PATCH_FILE%' -DestinationPath '%EXTRACT_DIR%' -Force" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] 补丁包解压失败
    goto CLEANUP
)

echo [4.1] 检查补丁包结构...
if exist "%EXTRACT_DIR%\app" (
    echo [OK] app\ 目录存在
) else (
    echo [FAIL] app\ 目录不存在
)

if exist "%EXTRACT_DIR%\required_baseline.txt" (
    echo [OK] required_baseline.txt 文件存在
    echo [4.2] 基线版本要求:
    type "%EXTRACT_DIR%\required_baseline.txt"
) else (
    echo [FAIL] required_baseline.txt 文件不存在
)

echo.
echo ========================================
echo 测试 5: apply_incremental_patch.bat 语法检查
echo ========================================
echo.

if exist "scripts\apply_incremental_patch.bat" (
    REM 检查关键功能是否存在
    findstr /C:"SHA256" "scripts\apply_incremental_patch.bat" >nul
    if errorlevel 1 (
        echo [FAIL] apply_incremental_patch.bat 未包含 SHA256 校验
    ) else (
        echo [OK] SHA256 校验代码已添加
    )
    
    findstr /C:"required_baseline" "scripts\apply_incremental_patch.bat" >nul
    if errorlevel 1 (
        echo [FAIL] apply_incremental_patch.bat 未包含版本验证
    ) else (
        echo [OK] 版本验证代码已添加
    )
    
    findstr /C:"BACKUP_DIR" "scripts\apply_incremental_patch.bat" >nul
    if errorlevel 1 (
        echo [FAIL] apply_incremental_patch.bat 未包含备份机制
    ) else (
        echo [OK] 备份机制代码已添加
    )
    
    findstr /C:"ROLLBACK" "scripts\apply_incremental_patch.bat" >nul
    if errorlevel 1 (
        echo [FAIL] apply_incremental_patch.bat 未包含回滚机制
    ) else (
        echo [OK] 回滚机制代码已添加
    )
) else (
    echo [FAIL] scripts\apply_incremental_patch.bat 不存在
)

:CLEANUP
echo.
echo ========================================
echo 清理测试文件...
echo ========================================
if exist "%EXTRACT_DIR%" rd /s /q "%EXTRACT_DIR%"
echo [OK] 清理完成

:RESTORE_VERSION
REM 恢复原始版本文件
if exist "%TEST_APP%\version.txt.bak" (
    move /y "%TEST_APP%\version.txt.bak" "%TEST_APP%\version.txt" >nul
    echo [OK] 原始版本文件已恢复
)

echo.
echo ========================================
echo 测试完成！
echo ========================================
echo.
echo 检查上述输出，确认所有 [OK] 标记。
echo 如有 [FAIL] 标记，请检查相关代码。
echo.
pause
exit /b 0

:strlen
setlocal enabledelayedexpansion
set "str=!%~1!"
set "len=0"
:strlen_loop
if defined str (
    set "str=!str:~1!"
    set /a len+=1
    goto strlen_loop
)
endlocal & set "%~2=%len%"
goto :eof

