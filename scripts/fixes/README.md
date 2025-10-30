# 静态文件修复脚本目录

本文档说明了项目中用于修复Streamlit静态文件问题的各种脚本及其功能。

## 目录结构

此目录包含以下静态文件修复脚本：

- `fix_streamlit_static_compatible.bat` - 与增量更新系统兼容的静态文件修复脚本
- `fix_streamlit_static_no_admin.bat` - 无需管理员权限的静态文件修复脚本
- `fix_streamlit_static_ps.bat` - 使用PowerShell实现的静态文件修复脚本
- `fix_streamlit_static.bat` - 创建junction link的静态文件修复脚本（需要管理员权限）

**注意**：基础修复脚本 `fix_static_files.bat` 保留在父目录（scripts/）中，因为它被多个其他脚本调用。

## 脚本功能说明

### 1. fix_streamlit_static_compatible.bat
- 设计用于与增量更新系统兼容
- 在应用增量更新后需要重新运行
- 提供中文界面提示

### 2. fix_streamlit_static_no_admin.bat
- 无需管理员权限运行
- 使用xcopy命令复制静态文件
- 适合普通用户使用

### 3. fix_streamlit_static_ps.bat
- 使用PowerShell的Copy-Item命令
- 提供更好的错误处理和彩色输出
- 适合需要详细错误信息的场景

### 4. fix_streamlit_static.bat
- 需要管理员权限创建junction link
- 通过创建符号链接而非复制文件来解决路径问题
- 效率更高但需要更高权限

### 5. fix_static_files.bat (位于scripts/目录)
- 基础的静态文件修复脚本
- 简单地创建streamlit/static目录并生成基础index.html
- 被多个构建和启动脚本调用

## 使用场景

1. **普通用户**：使用 `fix_streamlit_static_no_admin.bat` 或 `fix_streamlit_static_ps.bat`
2. **管理员权限用户**：使用 `fix_streamlit_static.bat` 获取最佳性能
3. **增量更新后**：使用 `fix_streamlit_static_compatible.bat`
4. **开发者**：根据自动化流程需求选择合适的脚本

## 更新历史

- 2025-10-29: 目录创建，脚本整理完成