@echo off
chcp 65001 >nul
echo ========================================
echo 增量更新改进快速验证
echo ========================================
echo.

REM 检查关键文件是否存在
echo [1/6] 检查关键文件...
if exist "build_exe_incremental.bat" (
    echo [OK] build_exe_incremental.bat 存在
) else (
    echo [FAIL] build_exe_incremental.bat 不存在
)

if exist "scripts\apply_incremental_patch.bat" (
    echo [OK] apply_incremental_patch.bat 存在
) else (
    echo [FAIL] apply_incremental_patch.bat 不存在
)

if exist "scripts\runtime_bootloader_guard.py" (
    echo [OK] runtime_bootloader_guard.py 存在
) else (
    echo [FAIL] runtime_bootloader_guard.py 不存在
)

echo.
echo [2/6] 检查 build_exe_incremental.bat 改进...
findstr /C:"required_baseline" "build_exe_incremental.bat" >nul
if errorlevel 1 (
    echo [FAIL] 未找到版本验证代码
) else (
    echo [OK] 版本验证代码已添加
)

findstr /C:"SHA256" "build_exe_incremental.bat" >nul
if errorlevel 1 (
    echo [FAIL] 未找到SHA256校验代码
) else (
    echo [OK] SHA256校验代码已添加
)

echo.
echo [3/6] 检查 apply_incremental_patch.bat 改进...
findstr /C:"required_baseline" "scripts\apply_incremental_patch.bat" >nul
if errorlevel 1 (
    echo [FAIL] 未找到版本验证代码
) else (
    echo [OK] 版本验证代码已添加
)

findstr /C:"SHA256" "scripts\apply_incremental_patch.bat" >nul
if errorlevel 1 (
    echo [FAIL] 未找到SHA256校验代码
) else (
    echo [OK] SHA256校验代码已添加
)

findstr /C:"BACKUP_DIR" "scripts\apply_incremental_patch.bat" >nul
if errorlevel 1 (
    echo [FAIL] 未找到备份机制
) else (
    echo [OK] 备份机制已添加
)

findstr /C:"ROLLBACK" "scripts\apply_incremental_patch.bat" >nul
if errorlevel 1 (
    echo [FAIL] 未找到回滚机制
) else (
    echo [OK] 回滚机制已添加
)

echo.
echo [4/6] 检查 runtime_bootloader_guard.py 改进...
findstr /C:"mtime" "scripts\runtime_bootloader_guard.py" >nul
if errorlevel 1 (
    echo [OK] mtime依赖已移除
) else (
    echo [FAIL] mtime依赖仍存在
)

echo.
echo [5/6] 检查文档...
if exist "docs\INCREMENTAL_UPDATE_IMPROVEMENTS.md" (
    echo [OK] 改进文档已创建
) else (
    echo [FAIL] 改进文档不存在
)

echo.
echo [6/6] 测试Python脚本语法...
set "PYTHON=C:\Users\z001syzk\AppData\Local\anaconda3\python.exe"
if exist "%PYTHON%" (
    "%PYTHON%" -m py_compile "scripts\runtime_bootloader_guard.py" >nul 2>&1
    if errorlevel 1 (
        echo [FAIL] runtime_bootloader_guard.py 语法错误
    ) else (
        echo [OK] runtime_bootloader_guard.py 语法正确
    )
) else (
    echo [SKIP] Python解释器未找到，跳过语法检查
)

echo.
echo ========================================
echo 快速验证完成！
echo ========================================
echo.
echo 如果看到 [OK] 标记，说明改进已正确实现。
echo 如果看到 [FAIL] 标记，请检查相关文件。
echo.
pause

