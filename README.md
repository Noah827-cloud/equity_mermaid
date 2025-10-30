# Equity Mermaid 股权结构可视化工具

## 项目简介

Equity Mermaid 是一个专业的股权结构可视化工具，支持通过图片识别、手动编辑和AI分析三种方式生成股权关系Mermaid图表，帮助用户直观地展示和分析复杂的股权结构关系。

## 快速开始

### 1. 安装依赖
首先安装项目所需的Python依赖包：
```bash
pip install -r requirements.txt
```

### 2. 启动主程序

**使用Windows专用启动脚本:**
```batch
scripts\start_all.bat
```

运行后将显示交互式菜单，可选择以下选项：
- 1: 主界面 (端口: 8504) - 提供功能概览和导航入口
- 2: 图像识别模式 (端口: 8501) - 基于图像的股权结构识别功能
- 3: 手动编辑模式 (端口: 8503) - 通过表单手动编辑股权关系
- 4: 退出 - 关闭启动器

**其他启动脚本**：所有独立启动脚本已整理到 `scripts/launchers` 目录下，包括便携版、带修复功能版等多种启动选项。详细信息请参考 `scripts/launchers/launchers_summary.md` 文档。

### 3. 直接启动特定功能
您也可以直接启动各个功能模块：

- 主界面 (综合导航):
  ```bash
  python -m streamlit run main_page.py
  ```
  访问地址: http://localhost:8504

- 图像识别模式:
  ```bash
  python -m streamlit run src/main/enhanced_equity_to_mermaid.py
  ```
  访问地址: http://localhost:8501

- 手动编辑模式:
  ```bash
  python -m streamlit run src/main/manual_equity_editor.py
  ```
  访问地址: http://localhost:8503

## 文档目录

详细文档已整理到 [docs 目录](docs/) 下，包括：

- **用户指南**：详细的使用说明和操作流程
- **部署指南**：项目部署和配置文档
- **开发文档**：开发环境设置和编码规范
- **更新日志**：各版本功能更新和修复记录
- **问题修复**：常见问题的解决方案

请访问 [docs/README.md](docs/README.md) 查看完整的文档结构和索引。

## 主要功能

- **图像识别模式**：上传股权结构图，自动识别公司、股东和子公司关系
- **手动编辑模式**：通过直观表单界面，手动创建和编辑复杂股权结构
- **AI分析功能**：从文本描述或文件中提取和分析股权结构信息
- **双重图表显示**：支持传统Mermaid图表和交互式HTML图表展示
- **数据导入导出**：支持JSON格式的数据导入和导出功能

## 检查依赖

安装依赖后，**强烈建议**运行依赖检查脚本：
```bash
python check_dependencies.py
```

## 最后更新

更新时间：2025-10-29