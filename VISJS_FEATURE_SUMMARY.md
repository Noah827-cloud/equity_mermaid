# 企查查风格股权结构图可视化功能 - 实施总结

## 📋 概述

本次更新在手动编辑模式中成功添加了企查查风格的交互式股权结构图可视化功能，基于vis.js Network库实现，与原有Mermaid图表并存，为用户提供更专业的可视化选择。

## ✅ 完成的工作

### 1. 核心工具模块创建
**文件**: `src/utils/visjs_equity_chart.py`

**主要函数**:
- `convert_equity_data_to_visjs(equity_data)` - 数据格式转换
  - 将equity_data转换为vis.js所需的nodes和edges格式
  - 自动设置节点层级（hierarchical layout）
  - 根据实体类型和角色分配颜色样式
  
- `generate_visjs_html(nodes, edges, height, enable_physics)` - HTML生成
  - 生成包含vis.js库的完整HTML页面
  - 内嵌CSS样式和JavaScript交互逻辑
  - 支持自定义容器高度
  
- `generate_fullscreen_visjs_html(nodes, edges)` - 全屏模式
  - 专为新标签页全屏显示优化
  - 容器高度设为100vh

### 2. 主程序集成
**文件**: `src/main/manual_equity_editor.py`

**修改内容**:
- 在"生成图表"步骤（第3625行起）添加图表类型选择器
- 使用`st.radio()`提供"Mermaid图表"和"企查查风格图表"两个选项
- 添加`_display_visjs_chart()`辅助函数处理vis.js图表显示
- 完全保留原有Mermaid图表功能和代码

### 3. 用户界面优化
**新增功能**:
- 图表类型切换开关（Radio按钮）
- 三个操作按钮：
  - 🔍 全屏查看图表 - 在新标签页打开完整交互版本
  - 📥 下载JSON数据 - 导出股权结构数据
  - 📥 下载HTML图表 - 保存独立可运行的HTML文件
- 实时统计信息显示：
  - 节点数量
  - 关系数量
  - 实体类型分布

## 🎨 可视化特性

### 节点设计
- **统一尺寸**: 150x60像素矩形
- **颜色区分**:
  - 实际控制人: 深蓝背景 (#0d47a1) + 白色字体
  - 核心公司: 橙黄背景 (#fff8e1) + 橙色边框 (#ff9100)
  - 个人股东: 淡绿背景 (#e8f5e9) + 绿色边框 (#4caf50)
  - 普通公司: 白色背景 + 蓝色边框 (#1976d2)
  - 政府机构: 灰色背景 + 灰色边框

### 连接线设计
- **股权关系**: 蓝色实线 (#1976d2)，标签显示持股比例
- **控制关系**: 红色虚线 (#d32f2f)，标签显示"控制"
- **线条样式**: cubicBezier曲线，接近直角效果，视觉更专业

### 布局算法
- **Hierarchical Layout**: 分层布局
- **方向**: 从上到下 (UD - Up-Down)
- **层级间距**: 150px
- **节点间距**: 120px
- **智能层级分配**:
  - Level 0: 顶级实体（股东、实际控制人）
  - Level 1: 核心公司
  - Level 2+: 子公司（根据持股关系自动计算）

### 交互功能
1. **拖拽移动**: 可拖拽整个视图查看不同区域
2. **滚轮缩放**: Ctrl+滚轮进行缩放
3. **节点高亮**: 点击节点高亮其所有相关关系
4. **适应窗口**: 自动调整视图以显示全部内容
5. **导出PNG**: 一键导出高清图片
6. **重置视图**: 恢复默认缩放和位置

## 📊 技术实现

### 前端库选择
- **vis.js Network v9.1.2**
- CDN: `https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js`
- 轻量级、功能强大、文档完善

### Streamlit集成
- 使用`streamlit.components.v1.html()`嵌入HTML内容
- 容器高度: 850px（含图例和控制按钮）
- 图表区域: 800px

### 数据流程
```
equity_data (dict)
    ↓
convert_equity_data_to_visjs()
    ↓
nodes (list), edges (list)
    ↓
generate_visjs_html()
    ↓
HTML string
    ↓
st.components.html()
    ↓
用户浏览器渲染
```

## 🧪 测试验证

已通过完整测试：
- ✅ 模块导入测试
- ✅ 数据转换测试（4个节点，4条边）
- ✅ HTML生成测试（11,900字符）
- ✅ 节点层级分配测试
- ✅ 颜色样式测试
- ✅ 交互功能测试

## 📚 使用文档

### 用户操作流程
1. 在手动编辑模式中完成股权结构数据录入
2. 进入"生成图表"步骤
3. 选择"企查查风格图表"选项
4. 查看生成的交互式图表
5. 使用工具按钮进行操作：
   - 点击"全屏查看图表"在新窗口查看
   - 点击"下载HTML图表"保存独立文件
   - 点击"适应窗口"调整视图
   - 点击"导出PNG"保存图片

### 开发者接口

```python
from src.utils.visjs_equity_chart import (
    convert_equity_data_to_visjs,
    generate_visjs_html,
    generate_fullscreen_visjs_html
)

# 转换数据
nodes, edges = convert_equity_data_to_visjs(equity_data)

# 生成HTML
html_content = generate_visjs_html(nodes, edges, height="800px")

# 在Streamlit中显示
import streamlit.components.v1 as components
components.html(html_content, height=850)
```

## 🎯 设计原则

1. **不影响现有功能**: 完全保留Mermaid图表，两种图表并存
2. **模块化设计**: 工具函数独立，易于维护和测试
3. **用户友好**: 提供图表类型切换，操作直观
4. **专业视觉**: 参考企查查设计，符合商务应用标准
5. **性能优化**: 使用CDN加载库，减少打包体积

## 📈 未来改进方向

1. **增强交互**:
   - 添加节点编辑功能
   - 支持关系筛选
   - 添加搜索高亮功能

2. **布局优化**:
   - 支持多种布局算法选择
   - 自定义节点位置保存

3. **样式定制**:
   - 提供主题选择（亮色/暗色）
   - 支持自定义颜色配置

4. **导出增强**:
   - 支持SVG导出
   - 支持PDF导出
   - 导出配置选项

## 📝 更新记录

- **2025-10-10**: 初始版本发布
  - 创建visjs_equity_chart.py工具模块
  - 集成到manual_equity_editor.py
  - 完成测试和文档

---

**开发者**: AI Assistant  
**日期**: 2025年10月10日  
**状态**: ✅ 已完成并测试通过

