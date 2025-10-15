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
    
    def _compose_display_label(entity: Dict[str, Any]) -> str:
        name = entity.get("name", "")
        reg_capital = entity.get("registration_capital") or entity.get("registered_capital")
        est_date = entity.get("establishment_date") or entity.get("established_date")
        extras = []
        if reg_capital:
            extras.append(f"Registration Captial {reg_capital}")
        if est_date:
            extras.append(f"Establishment Date {est_date}")
        return (name + (" " + " ".join(extras) if extras else "")).strip()

    # 预计算被引用的实体名称（用于过滤孤立/测试实体）
    referenced_names = set()
    for rel in equity_data.get("entity_relationships", []):
        parent = rel.get("from", rel.get("parent", ""))
        child = rel.get("to", rel.get("child", ""))
        if parent:
            referenced_names.add(parent)
        if child:
            referenced_names.add(child)
    # 顶级实体/子公司/核心公司/实控人也属于有效引用
    referenced_names.update([e.get("name", "") for e in equity_data.get("top_level_entities", [])])
    referenced_names.update([s.get("name", "") for s in equity_data.get("subsidiaries", [])])
    if core_company:
        referenced_names.add(core_company)
    if actual_controller:
        referenced_names.add(actual_controller)

    # 创建节点（去重并过滤未引用实体）
    for entity in all_entities:
        entity_name = entity.get("name", "")
        entity_type = entity.get("type", "company")
        
        if not entity_name:
            continue
        # 去重：如果该名称已创建节点则跳过
        if entity_name in node_id_map:
            continue
        # 过滤：未被任何关系/步骤引用且不是核心公司/实控人的实体（如测试值 abcd）
        if entity_name not in referenced_names:
            continue
        
        # 确定节点样式
        node_style = _get_node_style(entity_name, entity_type, core_company, actual_controller)
        
        display_label = _compose_display_label(entity)
        node = {
            "id": node_counter,
            "label": display_label,
            "shape": "box",
            "widthConstraint": {"minimum": 170, "maximum": 170},  # 固定宽度170px
            "heightConstraint": {"minimum": 60},   # 固定高度60px
            "font": {
                "size": 14,
                "color": node_style["font_color"],
                "multi": "html"
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
    
    # 🔥 优化：为同层节点添加智能排序和x坐标提示
    _optimize_node_positions(nodes, equity_data)
    
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
                    "multi": "html"  # 🔥 支持HTML格式
                },
                "color": {"color": "#1976d2", "highlight": "#0d47a1"},  # 🔥 使用蓝色，更专业
                "width": 2,  # 🔥 适中的线条粗细
                "smooth": {
                    "type": "continuous",  # 🔥 使用连续线条，符合专业股权结构图标准
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
                    "multi": "html"  # 🔥 支持HTML格式
                },
                "color": {"color": "#d32f2f", "highlight": "#b71c1c"},  # 🔥 使用红色，表示控制关系
                "width": 1.5,  # 🔥 虚线稍微细一点，与实线视觉保持一致
                "dashes": [5, 5],  # 虚线
                "smooth": {
                    "type": "continuous",  # 🔥 使用连续线条，符合专业股权结构图标准
                    "enabled": True
                }
            }
            edges.append(edge)
    
    return nodes, edges


def _calculate_node_importance(entity_name: str, equity_data: Dict[str, Any]) -> Tuple[float, int]:
    """
    计算节点重要性，用于排序
    返回: (持股比例, 子节点数量)
    """
    # 查找该节点作为父节点的所有关系
    relationships = equity_data.get('entity_relationships', [])
    total_percentage = 0
    child_count = 0
    
    for rel in relationships:
        if rel.get('from', rel.get('parent', '')) == entity_name:
            total_percentage += rel.get('percentage', 0)
            child_count += 1
    
    return (total_percentage, child_count)


def _optimize_node_positions(nodes: List[Dict], equity_data: Dict[str, Any]) -> None:
    """
    为同层节点添加智能排序和x坐标提示，减少连线交叉
    考虑上下层节点对应关系，实现更智能的布局
    """
    # 按层级分组节点
    level_nodes = {}  # {level: [nodes]}
    for node in nodes:
        level = node.get('level', 0)
        if level not in level_nodes:
            level_nodes[level] = []
        level_nodes[level].append(node)
    
    # 获取所有关系，用于分析上下层连接
    relationships = equity_data.get('entity_relationships', [])
    
    # 从最底层开始，逐层向上优化
    sorted_levels = sorted(level_nodes.keys(), reverse=True)  # 从最底层开始
    
    for level in sorted_levels:
        level_node_list = level_nodes[level]
        if len(level_node_list) <= 1:
            continue
        
        # 检查下一层（更深的层级）的节点分布
        next_level = level - 1
        next_level_nodes = level_nodes.get(next_level, [])
        
        if len(next_level_nodes) >= 2 and len(level_node_list) >= 4:
            # 🔥 关键优化：考虑下一层节点分布，智能排序当前层
            _smart_sort_by_child_distribution(level_node_list, next_level_nodes, relationships)
        else:
            # 简单排序：按持股比例和重要性
            _simple_sort_by_importance(level_node_list, equity_data)
        
        # 设置x坐标
        _set_node_x_positions(level_node_list)


def _smart_sort_by_child_distribution(parent_nodes: List[Dict], child_nodes: List[Dict], 
                                    relationships: List[Dict]) -> None:
    """
    根据子节点分布智能排序父节点，减少连线交叉
    """
    # 分析每个父节点的子节点分布
    parent_child_mapping = {}  # {parent_node_id: [child_nodes]}
    
    for parent_node in parent_nodes:
        parent_label = parent_node.get('label', '')
        parent_name = parent_label.split('<br>')[0].strip() if '<br>' in parent_label else parent_label.strip()
        parent_id = parent_node.get('id')
        
        # 找到该父节点的所有子节点
        children = []
        for rel in relationships:
            if rel.get('from', rel.get('parent', '')) == parent_name:
                child_name = rel.get('to', rel.get('child', ''))
                # 在child_nodes中找到对应的节点
                for child_node in child_nodes:
                    child_label = child_node.get('label', '')
                    child_node_name = child_label.split('<br>')[0].strip() if '<br>' in child_label else child_label.strip()
                    if child_node_name == child_name:
                        children.append(child_node)
                        break
        
        parent_child_mapping[parent_id] = children
    
    # 计算子节点的平均x坐标
    child_x_positions = {}
    for child_node in child_nodes:
        child_x_positions[child_node.get('id')] = child_node.get('x', 0)
    
    # 根据子节点分布排序父节点
    def sort_key(parent_node):
        parent_id = parent_node.get('id')
        children = parent_child_mapping.get(parent_id, [])
        if not children:
            # 没有子节点，按持股比例排序
            return (0, -_get_node_percentage(parent_node))
        
        # 计算子节点的平均x坐标
        child_ids = [child.get('id') for child in children]
        avg_child_x = sum(child_x_positions.get(child_id, 0) for child_id in child_ids) / len(child_ids)
        return (avg_child_x, -_get_node_percentage(parent_node))
    
    parent_nodes.sort(key=sort_key)


def _simple_sort_by_importance(nodes: List[Dict], equity_data: Dict[str, Any]) -> None:
    """
    简单按重要性排序节点
    """
    def sort_key(node):
        label = node.get('label', '')
        entity_name = label.split('<br>')[0].strip() if '<br>' in label else label.strip()
        
        total_percentage, child_count = _calculate_node_importance(entity_name, equity_data)
        node_type = 'person' if 'person' in str(node.get('color', {})) else 'company'
        
        return (-total_percentage, node_type == 'person', -child_count)
    
    nodes.sort(key=sort_key)


def _set_node_x_positions(nodes: List[Dict]) -> None:
    """
    为节点设置x坐标
    """
    spacing = 300
    start_x = -(len(nodes) - 1) * spacing / 2
    
    for i, node in enumerate(nodes):
        node['x'] = start_x + i * spacing
        node['fixed'] = {'x': False, 'y': False}  # 允许微调，不固定位置


def _get_node_percentage(node: Dict) -> float:
    """
    获取节点的持股比例
    """
    # 从节点标签中提取百分比信息
    label = node.get('label', '')
    
    # 尝试从标签中提取百分比（如果有显示的话）
    import re
    percentage_match = re.search(r'(\d+(?:\.\d+)?)%', label)
    if percentage_match:
        return float(percentage_match.group(1))
    
    # 如果没有找到百分比，返回0
    return 0.0


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
    修复层级计算逻辑，确保父节点在子节点的上一层
    
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
    
    # 🔥 修复层级计算逻辑：使用迭代算法，确保所有关系都正确处理
    # 从核心公司开始，逐层向上追溯所有父节点
    from collections import deque
    
    # 创建反向关系映射：child -> [parents]
    reverse_relationships = {}
    for rel in all_relationships:
        parent_entity = rel.get("parent", rel.get("from", ""))
        child_entity = rel.get("child", rel.get("to", ""))
        
        if parent_entity and child_entity:
            if child_entity not in reverse_relationships:
                reverse_relationships[child_entity] = []
            reverse_relationships[child_entity].append(parent_entity)
    
    # 🔥 关键修复：使用迭代算法，确保所有层级都正确计算
    max_iterations = 10  # 防止无限循环
    iteration = 0
    
    while iteration < max_iterations:
        changed = False
        
        # 遍历所有关系，确保父节点层级 < 子节点层级
        for rel in all_relationships:
            parent_entity = rel.get("parent", rel.get("from", ""))
            child_entity = rel.get("child", rel.get("to", ""))
            
            if parent_entity and child_entity:
                # 如果子节点有层级，父节点层级应该更小（更负）
                if child_entity in entity_levels:
                    child_level = entity_levels[child_entity]
                    parent_level = entity_levels.get(parent_entity, child_level - 1)
                    
                    # 确保父节点层级 < 子节点层级
                    if parent_level >= child_level:
                        entity_levels[parent_entity] = child_level - 1
                        changed = True
                    elif parent_entity not in entity_levels:
                        entity_levels[parent_entity] = child_level - 1
                        changed = True
        
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
                # 未连接的实体默认为最高层级（负数）
                entity_levels[entity_name] = -10
    
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
                        subgraphs: List[Dict] = None,
                        page_title: str = "交互式HTML股权结构图") -> str:
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
        page_title: 页面标题
    
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
    <title>{page_title}</title>
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
            max-height: calc(100vh - 100px);
            overflow-y: auto;
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
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .subgraph-label:hover {{
            background: #f8f9fa;
            transform: scale(1.05);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
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
        
        .legend-color.dashed {{
            border-style: dashed;
        }}
        
        /* 节点大小调整手柄样式 */
        .resize-handle {{
            position: absolute;
            width: 8px;
            height: 8px;
            background: #2196f3;
            border: 1px solid white;
            border-radius: 2px;
            cursor: pointer;
            z-index: 1001;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            transition: all 0.2s ease;
        }}
        
        .resize-handle:hover {{
            background: #1976d2;
            transform: scale(1.2);
        }}
        
        /* 不同方向的鼠标光标（4个角落手柄） */
        .resize-handle.top-left,
        .resize-handle.bottom-right {{
            cursor: nw-resize;
        }}
        
        .resize-handle.top-right,
        .resize-handle.bottom-left {{
            cursor: ne-resize;
        }}
        
        /* 调整状态时的样式 */
        .resizing {{
            user-select: none;
        }}
        
        .resizing .resize-handle {{
            background: #ff5722;
        }}
        
        /* 节点选中时的样式 */
        .node-selected {{
            outline: 2px solid #2196f3;
            outline-offset: 2px;
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
        <div class="toolbar-panel collapsed" id="toolbarPanel">
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
                
                <div class="btn-row">
                    <button class="control-btn reset-btn" onclick="resetAllNodeSizes()">重置所有节点</button>
                </div>
                
                <div class="control-section">
                    <h4>📏 全局节点尺寸</h4>
                    <div class="slider-container">
                        <span class="slider-label">宽度:</span>
                        <input type="range" class="slider" id="globalWidthSlider" min="120" max="400" value="170">
                        <span class="slider-value" id="globalWidthValue">170px</span>
                    </div>
                    <div class="slider-container">
                        <span class="slider-label">高度:</span>
                        <input type="range" class="slider" id="globalHeightSlider" min="40" max="120" value="60">
                        <span class="slider-value" id="globalHeightValue">60px</span>
                    </div>
                    <button class="control-btn" onclick="applyGlobalNodeSize()">应用全局尺寸</button>
                </div>
                
                <div class="control-section">
                    <h4>📝 操作说明</h4>
                    <div style="font-size: 11px; color: #6c757d; line-height: 1.4;">
                        <strong>节点调整：</strong><br>
                        • 使用上方滑块调整所有节点尺寸<br>
                        • 点击节点选中，出现4个调整手柄<br>
                        • 拖拽角落手柄调整单个节点<br>
                        • 双击节点重置该节点尺寸<br>
                        • 点击空白区域取消选中<br><br>
                        <strong>分组编辑：</strong><br>
                        • 双击分组标签可编辑分组名称<br>
                        • 修改后自动保存并更新显示
                    </div>
                </div>
                
                <button class="control-btn" onclick="exportImage()">导出图片</button>
            </div>
        </div>
        
        <button class="toolbar-toggle collapsed" id="toolbarToggle" onclick="toggleToolbar()">
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
            <div class="legend-color dashed" style="background: transparent; border-color: #28a745;"></div>
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
        
        // 节点大小调整相关变量
        let resizeHandles = [];
        let resizingNode = null;
        let resizeHandle = null;
        let startX = 0;
        let startY = 0;
        let originalWidth = 0;
        let originalHeight = 0;
        let isResizing = false;
        
        // localStorage 存储键
        const NODE_SIZE_STORAGE_KEY = 'visjs_nodeCustomSizes';
        const GLOBAL_NODE_SIZE_KEY = 'visjs_globalNodeSize';
        
        // 全局节点尺寸设置
        let globalNodeWidth = 170;
        let globalNodeHeight = 60;
        
        // 保存节点尺寸到localStorage
        function saveNodeSize(nodeId, width, height) {{
            const savedSizes = getSavedSizes();
            savedSizes[nodeId] = {{ width, height }};
            localStorage.setItem(NODE_SIZE_STORAGE_KEY, JSON.stringify(savedSizes));
            console.log(`保存节点 ${{nodeId}} 尺寸: ${{width}}x${{height}}`);
        }}
        
        // 从localStorage读取节点尺寸
        function getSavedSizes() {{
            const saved = localStorage.getItem(NODE_SIZE_STORAGE_KEY);
            return saved ? JSON.parse(saved) : {{}};
        }}
        
        // 加载已保存的节点尺寸
        function loadSavedSizes() {{
            const savedSizes = getSavedSizes();
            const updates = [];
            
            nodes.forEach(node => {{
                if (savedSizes[node.id]) {{
                    const {{ width, height }} = savedSizes[node.id];
                    updates.push({{
                        id: node.id,
                        widthConstraint: {{ 
                            minimum: Math.max(100, width - 50), 
                            maximum: width + 50 
                        }},
                        heightConstraint: {{ 
                            minimum: Math.max(40, height - 20) 
                        }}
                    }});
                    console.log(`加载节点 ${{node.id}} 尺寸: ${{width}}x${{height}}`);
                }}
            }});
            
            if (updates.length > 0) {{
                nodes.update(updates);
            }}
        }}
        
        // 重置所有节点尺寸
        function resetAllNodeSizes() {{
            localStorage.removeItem(NODE_SIZE_STORAGE_KEY);
            applyGlobalNodeSize();
            removeResizeHandles();
            console.log('已重置所有节点尺寸');
        }}
        
        // 重置单个节点尺寸
        function resetSingleNodeSize(nodeId) {{
            const savedSizes = getSavedSizes();
            delete savedSizes[nodeId];
            localStorage.setItem(NODE_SIZE_STORAGE_KEY, JSON.stringify(savedSizes));
            
            nodes.update([{{
                id: nodeId,
                widthConstraint: {{ minimum: globalNodeWidth, maximum: globalNodeWidth }},
                heightConstraint: {{ minimum: globalNodeHeight, maximum: globalNodeHeight }}
            }}]);
            
            console.log(`已重置节点 ${{nodeId}} 的尺寸`);
        }}
        
        // 应用全局节点尺寸
        function applyGlobalNodeSize() {{
            const updates = [];
            nodes.forEach(node => {{
                updates.push({{
                    id: node.id,
                    widthConstraint: {{ minimum: globalNodeWidth, maximum: globalNodeWidth }},
                    heightConstraint: {{ minimum: globalNodeHeight, maximum: globalNodeHeight }}
                }});
            }});
            nodes.update(updates);
            
            // 保存全局尺寸设置
            localStorage.setItem(GLOBAL_NODE_SIZE_KEY, JSON.stringify({{
                width: globalNodeWidth,
                height: globalNodeHeight
            }}));
            
            console.log(`已应用全局节点尺寸: ${{globalNodeWidth}}x${{globalNodeHeight}}`);
        }}
        
        // 加载全局节点尺寸设置
        function loadGlobalNodeSize() {{
            const saved = localStorage.getItem(GLOBAL_NODE_SIZE_KEY);
            if (saved) {{
                const {{ width, height }} = JSON.parse(saved);
                globalNodeWidth = width;
                globalNodeHeight = height;
                
                // 更新滑块值
                document.getElementById('globalWidthSlider').value = globalNodeWidth;
                document.getElementById('globalHeightSlider').value = globalNodeHeight;
                document.getElementById('globalWidthValue').textContent = globalNodeWidth + 'px';
                document.getElementById('globalHeightValue').textContent = globalNodeHeight + 'px';
                
                console.log(`加载全局节点尺寸: ${{globalNodeWidth}}x${{globalNodeHeight}}`);
            }}
        }}
        
        // 编辑分组标签
        function editSubgraphLabel(subgraphId, currentLabel, subgraphIndex) {{
            console.log(`开始编辑分组标签: ${{subgraphId}}, 当前标签: ${{currentLabel}}, 索引: ${{subgraphIndex}}`);
            const newLabel = prompt('请输入新的分组名称:', currentLabel);
            if (newLabel !== null && newLabel.trim() !== '') {{
                // 更新subgraphs数组中的标签
                subgraphs[subgraphIndex].label = newLabel.trim();
                
                // 更新页面上的标签显示
                const labelElement = document.querySelector(`[data-subgraph-id="${{subgraphId}}"]`);
                if (labelElement) {{
                    labelElement.textContent = newLabel.trim();
                    console.log(`已更新页面标签显示: ${{newLabel.trim()}}`);
                }} else {{
                    console.log(`未找到标签元素: [data-subgraph-id="${{subgraphId}}"]`);
                }}
                
                // 更新工具栏中的复选框标签
                const checkboxLabel = document.querySelector(`label[for="group-${{subgraphId}}"]`);
                if (checkboxLabel) {{
                    checkboxLabel.textContent = newLabel.trim();
                    console.log(`已更新工具栏复选框标签: ${{newLabel.trim()}}`);
                }} else {{
                    console.log(`未找到复选框标签: label[for="group-${{subgraphId}}"]`);
                }}
                
                console.log(`分组 ${{subgraphId}} 标签已更新为: ${{newLabel.trim()}}`);
            }}
        }}
        
        // 创建调整手柄
        function createResizeHandles(nodeId) {{
            removeResizeHandles();
            
            const nodePos = network.getPositions([nodeId])[nodeId];
            if (!nodePos) return;
            
            const node = nodes.get(nodeId);
            const nodeWidth = node.widthConstraint ? node.widthConstraint.maximum || 200 : 200;
            const nodeHeight = node.heightConstraint ? node.heightConstraint.minimum || 60 : 60;
            
            const containerRect = container.getBoundingClientRect();
            const scale = network.getScale();
            const view = network.getViewPosition();
            
            // 计算节点在屏幕上的位置
            const screenX = nodePos.x * scale + view.x + containerRect.width / 2;
            const screenY = nodePos.y * scale + view.y + containerRect.height / 2;
            
            const halfWidth = (nodeWidth * scale) / 2;
            const halfHeight = (nodeHeight * scale) / 2;
            
            // 4个核心调整手柄的位置（只保留角落手柄，避免误操作）
            const handlePositions = [
                {{ class: 'top-left', x: screenX - halfWidth, y: screenY - halfHeight }},
                {{ class: 'top-right', x: screenX + halfWidth, y: screenY - halfHeight }},
                {{ class: 'bottom-right', x: screenX + halfWidth, y: screenY + halfHeight }},
                {{ class: 'bottom-left', x: screenX - halfWidth, y: screenY + halfHeight }}
            ];
            
            handlePositions.forEach(pos => {{
                const handle = document.createElement('div');
                handle.className = `resize-handle ${{pos.class}}`;
                handle.style.left = (pos.x - 4) + 'px';
                handle.style.top = (pos.y - 4) + 'px';
                handle.dataset.direction = pos.class;
                handle.dataset.nodeId = nodeId;
                
                handle.addEventListener('mousedown', startResize);
                container.appendChild(handle);
                resizeHandles.push(handle);
            }});
            
            console.log(`为节点 ${{nodeId}} 创建了 ${{resizeHandles.length}} 个调整手柄`);
        }}
        
        // 移除调整手柄
        function removeResizeHandles() {{
            resizeHandles.forEach(handle => {{
                if (handle.parentNode) {{
                    handle.parentNode.removeChild(handle);
                }}
            }});
            resizeHandles = [];
        }}
        
        // 更新调整手柄位置
        function updateResizeHandles() {{
            if (resizeHandles.length === 0) return;
            
            const nodeId = parseInt(resizeHandles[0].dataset.nodeId);
            const nodePos = network.getPositions([nodeId])[nodeId];
            if (!nodePos) return;
            
            const node = nodes.get(nodeId);
            const nodeWidth = node.widthConstraint ? node.widthConstraint.maximum || 200 : 200;
            const nodeHeight = node.heightConstraint ? node.heightConstraint.minimum || 60 : 60;
            
            const containerRect = container.getBoundingClientRect();
            const scale = network.getScale();
            const view = network.getViewPosition();
            
            const screenX = nodePos.x * scale + view.x + containerRect.width / 2;
            const screenY = nodePos.y * scale + view.y + containerRect.height / 2;
            
            const halfWidth = (nodeWidth * scale) / 2;
            const halfHeight = (nodeHeight * scale) / 2;
            
            const handlePositions = [
                {{ class: 'top-left', x: screenX - halfWidth, y: screenY - halfHeight }},
                {{ class: 'top-right', x: screenX + halfWidth, y: screenY - halfHeight }},
                {{ class: 'bottom-right', x: screenX + halfWidth, y: screenY + halfHeight }},
                {{ class: 'bottom-left', x: screenX - halfWidth, y: screenY + halfHeight }}
            ];
            
            resizeHandles.forEach((handle, index) => {{
                const pos = handlePositions[index];
                handle.style.left = (pos.x - 4) + 'px';
                handle.style.top = (pos.y - 4) + 'px';
            }});
        }}
        
        // 开始调整大小
        function startResize(e) {{
            e.preventDefault();
            e.stopPropagation();
            
            isResizing = true;
            resizingNode = parseInt(e.target.dataset.nodeId);
            resizeHandle = e.target.dataset.direction;
            startX = e.clientX;
            startY = e.clientY;
            
            const node = nodes.get(resizingNode);
            originalWidth = node.widthConstraint ? node.widthConstraint.maximum || 200 : 200;
            originalHeight = node.heightConstraint ? node.heightConstraint.minimum || 60 : 60;
            
            document.body.classList.add('resizing');
            console.log(`开始调整节点 ${{resizingNode}}，方向: ${{resizeHandle}}`);
            
            document.addEventListener('mousemove', handleResize);
            document.addEventListener('mouseup', stopResize);
        }}
        
        // 处理调整大小
        function handleResize(e) {{
            if (!isResizing) return;
            
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            const scale = network.getScale();
            
            let newWidth = originalWidth;
            let newHeight = originalHeight;
            
            // 根据调整手柄方向计算新尺寸（4个角落手柄）
            switch (resizeHandle) {{
                case 'top-left':
                    newWidth = Math.max(100, originalWidth - deltaX / scale);
                    newHeight = Math.max(40, originalHeight - deltaY / scale);
                    break;
                case 'top-right':
                    newWidth = Math.max(100, originalWidth + deltaX / scale);
                    newHeight = Math.max(40, originalHeight - deltaY / scale);
                    break;
                case 'bottom-right':
                    newWidth = Math.max(100, originalWidth + deltaX / scale);
                    newHeight = Math.max(40, originalHeight + deltaY / scale);
                    break;
                case 'bottom-left':
                    newWidth = Math.max(100, originalWidth - deltaX / scale);
                    newHeight = Math.max(40, originalHeight + deltaY / scale);
                    break;
            }}
            
            // 更新节点尺寸
            nodes.update([{{
                id: resizingNode,
                widthConstraint: {{ 
                    minimum: Math.max(100, newWidth - 50), 
                    maximum: newWidth + 50 
                }},
                heightConstraint: {{ 
                    minimum: Math.max(40, newHeight - 20) 
                }}
            }}]);
            
            // 更新调整手柄位置
            updateResizeHandles();
            
            // 更新分组框位置（如果存在）
            if (typeof updateSubgraphPositions === 'function') {{
                updateSubgraphPositions();
            }}
        }}
        
        // 停止调整大小
        function stopResize() {{
            if (!isResizing) return;
            
            isResizing = false;
            document.body.classList.remove('resizing');
            
            // 保存调整后的尺寸
            const node = nodes.get(resizingNode);
            const width = node.widthConstraint ? node.widthConstraint.maximum || 200 : 200;
            const height = node.heightConstraint ? node.heightConstraint.minimum || 60 : 60;
            
            saveNodeSize(resizingNode, width, height);
            
            console.log(`完成调整节点 ${{resizingNode}}，最终尺寸: ${{width}}x${{height}}`);
            
            resizingNode = null;
            resizeHandle = null;
            
            document.removeEventListener('mousemove', handleResize);
            document.removeEventListener('mouseup', stopResize);
        }}
        
        // 初始化分组可见性 - 默认不选中
        subgraphs.forEach((subgraph, index) => {{
            groupVisibility[subgraph.id] = false;
        }});
        
        // 🔥 优化：智能层级布局，减少连线交叉，实现清晰的上-下、左-右结构
        const options = {{
            layout: {{
                hierarchical: {{
                    enabled: true,
                    direction: 'UD',
                    sortMethod: 'hubsize',  // 🔥 改为hubsize，按连接数排序，减少交叉
                    levelSeparation: {level_separation},  // 使用传入的层级间距参数
                    nodeSpacing: {node_spacing},      // 使用传入的节点间距参数
                    treeSpacing: {tree_spacing},
                    blockShifting: true,
                    edgeMinimization: true,
                    parentCentralization: true,
                    shakeTowards: 'leaves'  // 向叶子节点方向调整，减少交叉
                }}
            }},
            physics: {{
                enabled: true,  // 🔥 启用物理引擎用于初始布局优化
                stabilization: {{
                    enabled: true,  // 🔥 启用初始稳定化
                    iterations: 200,  // 🔥 限制迭代次数，避免过度计算
                    updateInterval: 50,
                    onlyDynamicEdges: false,
                    fit: true
                }},
                solver: 'hierarchicalRepulsion',  // 🔥 使用层级排斥算法
                hierarchicalRepulsion: {{
                    centralGravity: 0,
                    springLength: 200,
                    springConstant: 0.01,
                    nodeDistance: 180,
                    damping: 0.09
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
                    minimum: 170,
                    maximum: 170
                }},
                heightConstraint: {{
                    minimum: 60
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
                    type: 'cubicBezier',  // 🔥 使用贝塞尔曲线，更优雅
                    forceDirection: 'vertical',  // 🔥 强制垂直方向，减少交叉
                    roundness: 0.5,  // 🔥 适中的圆滑度
                    enabled: true
                }},
                selectionWidth: 3,  // 🔥 适中的选中线条粗细
                hoverWidth: 3  // 🔥 适中的悬停线条粗细
            }}
        }};
        
        // 创建网络（全局变量，供其他函数使用）
        const container = document.getElementById('network-container');
        window.network = new vis.Network(container, {{nodes, edges}}, options);
        const network = window.network;
        
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
                            label.style.borderColor = subgraph.borderColor || '#6c757d';
                            label.style.color = subgraph.borderColor || '#6c757d';
                            label.dataset.subgraphId = subgraph.id;
                            label.dataset.subgraphIndex = index;
                            label.style.cursor = 'pointer';
                            label.title = '双击编辑分组名称';
                            
                            // 添加双击编辑功能
                            label.addEventListener('dblclick', function(e) {{
                                e.stopPropagation();
                                console.log(`分组标签被双击: ${{subgraph.id}}, 标签: ${{subgraph.label || '分组'}}, 索引: ${{index}}`);
                                editSubgraphLabel(subgraph.id, subgraph.label || '分组', index);
                            }});
                            
                            box.appendChild(label);
                            
                            container.appendChild(box);
                            subgraphBoxes[index] = box;
                        }}
                        
                        // 更新标签文本（确保显示最新的标签内容）
                        const label = box.querySelector('.subgraph-label');
                        if (label) {{
                            label.textContent = subgraph.label || '分组';
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
        
        // 全局节点尺寸滑块事件处理
        function setupGlobalSizeSliders() {{
            const globalWidthSlider = document.getElementById('globalWidthSlider');
            const globalHeightSlider = document.getElementById('globalHeightSlider');
            const globalWidthValue = document.getElementById('globalWidthValue');
            const globalHeightValue = document.getElementById('globalHeightValue');
            
            globalWidthSlider.addEventListener('input', function() {{
                globalNodeWidth = parseInt(this.value);
                globalWidthValue.textContent = globalNodeWidth + 'px';
            }});
            
            globalHeightSlider.addEventListener('input', function() {{
                globalNodeHeight = parseInt(this.value);
                globalHeightValue.textContent = globalNodeHeight + 'px';
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
            // 🔥 稳定化完成后禁用物理引擎，保持固定布局
            network.setOptions({{physics: {{enabled: false}}}});
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
        
        // 手动绘制分组框到canvas（用于导出）
        function drawSubgraphsToCanvas(ctx) {{
            console.log('开始绘制分组框到canvas...');
            
            subgraphs.forEach((subgraph, index) => {{
                if (!groupVisibility[subgraph.id]) {{
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
                        // 计算分组框的边界
                        const minX = Math.min(...positions.map(p => p.x - p.width / 2)) - paddingX;
                        const maxX = Math.max(...positions.map(p => p.x + p.width / 2)) + paddingX;
                        const minY = Math.min(...positions.map(p => p.y - p.height / 2)) - paddingY;
                        const maxY = Math.max(...positions.map(p => p.y + p.height / 2)) + paddingY;
                        
                        // 绘制分组框
                        ctx.save();
                        ctx.strokeStyle = subgraph.borderColor || '#6c757d';
                        ctx.fillStyle = subgraph.color || 'rgba(108, 117, 125, 0.1)';
                        ctx.lineWidth = 2;
                        ctx.setLineDash([5, 5]); // 虚线边框
                        
                        // 绘制矩形框
                        ctx.fillRect(minX, minY, maxX - minX, maxY - minY);
                        ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);
                        
                        // 绘制标签
                        if (subgraph.label) {{
                            ctx.fillStyle = subgraph.borderColor || '#6c757d';
                            ctx.font = '12px Arial';
                            ctx.textAlign = 'left';
                            ctx.fillText(subgraph.label, minX + 5, minY + 15);
                        }}
                        
                        ctx.restore();
                        
                        console.log(`分组框 ${{subgraph.label}} 已绘制到canvas`);
                    }}
                }}
            }});
            
            console.log('分组框绘制完成');
        }}
        
        function exportImage() {{
            try {{
                console.log('开始导出图片...');
                
                // 获取网络对象
                const network = window.network;
                if (!network) {{
                    alert('网络未初始化，请刷新页面重试');
                    console.error('Network is not initialized');
                    return;
                }}
                
                console.log('网络对象获取成功');
                
                // 使用vis.js的正确导出方法
                network.once("afterDrawing", function (ctx) {{
                    try {{
                        console.log('afterDrawing事件触发，开始生成图片...');
                        
                        // 手动绘制分组框到canvas
                        drawSubgraphsToCanvas(ctx);
                        
                        // 获取canvas数据
                        const canvas = ctx.canvas;
                        if (!canvas) {{
                            alert('无法获取画布，请稍后重试');
                            console.error('Canvas is null');
                            return;
                        }}
                        
                        console.log('Canvas获取成功:', canvas);
                        
                        // 创建下载链接
            const link = document.createElement('a');
                        const pageTitle = document.title.replace(' - 交互式HTML股权结构图', '').replace('交互式HTML股权结构图', '股权结构图');
                        const fileName = pageTitle + '_股权结构图.png';
                        
                        console.log('文件名:', fileName);
                        
                        // 转换为图片数据
                        const dataURL = canvas.toDataURL('image/png', 1.0);
                        if (!dataURL || dataURL === 'data:,') {{
                            alert('图片生成失败，请检查图表是否已完全加载');
                            console.error('DataURL is empty');
                            return;
                        }}
                        
                        console.log('图片数据生成成功，大小:', dataURL.length);
                        
                        // 设置下载属性
                        link.download = fileName;
                        link.href = dataURL;
                        
                        // 添加到DOM并触发点击
                        document.body.appendChild(link);
            link.click();
                        document.body.removeChild(link);
                        
                        console.log('图片导出完成');
                        alert('图片导出成功！文件名：' + fileName);
                        
                    }} catch (error) {{
                        console.error('导出图片时发生错误:', error);
                        alert('导出图片失败：' + error.message);
                    }}
                }});
                
                // 触发重绘以激活afterDrawing事件
                network.redraw();
                
            }} catch (error) {{
                console.error('导出图片时发生错误:', error);
                alert('导出图片失败：' + error.message);
            }}
        }}
        
        // 节点点击事件
        network.on('selectNode', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                console.log('Selected node:', node.label);
                
                // 创建调整手柄
                createResizeHandles(nodeId);
            }}
        }});
        
        // 节点双击事件（重置单个节点尺寸）
        network.on('doubleClick', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                if (confirm(`确定要重置节点 "${{node.label}}" 的尺寸吗？`)) {{
                    resetSingleNodeSize(nodeId);
                    // 重新创建手柄以反映新尺寸
                    setTimeout(() => {{
                        createResizeHandles(nodeId);
                    }}, 100);
                }}
            }}
        }});
        
        // 节点取消选中事件
        network.on('deselectNode', function(params) {{
            removeResizeHandles();
            console.log('取消选中节点');
        }});
        
        // 点击空白区域时移除手柄
        network.on('click', function(params) {{
            if (params.nodes.length === 0) {{
                removeResizeHandles();
            }}
        }});
        
        // 网络变化时更新手柄位置
        network.on('afterDrawing', function() {{
            if (resizeHandles.length > 0) {{
                updateResizeHandles();
            }}
        }});
        
        // 页面卸载时清理
        window.addEventListener('beforeunload', function() {{
            stopDynamicUpdate();
        }});
        
        // 初始化
        createGroupCheckboxes();
        setupSliders();
        setupGlobalSizeSliders();
        setTimeout(() => {{
            startDynamicUpdate();
            // 加载已保存的节点尺寸
            loadSavedSizes();
            // 加载全局节点尺寸设置
            loadGlobalNodeSize();
            console.log('节点大小调整功能已加载');
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
                                 subgraphs: List[Dict] = None,
                                 page_title: str = "交互式HTML股权结构图") -> str:
    """
    生成全屏模式的 vis.js 图表 HTML
    
    Args:
        nodes: vis.js 节点列表
        edges: vis.js 边列表
        level_separation: 层级间距（上下间距）
        node_spacing: 节点间距（左右间距）
        tree_spacing: 树间距
        subgraphs: 分组配置列表
        page_title: 页面标题
    
    Returns:
        str: 全屏模式的完整 HTML 代码
    """
    return generate_visjs_html(nodes, edges, height="100vh", enable_physics=False,
                              level_separation=level_separation,
                              node_spacing=node_spacing,
                              tree_spacing=tree_spacing,
                              subgraphs=subgraphs,
                              page_title=page_title)