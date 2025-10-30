# Equity Mermaid Tool - 静态文件修复指南

## 问题描述

在使用PyInstaller打包Streamlit应用程序时，可能会遇到以下错误：
```
FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\...\\AppData\\Local\\Temp\\_MEI438282\\streamlit\\static\\index.html'
```

这是因为Streamlit的静态文件在PyInstaller打包后的临时目录中未找到。

## 解决方案

我们提供了以下脚本来解决这个问题：

### 1. 构建脚本
- `build_with_static_fix.bat` - 清理旧构建并重新构建应用程序

### 2. 启动脚本
- `start_simple.bat` - 简单启动应用程序，不包含静态文件修复
- `start_with_fix.bat` - 启动应用程序并修复静态文件问题

### 3. 修复脚本
- `scripts/fix_static_files.bat` - 修复Streamlit静态文件问题

## 使用方法

### 首次构建
1. 运行 `build_with_static_fix.bat` 重新构建应用程序
2. 运行 `start_with_fix.bat` 启动应用程序

### 日常使用
1. 运行 `start_with_fix.bat` 启动应用程序

## 技术细节

修复脚本会：
1. 检查应用程序目录是否存在
2. 创建 `streamlit/static` 目录（如果不存在）
3. 创建一个基本的 `index.html` 文件（如果不存在）

## 故障排除

如果仍然遇到静态文件问题：
1. 确保应用程序已正确构建
2. 检查 `dist/equity_mermaid_tool_incremental/streamlit/static/index.html` 是否存在
3. 尝试手动运行 `scripts/fix_static_files.bat`

## 更新日期
2025-06-17