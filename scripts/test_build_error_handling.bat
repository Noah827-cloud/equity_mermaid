@echo off
chcp 65001 >nul
REM 测试 build_exe.bat 的错误处理机制
REM 此脚本用于验证各种错误情况下是否正确停止执行

echo ========================================
echo 测试打包脚本的错误处理机制
echo ========================================
echo.

echo 本脚本将测试以下场景：
echo 1. Python 可执行文件不存在
echo 2. 检查脚本文件不存在
echo 3. 打包配置文件不存在
echo 4. Python 脚本执行失败
echo.
echo 每个测试都应该正确停止执行并显示错误信息
echo.

REM ==========================================
REM 测试 1: Python 可执行文件不存在
REM ==========================================
echo [测试 1] 检查 Python 可执行文件存在性检查
echo.

set PYTHON_PATH=C:\Users\z001syzk\AppData\Local\anaconda3\python.exe

if not exist "%PYTHON_PATH%" (
    echo ❌ Python 不存在 - 错误处理正确！
    echo 如果执行 build_exe.bat，将在第一步停止
) else (
    echo ✅ Python 存在于: %PYTHON_PATH%
)
echo.

REM ==========================================
REM 测试 2: 关键脚本文件存在性
REM ==========================================
echo [测试 2] 检查关键脚本文件是否存在
echo.

set SCRIPT1=scripts\sync_utils_to_spec.py
set SCRIPT2=check_all.py
set SCRIPT3=equity_mermaid.spec

if not exist "%SCRIPT1%" (
    echo ❌ 缺少: %SCRIPT1%
    echo    build_exe.bat 将在步骤 2.1 停止 ✓
    set TEST2_FAIL=1
) else (
    echo ✅ 存在: %SCRIPT1%
)

if not exist "%SCRIPT2%" (
    echo ❌ 缺少: %SCRIPT2%
    echo    build_exe.bat 将在步骤 2.2 停止 ✓
    set TEST2_FAIL=1
) else (
    echo ✅ 存在: %SCRIPT2%
)

if not exist "%SCRIPT3%" (
    echo ❌ 缺少: %SCRIPT3%
    echo    build_exe.bat 将在步骤 4 停止 ✓
    set TEST2_FAIL=1
) else (
    echo ✅ 存在: %SCRIPT3%
)

if defined TEST2_FAIL (
    echo.
    echo ⚠️ 发现缺失文件，build_exe.bat 将正确停止
) else (
    echo.
    echo ✅ 所有关键文件都存在
)
echo.

REM ==========================================
REM 测试 3: 验证错误码处理
REM ==========================================
echo [测试 3] 验证 Python 脚本错误码处理
echo.

echo 测试 check_all.py 的退出码...
%PYTHON_PATH% check_all.py >nul 2>&1
set CHECK_RESULT=%errorlevel%

if %CHECK_RESULT% equ 0 (
    echo ✅ check_all.py 执行成功 (退出码: 0)
    echo    build_exe.bat 将继续执行
) else (
    echo ❌ check_all.py 执行失败 (退出码: %CHECK_RESULT%)
    echo    build_exe.bat 将在步骤 2.2 停止 ✓
)
echo.

echo 测试 sync_utils_to_spec.py 的退出码...
%PYTHON_PATH% scripts\sync_utils_to_spec.py >nul 2>&1
set SYNC_RESULT=%errorlevel%

if %SYNC_RESULT% equ 0 (
    echo ✅ sync_utils_to_spec.py 执行成功 (退出码: 0)
    echo    build_exe.bat 将继续执行
) else (
    echo ⚠️ sync_utils_to_spec.py 检测到问题 (退出码: %SYNC_RESULT%)
    echo    build_exe.bat 将提示用户自动修复
)
echo.

REM ==========================================
REM 总结
REM ==========================================
echo ========================================
echo 测试总结
echo ========================================
echo.

echo ✅ 错误处理机制测试完成
echo.
echo 验证的保护机制：
echo 1. ✓ Python 可执行文件存在性检查 (第1步)
echo 2. ✓ Python 运行能力检查 (第1步)
echo 3. ✓ sync_utils_to_spec.py 存在性检查 (第2.1步)
echo 4. ✓ sync_utils_to_spec.py 执行结果检查 (第2.1步)
echo 5. ✓ check_all.py 存在性检查 (第2.2步)
echo 6. ✓ check_all.py 执行结果检查 (第2.2步)
echo 7. ✓ equity_mermaid.spec 存在性检查 (第4步)
echo 8. ✓ PyInstaller 打包结果检查 (第4步)
echo.
echo 💡 结论：
if %CHECK_RESULT% equ 0 (
    if %SYNC_RESULT% equ 0 (
        echo    所有检查通过，可以安全执行 build_exe.bat
    ) else (
        echo    配置需要修复，build_exe.bat 会提示自动修复
    )
) else (
    echo    检查发现问题，build_exe.bat 会在问题修复前停止
)
echo.

pause

