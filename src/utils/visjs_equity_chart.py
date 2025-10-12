#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式HTML股权结构图可视化工具
使用 vis.js Network 库生成交互式股权结构图
"""

import json
from typing import Dict, List, Any, Tuple


def _safe_print(msg):
    """安全地打印消息，避免编码错误"""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        except:
            pass


def convert_equity_data_to_visjs(equity_data: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    """
    将 equity_data 转换为 vis.js 所需的 nodes 和 edges 格式
    
    Args:
        equity_data: 股权数据字典，包含实体、关系等信息
    
    Returns:
        Tuple[List[Dict], List[Dict]]: (nodes, edges) 节点列表和边列表
    """
    nodes = []
    edges = []
    node_id_map = {}  # 实体名称 -> node_id 映射
    node_counter = 0
    
    # 获取核心公司
    core_company = equity_data.get("core_company", "")
    
    # 获取实际控制人
    actual_controller = equity_data.get("actual_controller", "")
    
    # 获取所有实体
    all_entities = equity_data.get("all_entities", [])
    
    # 获取顶级实体
    top_level_entities = equity_data.get("top_level_entities", [])
    
    # 创建节点
    for entity in all_entities:
        entity_name = entity.get("name", "")
        entity_type = entity.get("type", "company")
        
        if not entity_name:
            continue
        
        # 确定节点样式
        node_style = _get_node_style(entity_name, entity_type, core_company, actual_controller)
        
        node = {
            "id": node_counter,
            "label": entity_name,
            "shape": "box",
            "widthConstraint": {"minimum": 150, "maximum": 250},
            "heightConstraint": {"minimum": 60},
            "font": {
                "size": 14,
                "color": node_style["font_color"],
                "multi": "html",
                "bold": {
                    "color": node_style["font_color"]
                }
            },
            "color": {
                "background": node_style["bg_color"],
                "border": node_style["border_color"],
                "highlight": {
                    "background": node_style["highlight_bg"],
                    "border": node_style["highlight_border"]
                }
            },
            "borderWidth": 2,
            "margin": 10,
            "level": None  # 将在后续设置层级
        }
        
        node_id_map[entity_name] = node_counter
        nodes.append(node)
        node_counter += 1
    
    # 设置节点层级
    _set_node_levels(nodes, node_id_map, top_level_entities, core_company, equity_data)
    
    # 创建边（股权关系）
    entity_relationships = equity_data.get("entity_relationships", [])
    
    # 🔥 关键修复：关系去重，避免重复的边
    seen_relationships = set()
    for rel in entity_relationships:
        from_entity = rel.get("from", rel.get("parent", ""))
        to_entity = rel.get("to", rel.get("child", ""))
        percentage = rel.get("percentage", 0)
        
        if from_entity in node_id_map and to_entity in node_id_map:
            # 创建关系键，用于去重
            rel_key = f"{from_entity}_{to_entity}"
            
            # 如果关系已存在，跳过或合并
            if rel_key in seen_relationships:
                _safe_print(f"跳过重复的股权关系: {from_entity} -> {to_entity} ({percentage}%)")
                continue
            
            seen_relationships.add(rel_key)
            
            edge = {
                "from": node_id_map[from_entity],
                "to": node_id_map[to_entity],
                "arrows": {
                    "to": {
                        "enabled": True,
                        "scaleFactor": 0.6,  # 🔥 缩小箭头大小
                        "type": "arrow"
                    }
                },
                "label": f"{percentage}%" if percentage > 0 else "",
                "font": {
                    "size": 12,  # 🔥 减小字体大小，避免被箭头遮挡
                    "align": "horizontal",  # 🔥 水平对齐，更容易阅读
                    "background": "rgba(255, 255, 255, 0.95)",  # 🔥 更不透明的背景
                    "strokeWidth": 1,  # 🔥 减少描边宽度
                    "strokeColor": "rgba(0, 0, 0, 0.1)",  # 🔥 淡色描边
                    "color": "#000000",
                    "bold": True,
                    "multi": "html"  # 🔥 支持HTML格式
                },
                "color": {"color": "#1976d2", "highlight": "#0d47a1"},  # 🔥 使用蓝色，更专业
                "width": 2,  # 🔥 适中的线条粗细
                "smooth": {
                    "type": "straight",  # 🔥 使用直线，符合专业股权结构图标准
                    "enabled": True
                }
            }
            edges.append(edge)
    
    # 创建边（控制关系）
    control_relationships = equity_data.get("control_relationships", [])
    
    # 🔥 关键修复：控制关系去重，避免重复的边
    seen_control_relationships = set()
    for rel in control_relationships:
        # 支持多种键格式: from/to, controller/controlled, parent/child
        from_entity = rel.get("from", rel.get("controller", rel.get("parent", "")))
        to_entity = rel.get("to", rel.get("controlled", rel.get("child", "")))
        
        if from_entity in node_id_map and to_entity in node_id_map:
            # 创建控制关系键，用于去重
            control_rel_key = f"{from_entity}_{to_entity}_control"
            
            # 如果控制关系已存在，跳过
            if control_rel_key in seen_control_relationships:
                _safe_print(f"跳过重复的控制关系: {from_entity} -> {to_entity}")
                continue
            
            seen_control_relationships.add(control_rel_key)
            
            # 获取描述信息或使用默认的"控制"
            description = rel.get("description", "控制")
            
            edge = {
                "from": node_id_map[from_entity],
                "to": node_id_map[to_entity],
                "arrows": {
                    "to": {
                        "enabled": True,
                        "scaleFactor": 0.6,  # 🔥 缩小箭头大小
                        "type": "arrow"
                    }
                },
                "label": description if len(description) < 30 else "控制",  # 太长的描述简化显示
                "font": {
                    "size": 12,  # 🔥 减小字体大小，避免被箭头遮挡
                    "align": "horizontal",  # 🔥 水平对齐，更容易阅读
                    "background": "rgba(255, 255, 255, 0.95)",  # 🔥 更不透明的背景
                    "strokeWidth": 1,  # 🔥 减少描边宽度
                    "strokeColor": "rgba(0, 0, 0, 0.1)",  # 🔥 淡色描边
                    "color": "#000000",
                    "bold": True,
                    "multi": "html"  # 🔥 支持HTML格式
                },
                "color": {"color": "#d32f2f", "highlight": "#b71c1c"},  # 🔥 使用红色，表示控制关系
                "width": 2,  # 🔥 适中的线条粗细
                "dashes": [5, 5],  # 虚线
                "smooth": {
                    "type": "straight",  # 🔥 使用直线，符合专业股权结构图标准
                    "enabled": True
                }
            }
            edges.append(edge)
    
    return nodes, edges


def _get_node_style(entity_name: str, entity_type: str, core_company: str, actual_controller: str) -> Dict[str, str]:
    """
    根据实体类型和角色确定节点样式
    
    Args:
        entity_name: 实体名称
        entity_type: 实体类型 (person/company/government等)
        core_company: 核心公司名称
        actual_controller: 实际控制人名称
    
    Returns:
        Dict[str, str]: 包含颜色配置的字典
    """
    # 实际控制人 - 深蓝色背景，白色字体
    if entity_name == actual_controller:
        return {
            "bg_color": "#0d47a1",
            "border_color": "#0d47a1",
            "font_color": "#ffffff",
            "highlight_bg": "#1565c0",
            "highlight_border": "#0d47a1"
        }
    
    # 核心公司 - 橙色背景
    if entity_name == core_company:
        return {
            "bg_color": "#fff8e1",
            "border_color": "#ff9100",
            "font_color": "#000000",
            "highlight_bg": "#ffecb3",
            "highlight_border": "#ff6f00"
        }
    
    # 个人 - 绿色边框
    if entity_type == "person" or entity_type == "individual":
        return {
            "bg_color": "#e8f5e9",
            "border_color": "#4caf50",
            "font_color": "#000000",
            "highlight_bg": "#c8e6c9",
            "highlight_border": "#388e3c"
        }
    
    # 政府/机构 - 灰色边框
    if entity_type == "government" or entity_type == "institution":
        return {
            "bg_color": "#f5f5f5",
            "border_color": "#757575",
            "font_color": "#000000",
            "highlight_bg": "#eeeeee",
            "highlight_border": "#616161"
        }
    
    # 普通公司 - 蓝色边框
    return {
        "bg_color": "#ffffff",
        "border_color": "#1976d2",
        "font_color": "#000000",
        "highlight_bg": "#e3f2fd",
        "highlight_border": "#1565c0"
    }


def _calculate_unified_levels(equity_data: Dict[str, Any]) -> Dict[str, int]:
    """
    统一的层级计算函数，确保HTML和Mermaid使用相同的层级分配规则
    
    Args:
        equity_data: 完整的股权数据
        
    Returns:
        Dict[str, int]: 实体名称到层级的映射
    """
    # 获取所有关系
    entity_relationships = equity_data.get("entity_relationships", [])
    control_relationships = equity_data.get("control_relationships", [])
    all_relationships = entity_relationships + control_relationships
    
    # 获取核心公司
    core_company = equity_data.get("core_company", "")
    
    # 初始化层级映射
    entity_levels = {}
    
    # 核心公司作为基准点（Level 0）
    if core_company:
        entity_levels[core_company] = 0
    
    # 🔥 统一逻辑：使用Mermaid式的自动推断
    # 通过关系自动推断层级，而不是手动设置
    max_iterations = 10  # 防止无限循环
    iteration = 0
    
    while iteration < max_iterations:
        changed = False
        
        # 遍历所有关系，自动推断层级
        for rel in all_relationships:
            parent_entity = rel.get("parent", rel.get("from", ""))
            child_entity = rel.get("child", rel.get("to", ""))
            
            if parent_entity and child_entity:
                parent_level = entity_levels.get(parent_entity)
                child_level = entity_levels.get(child_entity)
                
                # 自动推断：child = parent + 1
                if parent_level is not None and child_level is None:
                    entity_levels[child_entity] = parent_level + 1
                    changed = True
                elif child_level is not None and parent_level is None:
                    entity_levels[parent_entity] = child_level - 1
                    changed = True
                elif parent_level is not None and child_level is not None:
                    # 如果两者都有层级，确保一致性
                    if child_level != parent_level + 1:
                        entity_levels[child_entity] = parent_level + 1
                        changed = True
        
        # 如果没有变化，说明层级已经稳定
        if not changed:
            break
            
        iteration += 1
    
    # 为未设置层级的实体设置默认层级
    all_entities = equity_data.get("all_entities", [])
    for entity in all_entities:
        entity_name = entity.get("name", "")
        if entity_name and entity_name not in entity_levels:
            if entity_name == core_company:
                entity_levels[entity_name] = 0  # 核心公司为0
            else:
                entity_levels[entity_name] = 1  # 其他未分类实体默认为1
    
    return entity_levels


def _set_node_levels(nodes: List[Dict], node_id_map: Dict[str, int], 
                     top_level_entities: List[Dict], core_company: str, 
                     equity_data: Dict[str, Any]) -> None:
    """
    使用统一的层级计算逻辑，确保HTML和Mermaid使用相同的层级分配规则
    
    Args:
        nodes: 节点列表
        node_id_map: 实体名称到节点ID的映射
        top_level_entities: 顶级实体列表
        core_company: 核心公司名称
        equity_data: 完整的股权数据
    """
    # 🔥 使用统一的层级计算函数
    entity_levels = _calculate_unified_levels(equity_data)
    
    # 将层级应用到节点
    for node in nodes:
        # 找到节点对应的实体名称
        node_name = None
        for name, node_id in node_id_map.items():
            if node_id == nodes.index(node):
                node_name = name
                break
        
        if node_name and node_name in entity_levels:
            node["level"] = entity_levels[node_name]
        else:
            # 如果找不到对应的实体，设置默认层级
            node["level"] = 1
    
    # 简化的调试信息
    debug_info = "[DEBUG] Unified level assignment:\n"
    debug_info += f"Core company: {core_company}\n"
    debug_info += f"Total entities: {len(entity_levels)}\n"
    debug_info += "Entity levels:\n"
    
    for entity_name, level in entity_levels.items():
        try:
            entity_name.encode('cp1252')
            debug_info += f"  - {entity_name}: level {level}\n"
        except (UnicodeEncodeError, UnicodeDecodeError):
            debug_info += f"  - Entity: level {level}\n"
    
    # 使用安全打印函数避免Unicode编码错误
    _safe_print(debug_info)
    
    # 保存调试信息到session state
    import streamlit as st
    if hasattr(st, 'session_state'):
        st.session_state.debug_level_info = debug_info


def generate_visjs_html(nodes: List[Dict], edges: List[Dict], 
                        height: str = "800px", 
                        enable_physics: bool = False,
                        level_separation: int = 150,  # 层级间距
                        node_spacing: int = 200,     # 节点间距
                        tree_spacing: int = 200,     # 树间距
                        subgraphs: List[Dict] = None) -> str:
    """
    生成包含 vis.js 图表的完整 HTML 代码（集成可折叠工具栏和subgraph功能）
    
    Args:
        nodes: vis.js 节点列表
        edges: vis.js 边列表
        height: 图表容器高度
        enable_physics: 是否启用物理引擎（用于动态布局）
        level_separation: 层级间距（上下间距）
        node_spacing: 节点间距（左右间距）
        tree_spacing: 树间距
        subgraphs: 分组配置列表
    
    Returns:
        str: 完整的 HTML 代码
    """
    # 使用ensure_ascii=False保留中文，但转义特殊字符
    nodes_json = json.dumps(nodes, ensure_ascii=False, indent=None)
    edges_json = json.dumps(edges, ensure_ascii=False, indent=None)
    subgraphs_json = json.dumps(subgraphs or [], ensure_ascii=False, indent=None)
    
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>交互式HTML股权结构图</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network@9.1.6/dist/vis-network.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: #f8f9fa;
            overflow: hidden;
        }}
        
        #network-container {{
            width: 100%;
            height: {height};
            border: 1px solid #dee2e6;
            background-color: #ffffff;
            border-radius: 8px;
            margin: 10px;
            position: relative;
        }}
        
        /* 可折叠工具栏样式 */
        .toolbar-container {{
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 1000;
            display: flex;
            flex-direction: row-reverse;
            align-items: flex-start;
        }}
        
        .toolbar-toggle {{
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 15px;
            border-radius: 8px 0 0 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .toolbar-toggle:hover {{
            background: #0056b3;
            transform: translateX(-2px);
        }}
        
        .toolbar-toggle.collapsed {{
            border-radius: 8px;
        }}
        
        .toolbar-toggle .toggle-icon {{
            transition: transform 0.3s ease;
        }}
        
        .toolbar-toggle.collapsed .toggle-icon {{
            transform: rotate(180deg);
        }}
        
        .toolbar-panel {{
            background: white;
            border-radius: 8px 0 0 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
            overflow: hidden;
            max-width: 300px;
        }}
        
        .toolbar-panel.collapsed {{
            width: 0;
            opacity: 0;
            transform: translateX(100%);
        }}
        
        .toolbar-panel.expanded {{
            width: 280px;
            opacity: 1;
            transform: translateX(0);
        }}
        
        .toolbar-content {{
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-width: 250px;
        }}
        
        .control-btn {{
            padding: 8px 12px;
            border: 1px solid #6c757d;
            background: white;
            color: #495057;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }}
        
        .control-btn:hover {{
            background: #6c757d;
            color: white;
        }}
        
        .control-section {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
            border: 1px solid #dee2e6;
        }}
        
        .control-section h4 {{
            margin: 0 0 10px 0;
            font-size: 13px;
            color: #495057;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .slider-container {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        
        .slider-label {{
            width: 50px;
            font-size: 11px;
            color: #6c757d;
        }}
        
        .slider {{
            flex: 1;
            margin: 0 8px;
            height: 4px;
            border-radius: 2px;
            background: #dee2e6;
            outline: none;
            -webkit-appearance: none;
        }}
        
        .slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #007bff;
            cursor: pointer;
            border: 2px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .slider::-moz-range-thumb {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #007bff;
            cursor: pointer;
            border: 2px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .slider-value {{
            width: 35px;
            text-align: center;
            font-size: 11px;
            font-weight: bold;
            color: #007bff;
        }}
        
        .checkbox-container {{
            display: flex;
            align-items: center;
            margin: 5px 0;
            padding: 5px;
            background: white;
            border-radius: 4px;
            border: 1px solid #dee2e6;
        }}
        
        .checkbox-container input[type="checkbox"] {{
            margin-right: 8px;
            transform: scale(1.1);
        }}
        
        .checkbox-container label {{
            font-size: 11px;
            color: #495057;
            cursor: pointer;
            flex: 1;
        }}
        
        .checkbox-container .subgraph-color {{
            width: 10px;
            height: 10px;
            border-radius: 2px;
            margin-left: 5px;
            border: 1px solid;
        }}
        
        /* 分组框样式 */
        .subgraph-box {{
            position: absolute;
            border: 4px dashed;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            pointer-events: none;
            z-index: 1;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .subgraph-label {{
            position: absolute;
            top: -15px;
            left: 15px;
            background: white;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: bold;
            border-radius: 6px;
            border: 2px solid;
            z-index: 2;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: white;
            padding: 10px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 1000;
            font-size: 12px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 4px 0;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            margin-right: 8px;
            border: 2px solid;
        }}
        
        .reset-btn {{
            background: #dc3545;
            color: white;
            border: 1px solid #dc3545;
        }}
        
        .reset-btn:hover {{
            background: #c82333;
            border-color: #bd2130;
        }}
        
        .select-all-btn {{
            background: #28a745;
            color: white;
            border: 1px solid #28a745;
            margin-bottom: 5px;
        }}
        
        .select-all-btn:hover {{
            background: #218838;
            border-color: #1e7e34;
        }}
        
        .btn-row {{
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }}
        
        .btn-row .control-btn {{
            flex: 1;
            min-width: 60px;
        }}
    </style>
</head>
<body>
    <div id="network-container"></div>
    
    <div class="toolbar-container">
        <div class="toolbar-panel" id="toolbarPanel">
            <div class="toolbar-content">
                <div class="control-section">
                    <h4>📏 默认内边距</h4>
                    <div class="slider-container">
                        <span class="slider-label">水平:</span>
                        <input type="range" class="slider" id="defaultPaddingX" min="0" max="100" value="25">
                        <span class="slider-value" id="defaultPaddingXValue">25px</span>
                    </div>
                    <div class="slider-container">
                        <span class="slider-label">垂直:</span>
                        <input type="range" class="slider" id="defaultPaddingY" min="0" max="80" value="20">
                        <span class="slider-value" id="defaultPaddingYValue">20px</span>
                    </div>
                    <button class="control-btn reset-btn" onclick="resetDefaultPadding()">重置默认</button>
                </div>
                
                <div class="control-section">
                    <h4>🎛️ 分组选择</h4>
                    <button class="control-btn select-all-btn" onclick="selectAllGroups()">全选分组</button>
                    <div id="groupCheckboxes"></div>
                </div>
                
                <div class="control-section">
                    <h4>📏 当前内边距</h4>
                    <div class="slider-container">
                        <span class="slider-label">水平:</span>
                        <input type="range" class="slider" id="paddingX" min="0" max="100" value="25">
                        <span class="slider-value" id="paddingXValue">25px</span>
                    </div>
                    <div class="slider-container">
                        <span class="slider-label">垂直:</span>
                        <input type="range" class="slider" id="paddingY" min="0" max="80" value="20">
                        <span class="slider-value" id="paddingYValue">20px</span>
                    </div>
                    <button class="control-btn reset-btn" onclick="resetPadding()">重置当前</button>
                </div>
                
                <div class="btn-row">
                    <button class="control-btn" onclick="fitNetwork()">适应</button>
                    <button class="control-btn" onclick="resetZoom()">重置</button>
                    <button class="control-btn" onclick="toggleAllSubgraphs()">切换</button>
                    <button class="control-btn" onclick="togglePhysics()">物理</button>
                </div>
                
                <button class="control-btn" onclick="exportImage()">导出图片</button>
            </div>
        </div>
        
        <button class="toolbar-toggle" id="toolbarToggle" onclick="toggleToolbar()">
            <span class="toggle-icon">◀</span>
            <span class="toggle-text">工具栏</span>
        </button>
    </div>

    <div class="legend">
        <div style="font-weight: bold; margin-bottom: 8px; color: #495057;">图例说明</div>
        <div class="legend-item">
            <div class="legend-color" style="background: #0d47a1; border-color: #0d47a1;"></div>
            <span>实际控制人</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #fff8e1; border-color: #ff9100;"></div>
            <span>核心公司</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #e8f5e9; border-color: #4caf50;"></div>
            <span>个人股东</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #ffffff; border-color: #1976d2;"></div>
            <span>公司实体</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(40, 167, 69, 0.1); border-color: #28a745;"></div>
            <span>分组框</span>
        </div>
    </div>
    
    <script type="text/javascript">
        // 数据
        const nodes = new vis.DataSet({nodes_json});
        const edges = new vis.DataSet({edges_json});
        const subgraphs = {subgraphs_json};
        
        let subgraphBoxes = [];
        let animationFrameId = null;
        let groupVisibility = {{}};
        let toolbarExpanded = false;
        
        // 内边距设置
        let paddingX = 25;
        let paddingY = 20;
        
        // 初始化分组可见性
        subgraphs.forEach((subgraph, index) => {{
            groupVisibility[subgraph.id] = true;
        }});
        
        // 🔥 优化：简化的网络配置，更接近Mermaid的自动布局方式
        const options = {{
            layout: {{
                hierarchical: {{
                    enabled: true,
                    direction: 'UD',
                    sortMethod: 'directed',
                    levelSeparation: {level_separation},  // 使用传入的层级间距参数
                    nodeSpacing: {node_spacing},      // 使用传入的节点间距参数
                    treeSpacing: {tree_spacing},
                    blockShifting: true,
                    edgeMinimization: true,
                    parentCentralization: true,
                    shakeTowards: 'leaves',  // 向叶子节点方向调整，减少交叉
                    avoidOverlap: true  // 避免节点重叠
                }}
            }},
            physics: {{
                enabled: false,  // 🔥 关键：禁用物理引擎，使用纯层级布局（类似Mermaid）
                stabilization: {{
                    enabled: false,  // 🔥 关键：禁用稳定化，使用固定布局
                    iterations: 0,
                    updateInterval: 0,
                    onlyDynamicEdges: false,
                    fit: true
                }}
            }},
            interaction: {{
                dragNodes: true,
                dragView: true,
                zoomView: true,
                hover: true,
                keyboard: {{
                    enabled: true,
                    speed: {{x: 10, y: 10, zoom: 0.02}},
                    bindToWindow: true
                }}
            }},
            nodes: {{
                font: {{
                    size: 13,
                    color: '#212529',
                    multi: 'html'
                }},
                borderWidth: 2,
                margin: 8,
                shape: 'box',
                widthConstraint: {{
                    minimum: 160,
                    maximum: 200
                }},
                heightConstraint: {{
                    minimum: 50
                }},
                shadow: false
            }},
            edges: {{
                font: {{
                    size: 12,  // 🔥 减小全局字体大小
                    align: 'horizontal',  // 🔥 水平对齐，更容易阅读
                    background: 'rgba(255, 255, 255, 0.95)',  // 🔥 更不透明的背景
                    strokeWidth: 1,  // 🔥 减少描边宽度
                    strokeColor: 'rgba(0, 0, 0, 0.1)',  // 🔥 淡色描边
                    color: '#000000',
                    bold: true,
                    multi: 'html'  // 🔥 支持HTML格式
                }},
                color: {{
                    color: '#1976d2',  // 🔥 使用蓝色作为默认颜色
                    highlight: '#0d47a1'
                }},
                width: 2,  // 🔥 适中的线条粗细
                arrows: {{
                    to: {{
                        enabled: true,
                        scaleFactor: 0.6,  // 🔥 缩小全局箭头大小
                        type: 'arrow'
                    }}
                }},
                smooth: {{
                    type: 'straight',  // 🔥 使用直线，符合专业股权结构图标准
                    enabled: true
                }},
                selectionWidth: 3,  // 🔥 适中的选中线条粗细
                hoverWidth: 3  // 🔥 适中的悬停线条粗细
            }}
        }};
        
        // 创建网络
        const container = document.getElementById('network-container');
        const network = new vis.Network(container, {{nodes, edges}}, options);
        
        // 切换工具栏
        function toggleToolbar() {{
            toolbarExpanded = !toolbarExpanded;
            const panel = document.getElementById('toolbarPanel');
            const toggle = document.getElementById('toolbarToggle');
            
            if (toolbarExpanded) {{
                panel.classList.remove('collapsed');
                panel.classList.add('expanded');
                toggle.classList.remove('collapsed');
                toggle.querySelector('.toggle-text').textContent = '收起';
            }} else {{
                panel.classList.remove('expanded');
                panel.classList.add('collapsed');
                toggle.classList.add('collapsed');
                toggle.querySelector('.toggle-text').textContent = '工具栏';
            }}
        }}
        
        // 创建分组选择复选框
        function createGroupCheckboxes() {{
            const container = document.getElementById('groupCheckboxes');
            container.innerHTML = '';
            
            subgraphs.forEach((subgraph, index) => {{
                const checkboxContainer = document.createElement('div');
                checkboxContainer.className = 'checkbox-container';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `group-${{subgraph.id}}`;
                checkbox.checked = groupVisibility[subgraph.id];
                checkbox.addEventListener('change', function() {{
                    groupVisibility[subgraph.id] = this.checked;
                    updateSubgraphPositions();
                }});
                
                const label = document.createElement('label');
                label.htmlFor = `group-${{subgraph.id}}`;
                label.textContent = subgraph.label || `分组 ${{index + 1}}`;
                
                const colorBox = document.createElement('div');
                colorBox.className = 'subgraph-color';
                colorBox.style.backgroundColor = subgraph.color || 'rgba(108, 117, 125, 0.1)';
                colorBox.style.borderColor = subgraph.borderColor || '#6c757d';
                
                checkboxContainer.appendChild(checkbox);
                checkboxContainer.appendChild(label);
                checkboxContainer.appendChild(colorBox);
                container.appendChild(checkboxContainer);
            }});
        }}
        
        // 全选分组
        function selectAllGroups() {{
            subgraphs.forEach(subgraph => {{
                groupVisibility[subgraph.id] = true;
                document.getElementById(`group-${{subgraph.id}}`).checked = true;
            }});
            updateSubgraphPositions();
        }}
        
        // 更新分组框位置
        function updateSubgraphPositions() {{
            subgraphs.forEach((subgraph, index) => {{
                if (!groupVisibility[subgraph.id]) {{
                    let box = subgraphBoxes[index];
                    if (box) {{
                        box.style.display = 'none';
                    }}
                    return;
                }}
                
                if (subgraph.nodes && subgraph.nodes.length > 0) {{
                    const positions = [];
                    subgraph.nodes.forEach(nodeId => {{
                        const nodePos = network.getPositions([nodeId])[nodeId];
                        if (nodePos) {{
                            const node = nodes.get(nodeId);
                            const nodeWidth = node.widthConstraint ? node.widthConstraint.maximum || 200 : 200;
                            const nodeHeight = node.heightConstraint ? node.heightConstraint.minimum || 50 : 50;
                            
                            positions.push({{
                                x: nodePos.x,
                                y: nodePos.y,
                                width: nodeWidth,
                                height: nodeHeight
                            }});
                        }}
                    }});
                    
                    if (positions.length > 0) {{
                        const minX = Math.min(...positions.map(p => p.x - p.width/2));
                        const maxX = Math.max(...positions.map(p => p.x + p.width/2));
                        const minY = Math.min(...positions.map(p => p.y - p.height/2));
                        const maxY = Math.max(...positions.map(p => p.y + p.height/2));
                        
                        const finalMinX = minX - paddingX;
                        const finalMaxX = maxX + paddingX;
                        const finalMinY = minY - paddingY;
                        const finalMaxY = maxY + paddingY;
                        
                        let box = subgraphBoxes[index];
                        if (!box) {{
                            box = document.createElement('div');
                            box.className = 'subgraph-box';
                            box.style.borderColor = subgraph.borderColor || '#6c757d';
                            
                            const label = document.createElement('div');
                            label.className = 'subgraph-label';
                            label.textContent = subgraph.label || '分组';
                            label.style.borderColor = subgraph.borderColor || '#6c757d';
                            label.style.color = subgraph.borderColor || '#6c757d';
                            box.appendChild(label);
                            
                            container.appendChild(box);
                            subgraphBoxes[index] = box;
                        }}
                        
                        const containerRect = container.getBoundingClientRect();
                        const scale = network.getScale();
                        const view = network.getViewPosition();
                        
                        box.style.left = (finalMinX * scale + view.x + containerRect.width / 2) + 'px';
                        box.style.top = (finalMinY * scale + view.y + containerRect.height / 2) + 'px';
                        box.style.width = ((finalMaxX - finalMinX) * scale) + 'px';
                        box.style.height = ((finalMaxY - finalMinY) * scale) + 'px';
                        box.style.display = 'block';
                    }}
                }}
            }});
        }}
        
        // 启动动态更新
        function startDynamicUpdate() {{
            if (animationFrameId) {{
                cancelAnimationFrame(animationFrameId);
            }}
            
            function update() {{
                updateSubgraphPositions();
                animationFrameId = requestAnimationFrame(update);
            }}
            
            update();
        }}
        
        // 停止动态更新
        function stopDynamicUpdate() {{
            if (animationFrameId) {{
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
            }}
        }}
        
        // 滑块事件处理
        function setupSliders() {{
            const defaultPaddingXSlider = document.getElementById('defaultPaddingX');
            const defaultPaddingYSlider = document.getElementById('defaultPaddingY');
            const defaultPaddingXValue = document.getElementById('defaultPaddingXValue');
            const defaultPaddingYValue = document.getElementById('defaultPaddingYValue');
            
            defaultPaddingXSlider.addEventListener('input', function() {{
                paddingX = parseInt(this.value);
                defaultPaddingXValue.textContent = paddingX + 'px';
                document.getElementById('paddingX').value = paddingX;
                document.getElementById('paddingXValue').textContent = paddingX + 'px';
                updateSubgraphPositions();
            }});
            
            defaultPaddingYSlider.addEventListener('input', function() {{
                paddingY = parseInt(this.value);
                defaultPaddingYValue.textContent = paddingY + 'px';
                document.getElementById('paddingY').value = paddingY;
                document.getElementById('paddingYValue').textContent = paddingY + 'px';
                updateSubgraphPositions();
            }});
            
            const paddingXSlider = document.getElementById('paddingX');
            const paddingYSlider = document.getElementById('paddingY');
            const paddingXValue = document.getElementById('paddingXValue');
            const paddingYValue = document.getElementById('paddingYValue');
            
            paddingXSlider.addEventListener('input', function() {{
                paddingX = parseInt(this.value);
                paddingXValue.textContent = paddingX + 'px';
                updateSubgraphPositions();
            }});
            
            paddingYSlider.addEventListener('input', function() {{
                paddingY = parseInt(this.value);
                paddingYValue.textContent = paddingY + 'px';
                updateSubgraphPositions();
            }});
        }}
        
        // 重置默认内边距
        function resetDefaultPadding() {{
            paddingX = 25;
            paddingY = 20;
            
            document.getElementById('defaultPaddingX').value = paddingX;
            document.getElementById('defaultPaddingY').value = paddingY;
            document.getElementById('defaultPaddingXValue').textContent = paddingX + 'px';
            document.getElementById('defaultPaddingYValue').textContent = paddingY + 'px';
            
            document.getElementById('paddingX').value = paddingX;
            document.getElementById('paddingY').value = paddingY;
            document.getElementById('paddingXValue').textContent = paddingX + 'px';
            document.getElementById('paddingYValue').textContent = paddingY + 'px';
            
            updateSubgraphPositions();
        }}
        
        // 重置当前内边距
        function resetPadding() {{
            paddingX = 25;
            paddingY = 20;
            
            document.getElementById('paddingX').value = paddingX;
            document.getElementById('paddingY').value = paddingY;
            document.getElementById('paddingXValue').textContent = paddingX + 'px';
            document.getElementById('paddingYValue').textContent = paddingY + 'px';
            
            updateSubgraphPositions();
        }}
        
        // 切换所有分组
        function toggleAllSubgraphs() {{
            const allVisible = Object.values(groupVisibility).every(v => v);
            const newState = !allVisible;
            
            subgraphs.forEach(subgraph => {{
                groupVisibility[subgraph.id] = newState;
                document.getElementById(`group-${{subgraph.id}}`).checked = newState;
            }});
            
            updateSubgraphPositions();
        }}
        
        // 网络事件
        network.on('stabilizationIterationsDone', function() {{
            startDynamicUpdate();
        }});
        
        network.on('afterDrawing', function() {{
            updateSubgraphPositions();
        }});
        
        network.on('dragStart', function() {{
            startDynamicUpdate();
        }});
        
        network.on('zoom', function() {{
            updateSubgraphPositions();
        }});
        
        network.on('dragEnd', function() {{
            updateSubgraphPositions();
        }});
        
        // 控制函数
        function fitNetwork() {{
            network.fit();
            setTimeout(updateSubgraphPositions, 200);
        }}
        
        function resetZoom() {{
            network.moveTo({{scale: 1}});
            setTimeout(updateSubgraphPositions, 200);
        }}
        
        function togglePhysics() {{
            const physics = network.getOptions().physics.enabled;
            network.setOptions({{physics: {{enabled: !physics}}}});
        }}
        
        function exportImage() {{
            const canvas = network.getCanvas();
            const link = document.createElement('a');
            link.download = 'equity_structure.png';
            link.href = canvas.toDataURL('image/png', 1.0);
            link.click();
        }}
        
        // 节点点击事件
        network.on('selectNode', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                console.log('Selected node:', node.label);
            }}
        }});
        
        // 页面卸载时清理
        window.addEventListener('beforeunload', function() {{
            stopDynamicUpdate();
        }});
        
        // 初始化
        createGroupCheckboxes();
        setupSliders();
        setTimeout(() => {{
            startDynamicUpdate();
        }}, 1000);
    </script>
</body>
</html>
"""
    return html_template


def generate_fullscreen_visjs_html(nodes: List[Dict], edges: List[Dict], 
                                 level_separation: int = 150,
                                 node_spacing: int = 200,
                                 tree_spacing: int = 200,
                                 subgraphs: List[Dict] = None) -> str:
    """
    生成全屏模式的 vis.js 图表 HTML
    
    Args:
        nodes: vis.js 节点列表
        edges: vis.js 边列表
        level_separation: 层级间距（上下间距）
        node_spacing: 节点间距（左右间距）
        tree_spacing: 树间距
        subgraphs: 分组配置列表
    
    Returns:
        str: 全屏模式的完整 HTML 代码
    """
    return generate_visjs_html(nodes, edges, height="100vh", enable_physics=False,
                              level_separation=level_separation,
                              node_spacing=node_spacing,
                              tree_spacing=tree_spacing,
                              subgraphs=subgraphs)