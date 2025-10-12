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
├── scripts/                  # 辅助脚本目录
│   ├── fix_expander.py                # 修复manual_equity_editor.py中展开面板的工具脚本
│   ├── generate_equity_data_with_controller.py  # 生成包含实控人信息的equity_data JSON文件工具
│   ├── import_control_relationship.py    # 导入控制关系工具
│   ├── mcp_env_uvx_launcher.py           # MCP环境UVX启动脚本
│   ├── restore_v2.py     # 版本恢复脚本
│   ├── run_app.py        # 应用运行脚本
│   ├── setup.sh          # 环境设置脚本(Linux/Mac)
│   └── start_all.bat     # Windows环境一键启动所有模块脚本
├── src/                  # 源代码目录
│   ├── __init__.py
│   ├── config/           # 配置文件目录
│   │   ├── __init__.py
│   │   ├── config.json.template     # 配置文件模板
│   │   └── mcp_config.json         # MCP配置文件
│   ├── main/             # 核心程序文件
│   │   ├── __init__.py
│   │   ├── enhanced_equity_to_mermaid.py # 图像识别生成股权结构(核心功能)
│   │   ├── manual_equity_editor.py      # 手动编辑生成股权结构(核心功能)
│   │   └── utils/             # 主模块工具目录
│   └── utils/            # 全局工具类和辅助函数
│       ├── __init__.py
│       ├── ai_equity_analyzer.py   # AI股权分析模块
│       ├── alicloud_translator.py  # 阿里云翻译功能
│       ├── config_encryptor.py     # 配置加密工具
│       ├── equity_llm_analyzer.py  # 大语言模型股权分析器
│       ├── icon_integration.py     # 图标集成功能
│       ├── import_control_relationship.py  # 导入控制关系工具
│       ├── mermaid_function.py     # Mermaid图表生成函数
│       └── uvx_helper.py           # UVX辅助工具
└── tests/                # 测试文件目录
```

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
我们推荐使用Windows专用启动脚本`scripts/start_all.bat`，因为它提供了交互式菜单，方便选择不同功能模块。

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
- **双重图表显示模式**：
  - **Mermaid图表**：传统流程图样式，支持文本编辑和代码导出
  - **交互式HTML图表**：专业层级结构图，基于vis.js实现交互式可视化
    - 统一节点大小，层级分明
    - 直角连接线，布局美观
    - 支持拖拽、缩放、节点高亮等交互功能
    - 可导出PNG图片和HTML文件
- 实时预览生成的股权结构图
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
- **visjs_equity_chart.py**: 交互式HTML图表生成工具，基于vis.js Network库实现
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

### Windows环境专用脚本
Windows用户可使用`scripts/start_all.bat`脚本，它提供了功能选择菜单：

```batch
scripts\start_all.bat
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

### 打包注意事项
使用 PyInstaller 打包时，添加 `--noconfirm` 参数可以避免覆盖现有目录的确认提示：
```bash
python -m PyInstaller equity_mermaid.spec --noconfirm
```

### 脚本功能说明
- **start_app.py**: 统一入口脚本，提供交互式菜单，可启动任意功能模块
- **start_app.bat**: Windows平台简化启动脚本，直接启动主界面
- **start_app.sh**: Linux/Mac平台简化启动脚本，直接启动主界面
- **scripts/start_all.bat**: Windows专用脚本，同时启动所有三个模块
- **scripts/run_app.py**: 应用启动脚本，直接启动主界面模块

## Figma图标集成方案

### 项目概述
为提升用户界面和图表可视化效果，我们推荐将TDesign开源图标库集成到项目中。本文档详细说明集成方案。

### Figma图标库分析

TDesign Icon SVG文件是一个完整的开源图标系统，包含多个分类，非常适合集成到项目中：

- **核心类别**：箭头、警报、沟通、开发、图表、设备、文档等
- **专业图标**：包含公司、组织相关的图标，特别适合股权结构展示
- **文件格式**：SVG矢量格式，支持无损缩放和颜色定制

### 集成方案

#### 1. 图标资源管理

**建议操作**：
1. 在项目中创建专门的图标资源目录：`src/assets/icons/`
2. 下载核心SVG图标，特别是与商业和公司相关的图标
3. 按功能分类组织图标（如：公司图标、操作图标、导航图标等）

#### 2. 用户界面组件优化

**功能卡片优化**：
```python
# main_page.py 中的功能卡片使用自定义SVG图标代替FontAwesome

# 示例代码修改
feature_html = f"""
<div class="feature-card">
    <div class="icon">
        <img src="data:image/svg+xml;base64,{svg_icon_encoded}" width="48" height="48">
    </div>
    <h3>{title}</h3>
    <p>{description}</p>
    <a href="{url}" class="btn">{button_text}</a>
</div>
"""
```

#### 3. Mermaid图表图标集成

**实体样式增强**：
```python
# mermaid_function.py 中增强实体样式，添加图标

# 在类定义中使用Mermaid支持的图标语法
mermaid_code += "    classDef company fill:#f3f4f6,stroke:#5a6772,stroke-width:2px,rx:4,ry:4,font-family:'Arial',font-size:14px,labelBackgroundColor:#f3f4f6,labelBorderColor:#5a6772,labelBorderWidth:1px,labelRadius:4px;
"
mermaid_code += "    classDef subsidiary fill:#ffffff,stroke:#1e88e5,stroke-width:1.5px,rx:4,ry:4,labelBackgroundColor:#ffffff,labelBorderColor:#1e88e5,labelBorderWidth:1px,labelRadius:4px;
"
mermaid_code += "    classDef topEntity fill:#0d47a1,color:#ffffff,stroke:#ffffff,stroke-width:2px,rx:4,ry:4,labelBackgroundColor:#0d47a1,labelBorderColor:#ffffff,labelBorderWidth:1px,labelRadius:4px;
"
mermaid_code += "    classDef coreCompany fill:#fff8e1,stroke:#ff9100,stroke-width:2px,rx:6,ry:6,labelBackgroundColor:#fff8e1,labelBorderColor:#ff9100,labelBorderWidth:1px,labelRadius:6px;
"
```

#### 4. 导航栏和侧边栏图标增强

**导航元素图标化**：
```python
# 侧边栏菜单项添加对应图标
st.sidebar.button(
    label=f":chart_with_upwards_trend: 图像识别模式",
    on_click=lambda: st.switch_page("pages/1_图像识别模式.py")
)
st.sidebar.button(
    label=f":pencil: 手动编辑模式",
    on_click=lambda: st.switch_page("pages/2_手动编辑模式.py")
)
```

### 具体实施步骤

1. **图标提取**：使用Figma AI Bridge工具下载选定的SVG图标
2. **资源整合**：将图标转换为Base64编码或直接引用文件路径
3. **样式更新**：
   - 更新CSS变量系统，添加图标相关样式
   - 为UI组件创建新的图标容器样式
4. **代码修改**：
   - 修改Mermaid图表生成函数，支持实体图标
   - 更新UI组件渲染逻辑，使用SVG图标
5. **测试验证**：确保图标在不同设备和分辨率下正确显示

### 推荐集成的关键图标

1. **实体类型图标**：
   - 公司/企业图标（建筑分类中的building、office等）
   - 个人图标（用户分类中的user图标）
   - 政府/机构图标（可以使用特殊建筑图标）

2. **操作功能图标**：
   - 分析/识别图标（图表分类中的analytics图标）
   - 编辑/修改图标（操作分类中的edit图标）
   - 导出/保存图标（文件分类中的export图标）

3. **界面导航图标**：
   - 主页/首页图标
   - 设置/配置图标
   - 帮助/信息图标

### 优势和价值

1. **视觉一致性**：使用统一风格的图标系统，提升品牌感
2. **直观表达**：通过图标快速区分不同类型的实体和操作
3. **专业外观**：符合商务应用的专业视觉标准
4. **用户体验**：增强导航的可识别性和交互的直观性
5. **国际化支持**：图标是语言无关的，有助于全球用户理解

## 更新日志

### 2025-10-11 更新 - HTML图表显示优化
- **专业股权结构图线条优化**：
  - 将连接线从曲线改为直线，符合专业股权结构图标准
  - 调整线条颜色方案：股权关系使用蓝色（#1976d2），控制关系使用红色（#d32f2f）
  - 优化线条粗细：从3px调整为2px，避免过粗影响视觉效果
  - 控制关系使用虚线样式（[5, 5]），与股权关系区分

- **百分比标签显示优化**：
  - 缩小箭头大小：使用`scaleFactor: 0.6`，避免箭头遮挡百分比数字
  - 调整字体大小：从16px减小到12px，与缩小的箭头更协调
  - 改进标签对齐：使用`align: 'horizontal'`让百分比标签水平显示，更容易阅读
  - 优化标签背景：使用`rgba(255, 255, 255, 0.95)`半透明白色背景，更清晰
  - 减少描边宽度：从2px减少到1px，避免过粗影响美观

- **统一层级计算逻辑**：
  - 创建了`_calculate_unified_levels()`统一层级计算函数
  - 简化HTML层级计算逻辑，参考Mermaid的自动推断方式
  - 使用迭代算法确保层级一致性：`child = parent + 1`
  - 移除复杂的手动水平位置分配，让vis.js自动处理布局
  - 确保HTML和Mermaid使用相同的层级分配规则

- **vis.js配置优化**：
  - 禁用物理引擎：`physics.enabled: false`，使用纯层级布局
  - 禁用稳定化：`stabilization.enabled: false`，使用固定布局
  - 优化全局边配置：统一箭头大小、字体大小和对齐方式
  - 增加选中和悬停时的线条粗细到3px，提升交互体验

- **技术改进细节**：
  - 修复了Unicode编码错误：实现`_safe_print()`函数处理中文字符
  - 优化了调试信息显示：简化调试输出，避免信息过载
  - 改进了错误处理：添加了更完善的异常处理机制
  - 统一了配置参数：确保所有边都有一致的显示效果

### 2025-10-10 更新
- **新增交互式HTML股权结构图可视化功能**：
  - 在手动编辑模式中添加了基于vis.js的交互式图表展示
  - 创建了`src/utils/visjs_equity_chart.py`工具模块
  - 提供双重图表显示模式：用户可在Mermaid图表和交互式HTML图表之间切换
  - 交互式HTML图表特性：
    - 统一矩形节点（150x60像素）
    - 层级化布局（hierarchical layout），从上到下清晰展示
    - 直角连接线（cubicBezier），视觉效果更专业
    - 实体类型颜色区分：实际控制人（深蓝）、核心公司（橙色）、个人（绿色）、普通公司（蓝色边框）
    - 交互功能：拖拽节点、滚轮缩放、点击高亮相关路径
    - 导出功能：支持导出PNG图片和独立HTML文件
  - 完全保留原有Mermaid图表功能，不影响现有用户体验
  - 所有功能模块化设计，易于维护和扩展

### 2025-10-08 更新
- **修复了实体数量统计问题**：
  - 修改了manual_equity_editor.py中数据统计部分，将实体数量计算从"从股权关系中提取所有唯一实体"改为直接使用top_level_entities的数量
  - 确保AI股权结构分析报告下方的数据统计能正确显示顶级实体的实际数量
  - 优化了数据获取逻辑，保持与equity_data数据结构的一致性
  
- **文件结构优化与规范化**：
  - 明确区分`scripts`和`utils`目录用途：`scripts`存放独立可执行脚本，`utils`存放被导入的工具类和函数
  - 将`fix_expander.py`和`generate_equity_data_with_controller.py`辅助脚本移动到`scripts`目录
  - 将`import_control_relationship.py`和`mcp_env_uvx_launcher.py`从`utils`目录移动到`scripts`目录
  - 将`mcp_config.json`配置文件从`utils`目录移动到`src/config`目录
  - 更新README.md中的文件结构描述和更新日志
- **项目规则优化**：
  - 将`.trae/rules/project_rules.md`重写为`.trae/rules/project_rules.yaml`，修正文件格式问题
  - 调整`allow_file_write`设置为`true`以允许开发工作
  - 创建`tests/results`目录用于存放测试结果
  - 优化规则结构，移除重复内容，添加清晰的分类和说明
- **安全配置更新**：
  - 将`allow_network_access`设置为`true`，允许正常的网络查询访问
  - 保留对破坏性操作和外部API调用的用户确认要求
- **应用布局与配置一致性优化**：
  - 修复了应用界面布局问题，确保主题颜色、侧边栏样式和响应式布局正常显示
  - 统一了`.streamlit/config.toml`与`main_page.py`中的颜色配置，确保一致性
  - 更新了主题颜色设置，primaryColor设置为#0f4c81、secondaryBackgroundColor设置为#f8f9fa、textColor设置为#2c3e50
  - 验证了打包后的应用程序运行正常，终端日志显示无布局相关错误，浏览器预览显示界面正常加载
  - 确保了配置一致性问题修复已在打包应用中生效

### 2025-10-07 更新
- **移除旧版主入口文件**：
  - 删除了不再使用的`src/main/equity_tool_main.py`旧版主入口文件
  - 更新README.md文档，移除对该文件的所有引用
  - 确保项目结构更加清晰，只保留当前使用的核心文件

- **优化侧边栏按钮样式**：
  - 修改了手动编辑模式中侧边栏导航按钮的背景样式
  - 将"图像识别模式"和"手动编辑模式"按钮的背景设置为透明
  - 添加了精确的CSS选择器和高优先级样式规则，确保覆盖默认样式
  - 移除了按钮的边框、阴影和背景图像，保留基本文本样式
  - 添加了轻微的悬停效果，提升用户交互体验
  - 确保侧边栏按钮样式与使用说明保持一致

### 2025-10-06 更新
- **修复了'核心公司'步骤中'AI分析'按钮跳转功能**：
  - 为'AI分析'按钮添加了唯一的key标识，避免与其他按钮冲突
  - 实现了分析完成后自动跳转到'关系设置'步骤的功能
  - 在AI分析成功后自动设置`st.session_state.current_step = "relationships"`并调用`st.rerun()`进行页面刷新
  - 清理了多余代码，确保跳转逻辑清晰完整，提升用户体验

### 2025-10-05 更新
- **启动脚本优化**：
  - 修改了`scripts/run_app.py`脚本，移除菜单选择功能，直接启动主界面模块
  - 更新了相关文档描述，确保与实际功能一致
- **UI界面统一化优化**：
  - 统一了手动编辑模式中所有核心按钮的颜色样式
  - 确保了"保存并继续"、"添加顶级实体"、"添加子公司"和"添加股权关系"等按钮显示为统一的商务深蓝色
  - 添加了特定的CSS样式规则，使用正确的选择器和优先级确保样式正确应用
  - 为所有按钮添加了文本换行属性，确保在各种情况下文本都能正确显示
  - 更新了信息框和实体卡片的样式，统一使用CSS变量管理主题色

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