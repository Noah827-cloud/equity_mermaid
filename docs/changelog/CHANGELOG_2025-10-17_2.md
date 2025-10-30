## 2025-10-17

- 修复: 实时预览在第二次生成时出现 [Errno 22] Invalid argument
  - 原因分析:
    - Windows 下自动保存工作区名包含非法字符（如 `: / \ ? * < > |` 或以空格/点结尾）导致写入 `user_data/autosave/<workspace>.autosave.json` 抛出 OSError。
    - Mermaid 预览阶段的大量调试打印在某些环境下写入 stdout 也可能触发 OSError（[Errno 22]）。
  - 解决方案:
    - 清洗工作区名后再进行 autosave，替换非法字符为 `_`，并去除尾部空格与点。
    - 加固 `_safe_print`，除编码异常外同时捕获并忽略 OSError 及其他打印异常，保证主流程不中断。
    - 预览组件使用基于代码内容的动态 key，避免组件复用缓存导致的异常。
    - 预览异常时增加 traceback 折叠框，便于进一步定位问题。
  - 影响范围:
    - 实时预览稳定性显著提升；不依赖外部 Mermaid 服务。
    - 自动保存文件名更安全，避免 Windows 平台写入失败。

- 技术细节:
  - 文件 `src/main/manual_equity_editor.py`
    - 预览区域: 为 `st_mermaid` 使用动态 key；新增“查看Mermaid代码（预览）”与“查看错误详情（traceback）”折叠框；在 autosave 前清洗工作区名。
  - 文件 `src/utils/mermaid_function.py`
    - `_safe_print`: 捕获并忽略 OSError 以及其他打印异常，避免大文本调试信息导致的 I/O 中断。

- 验证步骤:
  1. 打开“关系设置”页，勾选“显示股权结构预览”。
  2. 连续多次更新关系/数据，预览应稳定渲染，不再出现 [Errno 22]。
  3. 如有异常，展开“查看错误详情（traceback）”获取堆栈以继续排查。


