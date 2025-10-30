# Streamlit静态文件路径修复说明

## 问题描述

增量打包后运行时出现以下错误：
```
FileNotFoundError: [Errno 2] No such file or directory: 'C:\Users\z001syzk\AppData\Local\Temp\_MEI415882\streamlit\static\index.html'
```

## 问题原因

在增量打包中，Streamlit的静态文件被放置在`app/streamlit/static`目录下，但Streamlit在运行时尝试从`streamlit/static`目录查找这些文件，导致路径不匹配。

## 修复方案

### 1. 修改PyInstaller配置文件

在`equity_mermaid_incremental.spec`文件中，我们修改了Streamlit静态文件的收集路径：

```python
# 修复前
(streamlit_static_path, 'streamlit/static'),

# 修复后
(streamlit_static_path, 'app/streamlit/static'),
(anaconda_lib_bin + '\\..\\..\\Lib\\site-packages\\streamlit\\static', 'app/streamlit/static'),
```

### 2. 创建运行时钩子

创建了`scripts/streamlit_static_fix_hook.py`文件，在运行时设置环境变量并创建符号链接：

```python
def _fix_streamlit_static_path() -> None:
    """Fix Streamlit static file path for incremental bundle."""
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    
    # Check if we're in an incremental bundle
    app_streamlit_static = base_dir / "app" / "streamlit" / "static"
    if app_streamlit_static.exists():
        # Set environment variable to tell Streamlit where to find static files
        os.environ["STREAMLIT_STATIC_ROOT"] = str(app_streamlit_static)
        
        # Also check for the original static path and create a symlink if needed
        original_static = base_dir / "streamlit" / "static"
        if not original_static.exists():
            try:
                # Try to create a junction/symlink to the correct location
                if hasattr(os, "symlink"):
                    os.symlink(str(app_streamlit_static), str(original_static))
                elif sys.platform == "win32":
                    import subprocess
                    subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(original_static), str(app_streamlit_static)],
                        check=False,
                        capture_output=True
                    )
            except Exception:
                # If symlink creation fails, we'll rely on the environment variable
                pass
```

### 3. 添加运行时钩子到PyInstaller配置

在`equity_mermaid_incremental.spec`文件中添加了新的运行时钩子：

```python
runtime_hooks=['scripts/runtime_env_hook.py', 'scripts/streamlit_static_fix_hook.py'],
```

### 4. 创建构建后验证脚本

创建了`scripts/verify_streamlit_static.py`脚本，在构建后验证Streamlit静态文件是否正确放置，并在需要时创建符号链接。

### 5. 修改构建流程

在`build_exe_incremental.bat`中添加了Streamlit静态文件验证步骤：

```batch
echo [Phase 5] 验证Streamlit静态文件路径
python scripts\verify_streamlit_static.py "%DIST_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Streamlit静态文件验证失败
    goto :error
)
```

## 使用方法

1. 确保所有修复文件已正确创建：
   - `scripts/streamlit_static_fix_hook.py`
   - `scripts/verify_streamlit_static.py`

2. 重新运行增量构建：
   ```batch
   build_exe_incremental.bat
   ```

3. 构建完成后，验证脚本会自动检查并修复Streamlit静态文件路径问题。

## 手动修复方法

如果自动修复不工作，可以手动创建符号链接：

1. 打开命令提示符（以管理员身份）
2. 导航到增量打包目录：
   ```cmd
   cd c:\Users\z001syzk\Downloads\equity_mermaid\dist\equity_mermaid_tool_incremental
   ```
3. 创建符号链接：
   ```cmd
   mklink /J streamlit\static app\streamlit\static
   ```

## 验证修复

修复后，可以通过以下方式验证：

1. 检查`dist\equity_mermaid_tool_incremental\streamlit\static`目录是否存在
2. 检查该目录是否包含`index.html`文件
3. 运行应用程序，确认不再出现静态文件路径错误

## 注意事项

1. 符号链接创建需要管理员权限
2. 如果无法创建符号链接，应用程序将依赖环境变量`STREAMLIT_STATIC_ROOT`来定位静态文件
3. 此修复仅适用于增量打包，完整打包不受此问题影响