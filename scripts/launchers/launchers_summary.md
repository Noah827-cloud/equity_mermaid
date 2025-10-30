# 启动脚本功能总结

## 概述
本文档详细说明 Equity Mermaid 工具中各个启动脚本的功能、区别和适用场景。

## 启动脚本列表

### 1. start_equity_mermaid_portable.bat
- **功能**：便携版启动脚本
- **特点**：
  - 设置应用目录为脚本所在目录
  - 支持 `--skip-fix` 命令行参数跳过修复步骤
  - 内置简化的静态文件修复逻辑
  - 无需额外依赖即可运行
- **适用场景**：
  - 独立分发的便携版本
  - 需要在不同环境中快速部署
  - 用户不需要复杂修复功能的场景

### 2. start_equity_mermaid_with_fix.bat
- **功能**：带静态文件修复的启动脚本
- **特点**：
  - 设置应用目录为 `dist/equity_mermaid_tool_incremental`
  - 调用外部 `scripts/apply_incremental_patch_with_static_fix.bat` 进行修复
  - 使用 PowerShell 执行修复脚本
  - 检查可执行文件后启动应用
  - 不支持命令行参数
- **适用场景**：
  - 开发环境中使用
  - 需要增量更新和静态文件修复的场景

### 3. start_equity_mermaid.bat
- **功能**：统一启动器
- **特点**：
  - 增强的静态文件修复功能
  - 更完善的错误处理和日志记录
  - 支持多种运行模式
- **适用场景**：
  - 生产环境中的标准启动方式
  - 需要完整修复功能的场景

### 4. start_simple.bat
- **功能**：最简单的启动脚本
- **特点**：
  - 不包含任何修复功能
  - 直接启动应用程序
  - 结构简单，易于理解
- **适用场景**：
  - 开发调试
  - 环境已经正确配置的情况
  - 性能测试场景

### 5. start_with_fix.bat
- **功能**：基础修复启动脚本
- **特点**：
  - 包含基本的静态文件修复功能
  - 平衡了功能和复杂性
- **适用场景**：
  - 日常开发和测试
  - 需要基本修复但不需要复杂功能的场景

## 功能复杂度对比
从功能复杂度和完整性排序（从高到低）：
1. start_equity_mermaid.bat (统一启动器)
2. start_equity_mermaid_with_fix.bat (带修复的启动器)
3. start_with_fix.bat (基础修复启动器)
4. start_equity_mermaid_portable.bat (便携版启动器)
5. start_simple.bat (简单启动器)

## 修复机制差异
- **增量修复**：通过调用外部脚本实现，适用于复杂环境
- **内置修复**：直接在脚本中包含修复逻辑，适用于便携版本
- **简化修复**：只包含必要的修复步骤，适用于开发环境

## 使用建议
- **开发环境**：优先使用 `start_simple.bat` 或 `start_with_fix.bat`
- **测试环境**：使用 `start_equity_mermaid_with_fix.bat` 进行完整测试
- **生产部署**：使用 `start_equity_mermaid.bat` 确保稳定性
- **便携分发**：使用 `start_equity_mermaid_portable.bat` 方便用户使用

## 注意事项
- 使用前请确保脚本具有执行权限
- 根据实际环境选择合适的启动脚本
- 如需自定义修复行为，请参考相关脚本的具体实现

最后更新时间：2025-10-29