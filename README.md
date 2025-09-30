# 股权结构可视化工具

## 项目简介

本项目提供一个用于手动创建和编辑股权结构图的Streamlit应用。用户可以通过直观的界面添加公司、股东、子公司及它们之间的关系，并自动生成交互式Mermaid图表。

## 功能特点

- 手动添加和编辑核心公司、顶层实体/股东和子公司
- 设置实体之间的股权关系和控制关系
- 生成交互式Mermaid股权结构图
- 支持数据导出和导入
- 友好的用户界面和操作流程

## 部署到Streamlit Community Cloud

### 准备工作

1. 确保你的代码已提交到GitHub仓库
2. 确保项目中包含以下文件：
   - `manual_equity_editor.py` - 主应用文件
   - `mermaid_function.py` - 图表生成功能
   - `requirements.txt` - 依赖列表
   - `.gitignore` - Git忽略文件配置（确保敏感信息不被提交）

### 部署步骤

1. 访问 [Streamlit Community Cloud](https://share.streamlit.io/)
2. 使用GitHub账号登录
3. 点击 "New app" 按钮
4. 填写以下信息：
   - Repository: 你的GitHub仓库路径（例如：`用户名/equity_mermaid`）
   - Branch: 选择主分支（通常是 `main` 或 `master`）
   - Main file path: 输入 `manual_equity_editor.py`
5. 点击 "Deploy!" 按钮

### 环境配置

如果应用需要特殊的环境变量（如API密钥），可以在Streamlit Cloud中设置：

1. 在应用页面，点击右上角的 "⋮" 图标
2. 选择 "Settings"
3. 在 "Secrets" 标签页中添加你的环境变量

### 注意事项

- 确保移除所有硬编码的API密钥和敏感信息
- 确保requirements.txt中只包含必要的生产依赖
- 对于配置文件，确保使用环境变量或Streamlit Secrets进行管理
- 避免使用本地文件路径依赖，确保代码可以在任何环境中运行

## 本地开发

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
streamlit run manual_equity_editor.py
```

## 许可证

[MIT License](LICENSE)