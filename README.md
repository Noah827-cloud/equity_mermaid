# 股权结构可视化工具

## 项目简介
本项目提供股权结构可视化工具，支持通过图片识别、手动编辑和AI分析三种方式生成股权关系Mermaid图表。

## 项目结构

```
├── .gitignore            # Git忽略文件
├── .streamlit/           # Streamlit配置目录
│   ├── config.toml       # Streamlit全局配置
│   └── pages/            # Streamlit页面配置
│       ├── 1_图像识别模式.py
│       └── 2_手动编辑模式.py
├── README.md             # 项目说明文档
├── archive/              # 归档文件目录
│   ├── README.md
│   └── examples_backup_20251001/  # 示例备份
├── docs/                 # 文档目录
│   ├── DEPLOYMENT_GUIDE.md    # 部署指南
│   └── README.md              # 详细使用说明
├── examples/             # 示例数据目录
├── generate_equity_data_with_controller.py # 生成含实控人数据的工具脚本
├── import_control_relationship.py        # 导入控制关系的工具脚本
├── legacy/               # 旧版本和历史文件
├── main_page.py          # 推荐主入口页面 (简洁稳定)
├── pages/                # Streamlit应用页面
│   ├── 1_图像识别模式.py
│   └── 2_手动编辑模式.py
├── requirements.txt      # Python依赖列表
├── scripts/              # 脚本文件目录
│   ├── restore_v2.py     # 版本恢复脚本
│   ├── run_app.py        # 应用运行脚本
│   ├── setup.sh          # 环境设置脚本(Linux/Mac)
│   └── start_all.bat     # Windows环境一键启动所有模块脚本
├── src/                  # 源代码目录
│   ├── __init__.py
│   ├── config/           # 配置文件目录
│   │   ├── __init__.py
│   │   └── config.json.template     # 配置文件模板
│   ├── main/             # 核心程序文件
│   │   ├── __init__.py
│   │   ├── enhanced_equity_to_mermaid.py # 图像识别生成股权结构(核心功能)
│   │   ├── equity_tool_main.py          # 旧版主入口(可选)
│   │   ├── manual_equity_editor.py      # 手动编辑生成股权结构(核心功能)
│   │   └── utils/             # 主模块工具目录
│   └── utils/            # 全局工具类和辅助函数
│       ├── __init__.py
│       ├── ai_equity_analyzer.py   # AI股权分析模块
│       ├── alicloud_translator.py  # 阿里云翻译功能
│       ├── config_encryptor.py     # 配置加密工具
│       ├── equity_llm_analyzer.py  # 大语言模型股权分析器
│       └── mermaid_function.py     # Mermaid图表生成函数
├── start_app.bat         # Windows一键启动脚本
├── start_app.py          # 统一启动脚本(推荐)
├── start_app.sh          # Linux/Mac一键启动脚本
├── test_results/         # 测试结果目录
└── tests/                # 测试文件目录
```

## 快速开始

### 1. 安装依赖
首先安装项目所需的Python依赖包：
```bash
pip install -r requirements.txt
```

### 2. 启动主程序 (推荐使用统一启动脚本)

**使用统一启动脚本 (推荐):**
```bash
python start_app.py
```

运行后将显示交互式菜单，可选择以下选项：
- 1: 主界面 (端口: 8504) - 提供功能概览和导航入口
- 2: 图像识别模式 (端口: 8501) - 基于图像的股权结构识别功能
- 3: 手动编辑模式 (端口: 8503) - 通过表单手动编辑股权关系
- 4: 启动所有模块 (需要多个终端窗口) - 同时运行所有功能模块
- 5: 退出 - 关闭启动器

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

## 关于主入口选择
我们推荐使用统一启动脚本`start_app.py`，因为：
- 提供了交互式菜单，方便选择不同功能模块
- 自动处理端口配置，避免端口冲突
- 支持一键启动所有功能模块
- 提供清晰的操作指引和帮助信息
- 自动检查环境配置，提供必要的提示

如果需要快速启动主界面，可以使用根目录下的`main_page.py`，它结构简洁，启动稳定，提供了清晰的功能介绍和使用指南。

### 平台特定启动方式
- Windows环境：可直接双击`start_app.bat`启动主界面
- Linux/Mac环境：可执行`./start_app.sh`启动主界面

## 功能说明

### 核心功能模块

#### 1. 图像识别模式 (enhanced_equity_to_mermaid.py)
- 通过上传股权结构图，自动识别公司、股东和子公司关系
- 支持使用阿里云通义千问视觉模型进行精准图像分析
- 提供模拟数据模式，无需API密钥也可体验
- 生成交互式Mermaid图表，支持缩放、拖拽和文本编辑
- 支持将中文股权信息翻译成英文（需配置阿里云翻译API）

#### 2. 手动编辑模式 (manual_equity_editor.py)
- 手动添加公司名称、股东关系、子公司和持股比例
- 提供直观的表单界面，支持复杂股权结构编辑
- 支持添加实际控制人信息和控制关系
- 实时预览生成的Mermaid图表
- 提供数据导入/导出功能，支持JSON格式

#### 3. AI分析功能 (equity_llm_analyzer.py 和 ai_equity_analyzer.py)
- 从文本描述中提取股权结构信息
- 解析Excel等文件中的股东、实控人、子公司信息
- 根据用户提示词指导分析过程
- 自动生成符合前端需要的股权结构数据格式
- 提供错误处理和模拟数据功能（当API不可用时）

#### 4. 辅助工具脚本
- **generate_equity_data_with_controller.py**: 生成包含实控人信息的股权数据JSON文件
- **import_control_relationship.py**: 读取控制关系JSON文件并转换为系统可用格式
- **mermaid_function.py**: 核心Mermaid图表生成函数，支持复杂股权关系展示
- **alicloud_translator.py**: 阿里云翻译功能集成，支持中英文股权数据互译

### 启动和配置工具

#### 统一启动脚本 (start_app.py)
- 提供交互式菜单，方便选择不同功能模块
- 自动处理端口配置，避免冲突
- 支持一键启动所有功能模块
- 提供清晰的操作指引

#### 平台特定启动脚本
- **start_app.bat**: Windows环境一键启动脚本
- **start_app.sh**: Linux/Mac环境一键启动脚本
- **scripts/start_all.bat**: Windows环境一键启动所有模块脚本

#### 配置管理
- 支持配置文件和环境变量双重配置方式
- 提供配置加密工具，保护敏感信息
- 详细的配置说明文档

## 配置说明
1. 复制 `src/config/config.json.template` 为 `src/config/config.json`
2. 根据需要配置阿里云翻译API的AccessKey
3. 可以使用 `src/utils/config_encryptor.py` 对配置进行加密保护
4. 如需使用AI分析功能，可以配置DashScope API密钥

## 部署到Streamlit Cloud
请参考 `docs/DEPLOYMENT_GUIDE.md` 文档进行部署配置。

## 端口说明
本项目使用以下端口运行不同的功能模块：
- 主界面: http://localhost:8504
- 图像识别模式: http://localhost:8501
- 手动编辑模式: http://localhost:8503

所有端口配置都可以在启动时进行调整，请确保这些端口在您的系统上未被占用。

## 便捷启动脚本

### 统一启动脚本
我们提供了功能强大的统一启动脚本`start_app.py`，它支持交互式选择功能模块，是推荐的启动方式：

```bash
python start_app.py
```

### 平台特定启动脚本

#### Windows环境
直接双击`start_app.bat`启动主界面，或使用以下命令：
```batch
start_app.bat
```

若需要一键启动所有模块（同时运行三个Streamlit服务），可使用：
```batch
scripts\start_all.bat
```

#### Linux/Mac环境
赋予脚本执行权限并运行：
```bash
chmod +x start_app.sh
./start_app.sh
```

### 脚本功能说明
- **start_app.py**: 统一入口脚本，提供交互式菜单，可启动任意功能模块
- **start_app.bat**: Windows平台简化启动脚本，直接启动主界面
- **start_app.sh**: Linux/Mac平台简化启动脚本，直接启动主界面
- **scripts/start_all.bat**: Windows专用脚本，同时启动所有三个模块
- **scripts/run_app.py**: 底层应用运行脚本，由其他启动脚本调用

## 更新日志

### 2025-10-03 更新
- **项目结构优化**：
  - 移除了根目录中的旧版`enhanced_equity_to_mermaid.py`文件
  - 删除了`src/main`目录中的`enhanced_equity_to_mermaid copy.py`文件
  - 确保项目结构更加清晰，核心代码统一存储在`src`目录下

- **功能文件整理与说明优化**：
  - 完善了项目结构文档，增加了所有目录和文件的详细说明
  - 明确标注了核心功能文件和辅助工具脚本的用途
  - 优化了示例数据目录结构，按功能分类存放各类示例数据

### 2025-10-01 更新
- **修复了AI股权结构分析报告中的"name 're' is not defined"错误**：
  - 在`equity_llm_analyzer.py`中添加了`re`模块导入
  - 在`manual_equity_editor.py`文件的AI分析执行部分添加了`re`模块导入
  - 确保在使用正则表达式功能的所有位置都正确导入了必要模块

- **解决了实时预览功能中的"'shareholders'错误"**：
  - 将`manual_equity_editor.py`中所有直接字典键访问改为使用`.get()`方法并提供默认值
  - 为文本字段提供空字符串默认值，为列表字段提供空列表默认值
  - 提高了应用处理不完整数据的能力和稳定性

- **修复了"当前数据统计总是显示为0"的问题**：
  - 优化了数据获取逻辑，优先从`st.session_state.equity_data`中获取关系数据
  - 添加了后备机制，当主数据源不可用时从`st.session_state`根级别获取
  - 确保能够正确统计并显示实体数量、股权关系和控制关系的真实数量