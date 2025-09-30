# 股权结构可视化工具

## 项目简介
本项目提供股权结构可视化工具，支持通过图片识别和手动编辑两种方式生成股权关系Mermaid图表。

## 项目结构

```
├── .gitignore            # Git忽略文件
├── requirements.txt      # Python依赖列表
├── src/
│   ├── main/             # 核心程序文件
│   │   ├── equity_tool_main.py          # 主入口页面
│   │   ├── enhanced_equity_to_mermaid.py # 图像识别生成股权结构
│   │   └── manual_equity_editor.py      # 手动编辑生成股权结构
│   ├── utils/            # 工具类和辅助函数
│   │   ├── mermaid_function.py     # Mermaid图表生成函数
│   │   ├── alicloud_translator.py  # 阿里云翻译功能
│   │   └── config_encryptor.py     # 配置加密工具
│   └── config/           # 配置文件
│       └── config.json.template     # 配置文件模板
├── docs/                 # 文档
│   ├── README.md              # 详细使用说明
│   └── DEPLOYMENT_GUIDE.md    # 部署指南
├── scripts/              # 脚本文件
│   ├── setup.sh         # 环境设置脚本
│   ├── run_app.py       # 应用启动脚本
│   └── restore_v2.py    # 恢复脚本
├── examples/             # 示例和测试文件
│   ├── demo.py          # 示例程序
│   ├── test_equity_data.json  # 测试数据
│   └── image.demo.txt   # 图片演示说明
└── legacy/               # 旧版本和历史文件
```

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动主程序
```bash
python -m streamlit run src/main/equity_tool_main.py
```

### 3. 直接启动特定功能
- 图像识别模式:
  ```bash
  python -m streamlit run src/main/enhanced_equity_to_mermaid.py
  ```
- 手动编辑模式:
  ```bash
  python -m streamlit run src/main/manual_equity_editor.py
  ```

## 功能说明

### 图像识别模式
通过上传股权结构图，自动识别公司、股东和子公司关系，生成交互式Mermaid图表。

### 手动编辑模式
手动添加公司名称、股东关系、子公司和持股比例，生成交互式Mermaid图表。

### 翻译功能
支持将中文股权信息翻译成英文（需要配置阿里云翻译API）。

## 配置说明
1. 复制 `src/config/config.json.template` 为 `src/config/config.json`
2. 根据需要配置阿里云翻译API的AccessKey
3. 可以使用 `src/utils/config_encryptor.py` 对配置进行加密保护

## 部署到Streamlit Cloud
请参考 `docs/DEPLOYMENT_GUIDE.md` 文档进行部署配置。