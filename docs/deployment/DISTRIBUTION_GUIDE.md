# 股权结构图工具 - 分发指南

## 分发准备

### 1. 打包应用程序

使用统一打包脚本创建完整的应用程序包：

```bash
# 完整构建模式
build_incremental_with_static_fix.bat

# 或者仅创建补丁（如果已有基础版本）
build_incremental_with_static_fix.bat PATCH_ONLY
```

### 2. 分发文件结构

打包完成后，您只需要分发以下内容：

```
equity_mermaid_tool_incremental/    # 主应用程序目录（完整内容）
├── equity_mermaid_tool_incremental.exe    # 主可执行文件
├── start_equity_mermaid_portable.bat     # 分发版启动脚本（需放入此目录）
├── static/                               # 静态文件目录
├── .streamlit/                           # Streamlit配置目录
└── [其他依赖文件和目录]                   # PyInstaller生成的所有依赖
```

**重要提示：**
- `start_equity_mermaid_portable.bat` 启动脚本必须放在 `equity_mermaid_tool_incremental` 目录内
- 不要将启动脚本放在目录外，否则无法正确找到可执行文件
- 启动脚本设计为与可执行文件在同一目录下运行

### 3. 分发步骤

1. **创建分发压缩包**
   ```bash
   # 仅压缩应用程序目录
   cd dist
   tar -czf equity_mermaid_tool_v[版本号]_[日期].zip equity_mermaid_tool_incremental/
   ```

2. **添加启动脚本到压缩包**
   ```bash
   # 将启动脚本复制到应用程序目录内
   copy start_equity_mermaid_portable.bat dist/equity_mermaid_tool_incremental/
   
   # 重新创建包含启动脚本的压缩包
   cd dist
   tar -czf equity_mermaid_tool_v[版本号]_[日期].zip equity_mermaid_tool_incremental/
   ```

3. **包含必要文档**
   - 将本分发指南的简化版包含在压缩包中
   - 可选：包含用户手册或快速入门指南

4. **版本控制**
   - 在压缩包名称中包含版本号和日期
   - 保留内部版本控制记录

## 用户使用说明

### 系统要求

- Windows 10/11 (64位)
- 至少4GB可用内存
- 至少500MB可用磁盘空间

### 安装与启动

1. **解压文件**
   - 将压缩包解压到任意目录
   - 确保目录路径不包含特殊字符

2. **启动应用程序**
   - 进入 `equity_mermaid_tool_incremental` 目录
   - 双击运行 `start_equity_mermaid_portable.bat`
   - 等待应用程序自动启动（默认会在浏览器中打开）

3. **可选启动参数**
   - 如需跳过静态文件修复，可以：
     - 在命令行中运行：`start_equity_mermaid_portable.bat --skip-fix`
     - 或创建快捷方式，在目标中添加参数

4. **访问应用程序**
   - 主界面: http://127.0.0.1:8504
   - 图像识别模式: http://127.0.0.1:8501
   - 手动编辑模式: http://127.0.0.1:8503

### 常见问题解决

1. **应用程序无法启动**
   - 尝试以管理员身份运行启动脚本
   - 检查防病毒软件是否阻止程序运行
   - 使用 `--skip-fix` 参数跳过静态文件修复

2. **端口冲突**
   - 关闭占用端口的程序
   - 修改 `.streamlit/config.toml` 中的端口设置

3. **静态文件问题**
   - 删除 `static` 目录，重新启动应用程序
   - 启动脚本会自动创建必要的静态文件

## 分发注意事项

### 安全性

1. **代码签名**
   - 建议对可执行文件进行数字签名
   - 减少安全软件的误报

2. **防病毒软件兼容性**
   - 在主流防病毒软件上测试
   - 准备误报白名单指南

### 兼容性

1. **Windows版本**
   - 测试不同Windows版本的兼容性
   - 特别注意Windows 7的支持（如果需要）

2. **权限要求**
   - 文档化所需的系统权限
   - 提供受限环境下的安装指南

### 更新与维护

1. **增量更新**
   - 使用补丁机制进行小版本更新
   - 提供更新脚本和说明

2. **版本回退**
   - 保留旧版本的下载链接
   - 提供版本回退指南

## 技术支持

### 日志收集

启动脚本会自动创建以下日志文件：
- 应用程序日志：位于用户数据目录
- 启动脚本日志：控制台输出

### 问题报告

用户应提供以下信息：
- Windows版本
- 错误消息
- 复现步骤
- 日志文件（如果可用）

## 开发者备注

### 自定义分发

如果需要自定义分发配置：

1. **修改启动脚本**
   - 编辑 `start_equity_mermaid_portable.bat`
   - 调整端口、默认设置等

2. **添加自定义文件**
   - 在打包前添加到 `dist/equity_mermaid_tool_incremental/` 目录
   - 更新启动脚本以处理这些文件

3. **集成安装程序**
   - 使用NSIS或Inno Setup创建安装程序
   - 集成启动脚本的功能

### 自动化分发

可以创建自动化脚本：
1. 调用打包脚本
2. 创建压缩包
3. 生成版本说明
4. 上传到分发平台