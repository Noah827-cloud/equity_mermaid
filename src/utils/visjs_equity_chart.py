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
    # 检查是否在调试模式
    try:
        import streamlit as st
        if hasattr(st, 'session_state') and st.session_state.get('debug_mode', False):
            try:
                print(msg)
            except UnicodeEncodeError:
                try:
                    print(msg.encode('ascii', errors='replace').decode('ascii'))
                except:
                    pass
    except:
        pass


def convert_equity_data_to_visjs(equity_data: Dict[str, Any]) -> Tuple[List[Dict], List[Dict], Dict[str, int]]:
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
        lines = []
        
        # 第一行:英文名(如果存在) - 应用格式化
        english_name = entity.get("english_name")
        if english_name:
            try:
                from src.utils.display_formatters import format_english_company_name
                formatted_english_name = format_english_company_name(english_name)
                lines.append(formatted_english_name)
            except Exception:
                # 如果格式化失败，使用原始英文名称
                lines.append(english_name)
        
        # 第二行:中文名
        name = entity.get("name", "")
        lines.append(name)
        
        # 第三行:注册资本(如果存在) - 英文展示: Cap: RMB{X}M
        reg_capital = entity.get("registration_capital") or entity.get("registered_capital")
        if reg_capital:
            try:
                from src.utils.display_formatters import format_registered_capital_display
                formatted_cap = format_registered_capital_display(reg_capital)
                if formatted_cap:
                    lines.append(formatted_cap)
                else:
                    lines.append(f"注册资本 {reg_capital}")
            except Exception:
                lines.append(f"注册资本 {reg_capital}")
        
        # 第四行:成立日期(如果存在) - 英文展示: Established: Month.Year
        est_date = entity.get("establishment_date") or entity.get("established_date")
        if est_date:
            try:
                from src.utils.display_formatters import format_established_display
                formatted_est = format_established_display(est_date)
                if formatted_est:
                    lines.append(formatted_est)
                else:
                    lines.append(f"成立日期 {est_date}")
            except Exception:
                lines.append(f"成立日期 {est_date}")
        
        # 在vis.js中，当multi设置为true时，使用\n作为换行符
        return "\n".join(lines)

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
            "widthConstraint": {"minimum": 100, "maximum": 100},  # 固定宽度100px
            "heightConstraint": {"minimum": 57},   # 固定高度57px
            "font": {
                "size": 12,  # 🔥 减小字体大小，与全局设置一致
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
            "borderWidth": 1,  # 🔥 减小边框宽度，与全局设置一致
            "margin": {  # 🔥 减小内边距，让文字离边框更近
                "top": 4,
                "right": 4,
                "bottom": 4,
                "left": 4
            },
            "level": None,  # 将在后续设置层级
            "isCore": (entity_name == core_company)
        }
        
        node_id_map[entity_name] = node_counter
        nodes.append(node)
        node_counter += 1
    
    # 设置节点层级
    _set_node_levels(nodes, node_id_map, top_level_entities, core_company, equity_data)
    
    # 🔥 优化：为同层节点添加智能排序和x坐标提示
    _optimize_node_positions(nodes, equity_data)
    
    # 获取股权关系数据，将在控制关系处理后再处理
    entity_relationships = equity_data.get("entity_relationships", [])
    
    # 创建边（控制关系）
    control_relationships = equity_data.get("control_relationships", [])
    
    # 🔥 关键修复：控制关系去重，避免重复的边，并记录控制关系对
    seen_control_relationships = set()
    control_pairs = set()  # 记录控制关系对，用于后续过滤股权关系
    
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
            # 记录控制关系对，用于后续过滤股权关系
            control_pairs.add(f"{from_entity}_{to_entity}")
            
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
    
    # 🔥 关键修复：过滤掉与控制关系重复的股权关系
    # 重新处理股权关系，跳过与控制关系重复的关系
    filtered_entity_relationships = []
    for rel in entity_relationships:
        from_entity = rel.get("from", rel.get("parent", ""))
        to_entity = rel.get("to", rel.get("child", ""))
        rel_key = f"{from_entity}_{to_entity}"
        
        # 如果存在控制关系，跳过对应的股权关系
        if rel_key in control_pairs:
            _safe_print(f"跳过与控制关系重复的股权关系: {from_entity} -> {to_entity}")
            continue
        
        filtered_entity_relationships.append(rel)
    
    # 重新创建股权关系边，使用过滤后的关系
    seen_relationships = set()  # 重新定义seen_relationships用于股权关系去重
    for rel in filtered_entity_relationships:
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
    
    return nodes, edges, node_id_map


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
    # 实际控制人 - 深蓝色背景，白色字体（与Mermaid保持一致）
    if entity_name == actual_controller:
        return {
            "bg_color": "#0d47a1",
            "border_color": "#0d47a1",
            "font_color": "#ffffff",
            "highlight_bg": "#1565c0",
            "highlight_border": "#0d47a1"
        }
    
    # 核心公司 - 橙色背景（与Mermaid保持一致）
    if entity_name == core_company:
        return {
            "bg_color": "#fff8e1",
            "border_color": "#ff9100",
            "font_color": "#000000",
            "highlight_bg": "#ffecb3",
            "highlight_border": "#ff6f00"
        }
    
    # 个人 - 绿色背景（与Mermaid保持一致）
    if entity_type == "person" or entity_type == "individual":
        return {
            "bg_color": "#e8f5e9",
            "border_color": "#4caf50",
            "font_color": "#000000",
            "highlight_bg": "#c8e6c9",
            "highlight_border": "#388e3c"
        }
    
    # 政府/机构 - 灰色背景
    if entity_type == "government" or entity_type == "institution":
        return {
            "bg_color": "#f5f5f5",
            "border_color": "#757575",
            "font_color": "#000000",
            "highlight_bg": "#eeeeee",
            "highlight_border": "#616161"
        }
    
    # 普通公司 - 白色背景，蓝色边框（与Mermaid保持一致）
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
    max_iterations = 20  # 防止无限循环（原为10，提升以支持更深股权链）
    iteration = 0
    
    while iteration < max_iterations:
        changed = False
        
        # 遍历所有关系，同时双向收敛：
        # 1) 若已知父层级，则推进子到 parent+1（如子未设或子<=父）
        # 2) 若已知子层级，则推进父到 child-1（如父未设或父>=子）
        for rel in all_relationships:
            parent_entity = rel.get("parent", rel.get("from", ""))
            child_entity = rel.get("child", rel.get("to", ""))
            
            if not parent_entity or not child_entity:
                continue
            
            parent_known = parent_entity in entity_levels
            child_known = child_entity in entity_levels
            
            # 从父向子推进
            if parent_known:
                parent_level = entity_levels[parent_entity]
                desired_child_level = parent_level + 1
                if (not child_known) or (entity_levels[child_entity] <= parent_level):
                    if (not child_known) or (entity_levels[child_entity] != desired_child_level):
                        entity_levels[child_entity] = desired_child_level
                        changed = True
                        child_known = True
            
            # 从子向父推进
            if child_known:
                child_level = entity_levels[child_entity]
                desired_parent_level = child_level - 1
                if (not parent_known) or (entity_levels[parent_entity] >= child_level):
                    if (not parent_known) or (entity_levels[parent_entity] != desired_parent_level):
                        entity_levels[parent_entity] = desired_parent_level
                        changed = True
                        parent_known = True
        
        if not changed:
            break
        iteration += 1

    # 🔧 后处理：将无父节点的股东尽量“贴近”其子节点
    # 仅在该实体没有任何上游父节点时，将其层级提升至(其所有子节点中最小层级 - 1)
    # 这样可避免无父的小股东在没有必要时被置于 -2 或更低层
    forward_relationships = {}
    for rel in all_relationships:
        p = rel.get("parent", rel.get("from", ""))
        c = rel.get("child", rel.get("to", ""))
        if p and c:
            if p not in forward_relationships:
                forward_relationships[p] = []
            forward_relationships[p].append(c)

    for entity_name, level in list(entity_levels.items()):
        parents_of_entity = reverse_relationships.get(entity_name, [])
        has_parents = bool(parents_of_entity)
        if has_parents:
            continue  # 仅调整无父节点的实体

        children = forward_relationships.get(entity_name, [])
        if not children:
            continue

        child_levels = [entity_levels[ch] for ch in children if ch in entity_levels]
        if not child_levels:
            continue

        desired_parent_level = min(child_levels) - 1
        # 若当前更负（更远离子节点），则将其“抬高”至理想位置
        if level < desired_parent_level:
            entity_levels[entity_name] = desired_parent_level
    
    # 为未设置层级的实体设置默认层级
    all_entities = equity_data.get("all_entities", [])
    top_level_entities = equity_data.get("top_level_entities", [])
    
    for entity in all_entities:
        entity_name = entity.get("name", "")
        if entity_name and entity_name not in entity_levels:
            if entity_name == core_company:
                entity_levels[entity_name] = 0  # 核心公司为0
            else:
                # 🔥 改进：检查是否为顶级实体（股东）
                is_top_level = any(tl.get("name") == entity_name for tl in top_level_entities)
                if is_top_level:
                    # 顶级实体（股东）应该有更高的层级（更小的负数）
                    entity_levels[entity_name] = -1
                else:
                    # 其他未连接的实体默认为最高层级（负数）
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
        
        /* 🔥 右键菜单样式 */
        .context-menu {{
            position: absolute;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            padding: 4px 0;
            min-width: 140px;
            z-index: 1000;
            display: none;
            font-size: 12px;
        }}
        
        .context-menu-item {{
            padding: 8px 16px;
            cursor: pointer;
            color: #495057;
            display: flex;
            align-items: center;
            transition: background-color 0.2s;
        }}
        
        .context-menu-item:hover {{
            background-color: #f8f9fa;
        }}
        
        .context-menu-item.danger {{
            color: #dc3545;
        }}
        
        .context-menu-item.danger:hover {{
            background-color: #f8d7da;
        }}
        
        .context-menu-item .icon {{
            margin-right: 8px;
            width: 14px;
            text-align: center;
        }}
        
        .context-menu-separator {{
            height: 1px;
            background-color: #dee2e6;
            margin: 4px 0;
        }}
        
        /* 🔥 隐藏节点列表样式 */
        .hidden-node-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 8px;
            margin: 2px 0;
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            font-size: 11px;
        }}
        
        .hidden-node-item:hover {{
            background: #fff;
            border-color: #007bff;
        }}
        
        .hidden-node-name {{
            flex: 1;
            color: #856404;
            font-weight: 500;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .hidden-node-actions {{
            display: flex;
            gap: 4px;
        }}
        
        .hidden-node-btn {{
            padding: 2px 6px;
            font-size: 10px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            background: #007bff;
            color: white;
            transition: background-color 0.2s;
        }}
        
        .hidden-node-btn:hover {{
            background: #0056b3;
        }}
        
        .hidden-node-btn.danger {{
            background: #dc3545;
        }}
        
        .hidden-node-btn.danger:hover {{
            background: #c82333;
        }}
        
        .hidden-nodes-empty {{
            text-align: center;
            color: #6c757d;
            font-size: 11px;
            padding: 20px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div id="network-container"></div>
    
    <!-- 🔥 右键菜单 - 节点 -->
    <div id="contextMenu" class="context-menu">
        <div class="context-menu-item" id="hideNodeItem">
            <span class="icon">👁️</span>
            隐藏节点
        </div>
        <div class="context-menu-item" id="showHiddenNodesItem" style="display: none;">
            <span class="icon">👁️‍🗨️</span>
            显示隐藏节点
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item danger" id="deleteNodeItem">
            <span class="icon">🗑️</span>
            删除节点
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item" id="resetNodeSizeItem">
            <span class="icon">📏</span>
            重置尺寸
        </div>
        <div class="context-menu-item" id="centerNodeItem">
            <span class="icon">🎯</span>
            居中显示
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item" id="unlockNodeItem">
            <span class="icon">🔓</span>
            解除锁定
        </div>
    </div>
    
    <!-- 🔥 右键菜单 - 连线 -->
    <div id="edgeContextMenu" class="context-menu">
        <div class="context-menu-item" id="hideEdgeItem">
            <span class="icon">👁️</span>
            隐藏连线
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item danger" id="deleteEdgeItem">
            <span class="icon">🗑️</span>
            删除连线
        </div>
    </div>
    
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
                
                <!-- 🔥 隐藏节点管理区域 -->
                <div class="control-section" id="hiddenNodesSection">
                    <h4>👁️ 隐藏节点管理</h4>
                    <div id="hiddenNodesList" style="max-height: 200px; overflow-y: auto; margin-bottom: 10px;">
                        <div class="hidden-nodes-empty">暂无隐藏节点</div>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="showAllHiddenNodes()">显示全部</button>
                        <button class="control-btn" onclick="clearHiddenNodesList()">清空列表</button>
                    </div>
                    <div class="btn-row" style="margin-top: 5px;">
                        <button class="control-btn" onclick="testHideNode()" style="font-size: 10px;">测试隐藏第一个节点</button>
                    </div>
                </div>
                
                <!-- 🔥 隐藏连线管理区域 -->
                <div class="control-section" id="hiddenEdgesSection">
                    <h4>🔗 隐藏连线管理</h4>
                    <div id="hiddenEdgesList" style="max-height: 200px; overflow-y: auto; margin-bottom: 10px;">
                        <div class="hidden-edges-empty">暂无隐藏连线</div>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="showAllHiddenEdges()">显示全部</button>
                        <button class="control-btn" onclick="clearHiddenEdgesList()">清空列表</button>
                    </div>
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
                        <input type="range" class="slider" id="globalWidthSlider" min="80" max="400" value="100">
                        <span class="slider-value" id="globalWidthValue">100px</span>
                    </div>
                    <div class="slider-container">
                        <span class="slider-label">高度:</span>
                        <input type="range" class="slider" id="globalHeightSlider" min="30" max="120" value="57">
                        <span class="slider-value" id="globalHeightValue">57px</span>
                    </div>
                    <button class="control-btn" onclick="applyGlobalNodeSize()">应用全局尺寸</button>
                </div>
                
                <!-- 🔥 新增：字体和边框调整控件 -->
                <div class="control-section">
                    <h4>🔤 字体和边框调整</h4>
                    <div style="font-size: 11px; color: #6c757d; line-height: 1.4; margin-bottom: 8px;">
                        <strong>字体大小：</strong>调整节点内文字大小<br>
                        <strong>边框宽度：</strong>调整节点边框粗细
                    </div>
                    <div class="slider-container">
                        <span class="slider-label">字体大小:</span>
                        <input type="range" class="slider" id="fontSizeSlider" min="8" max="20" value="12">
                        <span class="slider-value" id="fontSizeValue">12px</span>
                    </div>
                    <div class="slider-container">
                        <span class="slider-label">边框宽度:</span>
                        <input type="range" class="slider" id="borderWidthSlider" min="1" max="4" value="1">
                        <span class="slider-value" id="borderWidthValue">1px</span>
                    </div>
                    <button class="control-btn" onclick="applyFontAndBorder()">应用设置</button>
                    <button class="control-btn reset-btn" onclick="resetFontAndBorder()">重置默认</button>
                </div>
                
                <div class="control-section">
                    <h4>📏 层级间距</h4>
                    <div style="font-size: 11px; color: #6c757d; line-height: 1.4; margin-bottom: 8px;">
                        <strong>上下间距：</strong>调整不同层级之间的垂直距离
                    </div>
                    <div class="slider-container">
                        <span class="slider-label">层级间距:</span>
                        <input type="range" class="slider" id="levelSeparationSlider" min="100" max="500" value="{level_separation}">
                        <span class="slider-value" id="levelSeparationValue">{level_separation}px</span>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="applyLevelSpacing()">应用间距</button>
                        <button class="control-btn reset-btn" onclick="resetLevelSpacing()">重置间距</button>
                    </div>
                </div>
                
                <div class="control-section">
                    <h4>🔄 布局模式</h4>
                    <div class="btn-row">
                        <button class="control-btn" id="layoutToggleBtn" onclick="toggleLayout()">切换到自由布局</button>
                    </div>
                    <div style="font-size: 11px; color: #6c757d; line-height: 1.4; margin-top: 8px;">
                        <strong>布局说明：</strong><br>
                        • <strong>层级布局：</strong>节点按层级排列，只能左右移动<br>
                        • <strong>自由布局：</strong>节点可任意拖动到任何位置
                    </div>
                </div>
                
                <div class="control-section">
                    <h4>📍 节点位置控制</h4>
                    <div style="font-size: 11px; color: #6c757d; line-height: 1.4; margin-bottom: 8px;">
                        <strong>操作说明：</strong>点击节点选中，然后使用下方按钮精确移动
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" id="moveUpBtn" onclick="moveNode('up')" disabled>↑ 上移</button>
                        <button class="control-btn" id="moveDownBtn" onclick="moveNode('down')" disabled>↓ 下移</button>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" id="moveLeftBtn" onclick="moveNode('left')" disabled>← 左移</button>
                        <button class="control-btn" id="moveRightBtn" onclick="moveNode('right')" disabled>→ 右移</button>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" id="resetPositionBtn" onclick="resetNodePosition()" disabled>🔄 重置位置</button>
                        <button class="control-btn" onclick="unfixAllNodes()">🔓 解除固定</button>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="redistributeNodes()">📐 智能分布</button>
                        <button class="control-btn" onclick="simpleRedistribute()">📏 简单分布</button>
                        <button class="control-btn" onclick="optimizeLayout()">🎯 智能股权布局</button>
                    </div>
                    <div id="selectedNodeInfo" style="font-size: 11px; color: #6c757d; margin-top: 8px; display: none;">
                        已选中节点: <span id="selectedNodeName"></span>
                    </div>
                </div>
                
                <div class="control-section">
                    <h4>🎨 连线样式</h4>
                    <div style="font-size: 11px; color: #6c757d; line-height: 1.4; margin-bottom: 8px;">
                        <strong>连线风格：</strong>选择不同的连线样式
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="setEdgeStyle('straight')">📏 直线</button>
                        <button class="control-btn" onclick="setEdgeStyle('smooth')">🌊 平滑</button>
                        <button class="control-btn" onclick="setEdgeStyle('dynamic')">⚡ 动态</button>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="setEdgeStyle('continuous')">📈 连续</button>
                        <button class="control-btn" onclick="setEdgeStyle('discrete')">📊 离散</button>
                        <button class="control-btn" onclick="setEdgeStyle('diagonalCross')">❌ 对角交叉</button>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="setEdgeStyle('straightCross')">➕ 直线交叉</button>
                        <button class="control-btn" onclick="setEdgeStyle('horizontal')">➡️ 水平</button>
                        <button class="control-btn" onclick="setEdgeStyle('vertical')">⬇️ 垂直</button>
                    </div>
                </div>
                
                <div class="control-section">
                    <h4>🎨 连线颜色</h4>
                    <div style="font-size: 11px; color: #6c757d; line-height: 1.4; margin-bottom: 8px;">
                        <strong>连线颜色：</strong>选择连线的颜色主题
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="setEdgeColor('blue')">🔵 蓝色</button>
                        <button class="control-btn" onclick="setEdgeColor('red')">🔴 红色</button>
                        <button class="control-btn" onclick="setEdgeColor('green')">🟢 绿色</button>
                    </div>
                    <div class="btn-row">
                        <button class="control-btn" onclick="setEdgeColor('purple')">🟣 紫色</button>
                        <button class="control-btn" onclick="setEdgeColor('orange')">🟠 橙色</button>
                        <button class="control-btn" onclick="setEdgeColor('gray')">⚫ 灰色</button>
                    </div>
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
                        <strong>层级间距：</strong><br>
                        • 📏 层级间距：调整上下层级之间的垂直距离<br>
                        • 🔄 应用间距：立即应用新的层级间距设置<br>
                        • 🔄 重置间距：恢复到默认层级间距值(150px)<br><br>
                        <strong>智能布局：</strong><br>
                        • 🎯 智能股权布局：按最大比例排序，每层3-4个节点<br>
                        • 📐 智能分布：考虑连接关系，减少交叉<br>
                        • 📏 简单分布：保守的居中分布<br>
                        • 🔄 重置位置：恢复到原始布局<br><br>
                        <strong>连线样式：</strong><br>
                        • 📏 直线：简洁的直线连接<br>
                        • 🌊 平滑：流畅的曲线连接<br>
                        • ⚡ 动态：动态调整的曲线<br>
                        • ➡️ 水平/⬇️ 垂直：强制水平或垂直方向<br>
                        • ❌ 对角交叉：减少交叉的斜线<br><br>
                        <strong>连线颜色：</strong><br>
                        • 支持6种颜色主题：蓝、红、绿、紫、橙、灰<br>
                        • 根据持股比例自动调整颜色深度<br>
                        • 高比例（>50%）颜色更深，低比例（<20%）颜色更浅<br><br>
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
        
        // 🔥 新增：字体和边框调整变量
        let globalFontSize = 12;
        let globalBorderWidth = 1;
        
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
        let globalNodeWidth = 100;
        let globalNodeHeight = 57;
        
        // 🔥 布局模式切换
        let isHierarchicalLayout = true;  // 默认使用层级布局
        
        // 🔥 节点位置控制
        let selectedNodeId = null;  // 当前选中的节点ID
        const MOVE_STEP = 20;  // 每次移动的像素距离
        
        // 🔥 Ctrl+拖拽Y轴移动控制
        let isDraggingWithCtrl = false;  // 是否正在Ctrl+拖拽
        let draggedNodeId = null;  // 正在拖拽的节点ID
        let dragStartPos = null;  // 拖拽开始时的位置
        
        // 🔥 右键菜单控制
        let contextMenuNodeId = null;  // 右键菜单对应的节点ID
        let contextMenuEdgeId = null;  // 右键菜单对应的边ID
        let hiddenNodes = new Set();   // 隐藏的节点ID集合
        let hiddenEdges = new Set();   // 隐藏的边ID集合
        let deletedNodes = new Set();  // 删除的节点ID集合
        let deletedEdges = new Set();  // 删除的边ID集合
        let nodeHistory = [];          // 操作历史，用于撤销功能

        function normalizeNodeId(nodeId) {{
            if (typeof nodeId === 'string') {{
                const trimmed = nodeId.trim();
                if (!trimmed) {{
                    return nodeId;
                }}
                const numericId = Number(trimmed);
                if (!Number.isNaN(numericId)) {{
                    return numericId;
                }}
            }}
            return nodeId;
        }}
        
        // 🔥 消息显示函数
        function showMessage(message, type = 'info') {{
            console.log(`[消息] ${{message}}`);
            
            // 创建消息元素
            const messageDiv = document.createElement('div');
            messageDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${{type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'}};
                color: white;
                padding: 12px 20px;
                border-radius: 6px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                font-size: 14px;
                max-width: 300px;
                word-wrap: break-word;
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s ease;
            `;
            messageDiv.textContent = message;
            
            document.body.appendChild(messageDiv);
            
            // 显示动画
            setTimeout(() => {{
                messageDiv.style.opacity = '1';
                messageDiv.style.transform = 'translateX(0)';
            }}, 100);
            
            // 自动隐藏
            setTimeout(() => {{
                messageDiv.style.opacity = '0';
                messageDiv.style.transform = 'translateX(100%)';
                setTimeout(() => {{
                    if (messageDiv.parentNode) {{
                        messageDiv.parentNode.removeChild(messageDiv);
                    }}
                }}, 300);
            }}, 3000);
        }}
        
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
                            minimum: Math.max(80, width - 50), 
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
        
        // 🔥 新增：应用字体和边框设置
        function applyFontAndBorder() {{
            try {{
                console.log(`🎨 应用字体和边框设置: 字体${{globalFontSize}}px, 边框${{globalBorderWidth}}px`);
                
                // 更新所有节点的字体和边框设置
                const updates = [];
                nodes.forEach(node => {{
                    updates.push({{
                        id: node.id,
                        font: {{
                            size: globalFontSize,
                            color: node.font ? node.font.color : '#212529',
                            multi: true
                        }},
                        borderWidth: globalBorderWidth
                    }});
                }});
                nodes.update(updates);
                
                // 更新网络选项
                network.setOptions({{
                    nodes: {{
                        font: {{
                            size: globalFontSize,
                            color: '#212529',
                            multi: true
                        }},
                        borderWidth: globalBorderWidth
                    }}
                }});
                
                console.log('✅ 字体和边框设置已应用');
            }} catch (error) {{
                console.error('❌ 应用字体和边框设置失败:', error);
            }}
        }}
        
        // 🔥 新增：重置字体和边框到默认值
        function resetFontAndBorder() {{
            try {{
                console.log('🔄 重置字体和边框到默认值...');
                
                // 重置为默认值
                globalFontSize = 12;
                globalBorderWidth = 1;
                
                // 更新滑块
                document.getElementById('fontSizeSlider').value = globalFontSize;
                document.getElementById('borderWidthSlider').value = globalBorderWidth;
                
                // 更新显示值
                document.getElementById('fontSizeValue').textContent = globalFontSize + 'px';
                document.getElementById('borderWidthValue').textContent = globalBorderWidth + 'px';
                
                // 应用重置后的设置
                applyFontAndBorder();
                
                console.log('✅ 字体和边框已重置到默认值');
            }} catch (error) {{
                console.error('❌ 重置字体和边框失败:', error);
            }}
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
            const nodeWidth = node.widthConstraint ? node.widthConstraint.maximum || 100 : 100;
            const nodeHeight = node.heightConstraint ? node.heightConstraint.minimum || 57 : 57;
            
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
            const nodeWidth = node.widthConstraint ? node.widthConstraint.maximum || 100 : 100;
            const nodeHeight = node.heightConstraint ? node.heightConstraint.minimum || 57 : 57;
            
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
            originalWidth = node.widthConstraint ? node.widthConstraint.maximum || 100 : 100;
            originalHeight = node.heightConstraint ? node.heightConstraint.minimum || 57 : 57;
            
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
                    newWidth = Math.max(80, originalWidth - deltaX / scale);
                    newHeight = Math.max(30, originalHeight - deltaY / scale);
                    break;
                case 'top-right':
                    newWidth = Math.max(80, originalWidth + deltaX / scale);
                    newHeight = Math.max(30, originalHeight - deltaY / scale);
                    break;
                case 'bottom-right':
                    newWidth = Math.max(80, originalWidth + deltaX / scale);
                    newHeight = Math.max(30, originalHeight + deltaY / scale);
                    break;
                case 'bottom-left':
                    newWidth = Math.max(80, originalWidth - deltaX / scale);
                    newHeight = Math.max(30, originalHeight + deltaY / scale);
                    break;
            }}
            
            // 更新节点尺寸
            nodes.update([{{
                id: resizingNode,
                widthConstraint: {{ 
                    minimum: Math.max(80, newWidth - 50), 
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
            const width = node.widthConstraint ? node.widthConstraint.maximum || 100 : 100;
            const height = node.heightConstraint ? node.heightConstraint.minimum || 57 : 57;
            
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
                    enabled: isHierarchicalLayout,  // 🔥 动态控制层级布局
                    direction: 'UD',
                    sortMethod: 'directed',  // 🔥 改为directed，避免hubsize的堆叠问题
                    levelSeparation: {level_separation},  // 🔥 使用原始层级间距值
                    nodeSpacing: Math.max(280, {node_spacing}),      // 🔥 优化节点间距
                    treeSpacing: Math.max(280, {tree_spacing}),      // 🔥 优化树间距
                    blockShifting: true,
                    edgeMinimization: true,
                    parentCentralization: false,  // 🔥 关闭父节点居中，让子节点自由分布
                    shakeTowards: 'leaves'  // 向叶子节点方向调整，减少交叉
                }}
            }},
            physics: {{
                enabled: true,  // 🔥 启用物理引擎用于初始布局优化
                stabilization: {{
                    enabled: true,  // 🔥 启用初始稳定化
                    iterations: isHierarchicalLayout ? 200 : 100,  // 🔥 根据布局模式调整迭代次数
                    updateInterval: 50,
                    onlyDynamicEdges: false,
                    fit: false  // 🔥 不自动调整视图，保持连线样式
                }},
                solver: isHierarchicalLayout ? 'hierarchicalRepulsion' : 'forceAtlas2Based',  // 🔥 根据布局模式选择算法
                hierarchicalRepulsion: {{
                    centralGravity: 0,
                    springLength: 250,        // 🔥 增加弹簧长度
                    springConstant: 0.005,    // 🔥 减少弹簧常数，降低约束力
                    nodeDistance: 200,        // 🔥 增加节点距离
                    damping: 0.1              // 🔥 增加阻尼，提高稳定性
                }},
                forceAtlas2Based: {{
                    theta: 0.5,
                    gravitationalConstant: -26,
                    centralGravity: 0.01,
                    springConstant: 0.08,
                    springLength: 100,
                    damping: 0.4,
                    avoidOverlap: 0.5
                }}
            }},
            interaction: {{
                dragNodes: true,
                dragView: true,
                zoomView: true,
                hover: true,
                keyboard: {{
                    enabled: false,  // 🔥 禁用vis.js键盘平移，避免与节点移动冲突
                    speed: {{x: 10, y: 10, zoom: 0.02}},
                    bindToWindow: true
                }}
            }},
            nodes: {{
                font: {{
                    size: 12,  // 🔥 减小字体大小，给文字更多空间
                    color: '#212529',
                    multi: true
                }},
                borderWidth: 1,  // 🔥 减小边框宽度，给内容更多空间
                margin: {{  // 🔥 减小内边距，让文字离边框更近
                    top: 4,
                    right: 4,
                    bottom: 4,
                    left: 4
                }},
                shape: 'box',
                widthConstraint: {{
                    minimum: 100,
                    maximum: 100
                }},
                heightConstraint: {{
                    minimum: 57
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
                    enabled: false  // 🔥 默认使用直线连接
                }},
                selectionWidth: 3,  // 🔥 适中的选中线条粗细
                hoverWidth: 3  // 🔥 适中的悬停线条粗细
            }}
        }};
        
        // 创建网络（全局变量，供其他函数使用）
        const container = document.getElementById('network-container');
        window.network = new vis.Network(container, {{nodes, edges}}, options);
        const network = window.network;
        
        // 🔥 添加节点选择事件监听
        network.on('selectNode', function(params) {{
            if (params.nodes.length > 0) {{
                selectedNodeId = params.nodes[0];
                
                // 🔥 自动解除节点锁定（无条件，以确保核心公司也有明确反馈）
                const nodeData = nodes.get(selectedNodeId);
                if (nodeData) {{
                    const updatedNode = {{
                        ...nodeData,
                        fixed: {{x: false, y: false}}
                    }};
                    nodes.update(updatedNode);
                    showMessage('节点已自动解除锁定');
                }}
                
                updateNodeSelectionUI();
            }}
        }});
        
        network.on('deselectNode', function(params) {{
            selectedNodeId = null;
            updateNodeSelectionUI();
        }});
        
        // 点击空白区域取消选择
        network.on('click', function(params) {{
            if (params.nodes.length === 0) {{
                selectedNodeId = null;
                updateNodeSelectionUI();
            }}
        }});
        
        // 🔥 右键菜单事件监听
        network.on('oncontext', function(params) {{
            console.log('右键事件触发:', params);
            params.event.preventDefault();
            if (params.nodes.length > 0) {{
                showContextMenu(params.event, params.nodes[0]);
            }} else if (params.edges.length > 0) {{
                showEdgeContextMenu(params.event, params.edges[0]);
            }}
        }});
        
        // 备用方案：使用原生右键事件
        network.on('click', function(params) {{
            if (params.event && params.event.button === 2 && params.nodes.length > 0) {{
                console.log('原生右键事件触发:', params);
                showContextMenu(params.event, params.nodes[0]);
            }}
        }});
        
        // 点击其他地方隐藏右键菜单
        document.addEventListener('click', function(event) {{
            if (!event.target.closest('.context-menu')) {{
                hideContextMenu();
                hideEdgeContextMenu();
            }}
        }});
        
        // 右键菜单项点击事件 - 节点
        document.getElementById('hideNodeItem').addEventListener('click', function() {{
            hideNode();
        }});
        
        document.getElementById('showHiddenNodesItem').addEventListener('click', function() {{
            showNode();
        }});
        
        document.getElementById('deleteNodeItem').addEventListener('click', function() {{
            deleteNode();
        }});
        
        // 右键菜单项点击事件 - 边
        document.getElementById('hideEdgeItem').addEventListener('click', function() {{
            hideEdge();
        }});
        
        document.getElementById('deleteEdgeItem').addEventListener('click', function() {{
            deleteEdge();
        }});
        
        document.getElementById('resetNodeSizeItem').addEventListener('click', function() {{
            if (contextMenuNodeId) {{
                resetSingleNodeSize(contextMenuNodeId);
                hideContextMenu();
                showMessage('节点尺寸已重置');
            }}
        }});
        
        document.getElementById('centerNodeItem').addEventListener('click', function() {{
            centerNode();
        }});
        
        document.getElementById('unlockNodeItem').addEventListener('click', function() {{
            if (contextMenuNodeId) {{
                unlockNode(contextMenuNodeId);
                hideContextMenu();
                showMessage('节点已解除锁定');
            }}
        }});

        // 🔥 改进的键盘事件处理：确保节点移动优先于画布平移
        document.addEventListener('keydown', function(e) {{
            // 当焦点在输入框、文本域、下拉框或可编辑区域时不拦截
            const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
            if (tag === 'input' || tag === 'textarea' || tag === 'select' || (e.target && e.target.isContentEditable)) {{
                return;
            }}

            // 🔥 如果有选中的节点，优先处理节点移动
            if (selectedNodeId !== null) {{
                if (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'ArrowLeft' || e.key === 'ArrowRight') {{
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation(); // 🔥 阻止其他事件监听器
                    
                    console.log(`🎯 键盘移动节点: ${{e.key}}`);
                    if (e.key === 'ArrowUp') moveNode('up');
                    else if (e.key === 'ArrowDown') moveNode('down');
                    else if (e.key === 'ArrowLeft') moveNode('left');
                    else if (e.key === 'ArrowRight') moveNode('right');
                    return false; // 🔥 确保事件被完全阻止
                }} else if (e.key === 'Delete' || e.key === 'Backspace') {{
                    // 🔥 删除键删除选中的节点
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    deleteNode(selectedNodeId);
                    return false;
                }}
            }}
        }}, true); // capture=true，确保优先处理
        
        // 🔥 额外的键盘事件监听器，确保完全阻止vis.js的键盘处理
        window.addEventListener('keydown', function(e) {{
            if (selectedNodeId !== null && (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {{
                e.preventDefault();
                e.stopPropagation();
                return false;
            }}
        }}, true);
        
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
                            const nodeWidth = node.widthConstraint ? node.widthConstraint.maximum || 100 : 100;
                            const nodeHeight = node.heightConstraint ? node.heightConstraint.minimum || 57 : 57;
                            
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
            
            // 🔥 新增：字体和边框滑块事件处理
            const fontSizeSlider = document.getElementById('fontSizeSlider');
            const borderWidthSlider = document.getElementById('borderWidthSlider');
            const fontSizeValue = document.getElementById('fontSizeValue');
            const borderWidthValue = document.getElementById('borderWidthValue');
            
            fontSizeSlider.addEventListener('input', function() {{
                globalFontSize = parseInt(this.value);
                fontSizeValue.textContent = globalFontSize + 'px';
            }});
            
            borderWidthSlider.addEventListener('input', function() {{
                globalBorderWidth = parseInt(this.value);
                borderWidthValue.textContent = globalBorderWidth + 'px';
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
            
            // 🔥 层级间距滑块监听器
            const levelSeparationSlider = document.getElementById('levelSeparationSlider');
            const levelSeparationValue = document.getElementById('levelSeparationValue');
            
            levelSeparationSlider.addEventListener('input', function() {{
                const value = parseInt(this.value);
                levelSeparationValue.textContent = value + 'px';
                currentLevelSeparation = value;
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
        
        // 🔥 层级间距调整功能
        let currentLevelSeparation = {level_separation};
        
        // 应用层级间距变化
        function applyLevelSpacing() {{
            try {{
                console.log('📏 应用层级间距变化...');
                
                // 获取滑块值
                currentLevelSeparation = parseInt(document.getElementById('levelSeparationSlider').value);
                
                console.log('📏 新层级间距:', currentLevelSeparation);
                
                // 更新层级布局选项，只调整层级间距，保持当前布局模式
                if (isHierarchicalLayout) {{
                    network.setOptions({{
                        layout: {{
                            hierarchical: {{
                                enabled: true,
                                direction: 'UD',
                                sortMethod: 'directed',
                                levelSeparation: currentLevelSeparation,  // 🔥 直接使用用户设置的值
                                nodeSpacing: Math.max(280, {node_spacing}),
                                treeSpacing: Math.max(280, {tree_spacing}),
                                blockShifting: true,
                                edgeMinimization: true,
                                parentCentralization: false
                            }}
                        }},
                        physics: {{
                            enabled: false  // 🔥 保持物理引擎关闭，避免重新排版
                        }}
                    }});
                    
                    console.log('✅ 层级间距已更新，保持层级布局模式');
                }} else {{
                    console.log('ℹ️ 当前为自由布局，层级间距调整将在切换到层级布局时生效');
                }}
                
                // 🔥 不调用distributeLevels()，避免触发重新排版
                // 只更新布局参数，让vis.js自动调整间距
                
            }} catch (error) {{
                console.error('❌ 应用层级间距失败:', error);
            }}
        }}
        
        // 重置层级间距到默认值
        function resetLevelSpacing() {{
            try {{
                console.log('🔄 重置层级间距到默认值...');
                
                // 重置为默认值
                currentLevelSeparation = 150;
                
                // 更新滑块
                document.getElementById('levelSeparationSlider').value = currentLevelSeparation;
                
                // 更新显示值
                document.getElementById('levelSeparationValue').textContent = currentLevelSeparation + 'px';
                
                // 直接应用重置后的间距，不调用applyLevelSpacing避免重复
                if (isHierarchicalLayout) {{
                    network.setOptions({{
                        layout: {{
                            hierarchical: {{
                                enabled: true,
                                direction: 'UD',
                                sortMethod: 'directed',
                                levelSeparation: currentLevelSeparation,  // 🔥 直接使用用户设置的值
                                nodeSpacing: Math.max(280, {node_spacing}),
                                treeSpacing: Math.max(280, {tree_spacing}),
                                blockShifting: true,
                                edgeMinimization: true,
                                parentCentralization: false
                            }}
                        }},
                        physics: {{
                            enabled: false  // 🔥 保持物理引擎关闭
                        }}
                    }});
                }}
                
                console.log('✅ 层级间距已重置，保持层级布局模式');
                
            }} catch (error) {{
                console.error('❌ 重置层级间距失败:', error);
            }}
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
            // 🔥 稳定化后执行按层均匀分布，多次执行确保效果
            if (typeof distributeLevels === 'function') {{
                setTimeout(() => distributeLevels(), 100);   // 第一次执行
                setTimeout(() => distributeLevels(), 300);   // 第二次执行确保效果
                setTimeout(() => distributeLevels(), 600);   // 第三次执行最终调整
            }}
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
            // 🔥 修复：直接切换物理引擎状态，不依赖getOptions
            network.setOptions({{physics: {{enabled: true}}}});
            setTimeout(() => {{
                network.setOptions({{physics: {{enabled: false}}}});
            }}, 100);
        }}
        
        // 🔥 布局切换函数
        function toggleLayout() {{
            isHierarchicalLayout = !isHierarchicalLayout;
            
            // 更新按钮文本
            const btn = document.getElementById('layoutToggleBtn');
            btn.textContent = isHierarchicalLayout ? '切换到自由布局' : '切换到层级布局';
            
            // 更新网络配置
            const newOptions = {{
                layout: {{
                    hierarchical: {{
                        enabled: isHierarchicalLayout,
                        direction: 'UD',
                        sortMethod: 'hubsize',
                        levelSeparation: {level_separation},
                        nodeSpacing: {node_spacing},
                        treeSpacing: {tree_spacing},
                        blockShifting: true,
                        edgeMinimization: true,
                        parentCentralization: true,
                        shakeTowards: 'leaves'
                    }}
                }},
                physics: {{
                    enabled: true,
                        stabilization: {{
                            enabled: true,
                            iterations: isHierarchicalLayout ? 200 : 100,
                            updateInterval: 50,
                            onlyDynamicEdges: false,
                            fit: false  // 🔥 不自动调整视图，保持连线样式
                        }},
                    solver: isHierarchicalLayout ? 'hierarchicalRepulsion' : 'forceAtlas2Based',
                    hierarchicalRepulsion: {{
                        centralGravity: 0,
                        springLength: 200,
                        springConstant: 0.01,
                        nodeDistance: 180,
                        damping: 0.09
                    }},
                    forceAtlas2Based: {{
                        theta: 0.5,
                        gravitationalConstant: -26,
                        centralGravity: 0.01,
                        springConstant: 0.08,
                        springLength: 100,
                        damping: 0.4,
                        avoidOverlap: 0.5
                    }}
                }}
            }};
            
            network.setOptions(newOptions);
            
            // 显示切换提示
            const message = isHierarchicalLayout ? 
                '已切换到层级布局：节点按层级排列，只能左右移动' : 
                '已切换到自由布局：节点可任意拖动到任何位置';
            console.log(message);
            
            // 显示用户提示
            showMessage(message);

            // 触发布局稳定化后再做一次按层均匀分布
            setTimeout(function() {{
                if (typeof distributeLevels === 'function') {{
                    distributeLevels();
                }}
            }}, 150);
        }}
        
        // 🔥 右键菜单功能
        function showContextMenu(event, nodeId) {{
            event.preventDefault();
            contextMenuNodeId = nodeId;
            
            const contextMenu = document.getElementById('contextMenu');
            const hideItem = document.getElementById('hideNodeItem');
            const showItem = document.getElementById('showHiddenNodesItem');
            
            // 根据节点状态显示不同的菜单项
            if (hiddenNodes.has(nodeId)) {{
                hideItem.style.display = 'none';
                showItem.style.display = 'flex';
            }} else {{
                hideItem.style.display = 'flex';
                showItem.style.display = 'none';
            }}
            
            // 设置菜单位置
            contextMenu.style.left = event.pageX + 'px';
            contextMenu.style.top = event.pageY + 'px';
            contextMenu.style.display = 'block';
        }}
        
        function hideContextMenu() {{
            const contextMenu = document.getElementById('contextMenu');
            contextMenu.style.display = 'none';
            contextMenuNodeId = null;
        }}
        
        // 🔥 边的右键菜单功能
        function showEdgeContextMenu(event, edgeId) {{
            event.preventDefault();
            contextMenuEdgeId = edgeId;
            
            const edgeContextMenu = document.getElementById('edgeContextMenu');
            
            // 设置菜单位置
            edgeContextMenu.style.left = event.pageX + 'px';
            edgeContextMenu.style.top = event.pageY + 'px';
            edgeContextMenu.style.display = 'block';
        }}
        
        function hideEdgeContextMenu() {{
            const edgeContextMenu = document.getElementById('edgeContextMenu');
            if (edgeContextMenu) {{
                edgeContextMenu.style.display = 'none';
                contextMenuEdgeId = null;
            }}
        }}
        
        function hideEdge(edgeId) {{
            if (!edgeId) edgeId = contextMenuEdgeId;
            if (!edgeId) return;
            
            // 隐藏边
            hiddenEdges.add(edgeId);
            const edge = edges.get(edgeId);
            if (edge) {{
                edge.hidden = true;
                edges.update(edge);
                
                const fromNode = nodes.get(edge.from);
                const toNode = nodes.get(edge.to);
                const fromLabel = fromNode ? fromNode.label : edge.from;
                const toLabel = toNode ? toNode.label : edge.to;
                showMessage(`连线 "${{fromLabel}} → ${{toLabel}}" 已隐藏`);
            }}
            
            hideEdgeContextMenu();
            updateHiddenEdgesList();
            
            // 🔥 不调用redraw()，保持当前布局不变
            // 如果需要刷新布局，用户可以手动点击"适应"按钮
        }}
        
        function showEdge(edgeId) {{
            if (!edgeId) return;
            
            // 显示边
            hiddenEdges.delete(edgeId);
            const edge = edges.get(edgeId);
            if (edge) {{
                edge.hidden = false;
                edges.update(edge);
            }}
            
            updateHiddenEdgesList();
        }}
        
        function deleteEdge(edgeId) {{
            if (!edgeId) edgeId = contextMenuEdgeId;
            if (!edgeId) return;
            
            if (confirm('确定要删除这条连线吗？')) {{
                deletedEdges.add(edgeId);
                edges.remove(edgeId);
                hiddenEdges.delete(edgeId);
                
                showMessage('连线已删除');
                hideEdgeContextMenu();
                updateHiddenEdgesList();
            }}
        }}
        
        function showAllHiddenEdges() {{
            hiddenEdges.forEach(edgeId => {{
                showEdge(edgeId);
            }});
            hiddenEdges.clear();
            updateHiddenEdgesList();
            showMessage('所有隐藏的连线已显示');
        }}
        
        function clearHiddenEdgesList() {{
            if (confirm('确定要清空隐藏的连线列表吗？这将永久删除这些连线。')) {{
                hiddenEdges.forEach(edgeId => {{
                    edges.remove(edgeId);
                    deletedEdges.add(edgeId);
                }});
                hiddenEdges.clear();
                updateHiddenEdgesList();
                showMessage('隐藏的连线已清空');
            }}
        }}
        
        function updateHiddenEdgesList() {{
            const hiddenEdgesList = document.getElementById('hiddenEdgesList');
            if (!hiddenEdgesList) return;
            
            if (hiddenEdges.size === 0) {{
                hiddenEdgesList.innerHTML = '<div class="hidden-edges-empty">暂无隐藏连线</div>';
                return;
            }}
            
            let html = '';
            hiddenEdges.forEach(edgeId => {{
                const edge = edges.get(edgeId);
                if (edge) {{
                    const fromNode = nodes.get(edge.from);
                    const toNode = nodes.get(edge.to);
                    const fromLabel = fromNode ? fromNode.label.split('<br>')[0] : edge.from;
                    const toLabel = toNode ? toNode.label.split('<br>')[0] : edge.to;
                    const edgeLabel = edge.label || '';
                    
                    html += `
                        <div class="hidden-node-item">
                            <span class="hidden-node-name">${{fromLabel}} → ${{toLabel}} ${{edgeLabel}}</span>
                            <button class="show-node-btn" onclick="showEdge('${{edgeId}}')">显示</button>
                        </div>
                    `;
                }}
            }});
            
            hiddenEdgesList.innerHTML = html;
        }}
        
        function hideNode(nodeId) {{
            if (!nodeId) nodeId = contextMenuNodeId;
            if (!nodeId) {{
                console.log('hideNode: 没有提供nodeId');
                return;
            }}
            
            console.log('hideNode: 开始隐藏节点', nodeId);
            
            // 保存操作历史
            saveToHistory('hide', nodeId);
            
            // 隐藏节点
            hiddenNodes.add(nodeId);
            console.log('hideNode: 已添加到hiddenNodes集合，当前数量:', hiddenNodes.size);
            
            const node = nodes.get(nodeId);
            if (node) {{
                node.hidden = true;
                nodes.update(node);
                console.log('hideNode: 节点已隐藏:', node.label);
            }}
            
            // 隐藏相关的边
            const connectedEdges = edges.get({{
                filter: function(edge) {{
                    return edge.from === nodeId || edge.to === nodeId;
                }}
            }});
            
            connectedEdges.forEach(edge => {{
                edge.hidden = true;
                edges.update(edge);
            }});
            
            hideContextMenu();
            showMessage(`节点 "${{node.label}}" 已隐藏`);
            
            console.log('hideNode: 准备更新隐藏节点列表');
            updateHiddenNodesList();
        }}
        
        function showNode(nodeId) {{
            if (nodeId === undefined || nodeId === null) nodeId = contextMenuNodeId;
            if (nodeId === undefined || nodeId === null) return;

            const originalId = nodeId;
            nodeId = normalizeNodeId(nodeId);
            const candidateIds = new Set([nodeId]);
            if (originalId !== nodeId) {{
                candidateIds.add(originalId);
            }}

            const node = nodes.get(nodeId) || nodes.get(originalId);
            if (!node) {{
                console.warn('showNode: 找不到节点', nodeId);
                candidateIds.forEach(id => hiddenNodes.delete(id));
                updateHiddenNodesList();
                return;
            }}
            
            // 保存操作历史
            saveToHistory('show', node.id);
            
            // 显示节点
            candidateIds.forEach(id => hiddenNodes.delete(id));
            node.hidden = false;
            nodes.update(node);
            
            // 显示相关的边
            const connectedEdges = edges.get({{
                filter: function(edge) {{
                    return candidateIds.has(edge.from) || candidateIds.has(edge.to);
                }}
            }});
            
            connectedEdges.forEach(edge => {{
                edge.hidden = false;
                edges.update(edge);
            }});
            
            hideContextMenu();
            showMessage(`节点 "${{node.label}}" 已显示`);
            updateHiddenNodesList();
        }}
        
        function deleteNode(nodeId) {{
            if (nodeId === undefined || nodeId === null) nodeId = contextMenuNodeId;
            if (nodeId === undefined || nodeId === null) return;
            
            const originalId = nodeId;
            nodeId = normalizeNodeId(nodeId);
            const candidateIds = new Set([nodeId]);
            if (originalId !== nodeId) {{
                candidateIds.add(originalId);
            }}
            
            const node = nodes.get(nodeId) || nodes.get(originalId);
            if (!node) return;
            
            if (!confirm(`确定要删除节点 "${{node.label}}" 吗？此操作不可撤销。`)) {{
                hideContextMenu();
                return;
            }}
            
            // 保存操作历史
            saveToHistory('delete', node.id, node, edges.get({{
                filter: function(edge) {{
                    return candidateIds.has(edge.from) || candidateIds.has(edge.to);
                }}
            }}));
            
            // 删除节点
            candidateIds.forEach(id => deletedNodes.add(id));
            nodes.remove(node.id);
            
            // 删除相关的边
            const connectedEdges = edges.get({{
                filter: function(edge) {{
                    return candidateIds.has(edge.from) || candidateIds.has(edge.to);
                }}
            }});
            
            connectedEdges.forEach(edge => {{
                edges.remove(edge.id);
            }});
            
            hideContextMenu();
            showMessage(`节点 "${{node.label}}" 已删除`);
            updateHiddenNodesList();
        }}
        
        // 🔥 解除节点锁定函数
        function unlockNode(nodeId) {{
            if (!nodeId) nodeId = contextMenuNodeId;
            if (!nodeId) return;
            
            const nodeData = nodes.get(nodeId);
            if (!nodeData) return;
            
            // 解除固定状态
            const updatedNode = {{
                ...nodeData,
                fixed: {{x: false, y: false}}
            }};
            nodes.update(updatedNode);
            
            console.log(`🔓 节点 ${{nodeId}} 已解除锁定`);
        }}
        
        function centerNode(nodeId) {{
            if (!nodeId) nodeId = contextMenuNodeId;
            if (!nodeId) return;
            
            network.focus(nodeId, {{
                scale: 1.2,
                animation: {{
                    duration: 1000,
                    easingFunction: "easeInOutQuad"
                }}
            }});
            
            hideContextMenu();
            showMessage(`节点已居中显示`);
        }}
        
        function saveToHistory(action, nodeId, nodeData = null, edgeData = null) {{
            const historyItem = {{
                action: action,
                nodeId: nodeId,
                nodeData: nodeData,
                edgeData: edgeData,
                timestamp: Date.now()
            }};
            
            nodeHistory.push(historyItem);
            
            // 限制历史记录数量
            if (nodeHistory.length > 50) {{
                nodeHistory.shift();
            }}
        }}
        
        // 🔥 隐藏节点管理功能
        function updateHiddenNodesList() {{
            console.log('更新隐藏节点列表，当前隐藏节点数量:', hiddenNodes.size);
            
            const hiddenNodesSection = document.getElementById('hiddenNodesSection');
            const hiddenNodesList = document.getElementById('hiddenNodesList');
            
            if (!hiddenNodesSection || !hiddenNodesList) {{
                console.error('找不到隐藏节点管理元素');
                return;
            }}
            
            // 清空现有列表
            hiddenNodesList.innerHTML = '';
            
            if (hiddenNodes.size === 0) {{
                // 显示空状态提示
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'hidden-nodes-empty';
                emptyDiv.textContent = '暂无隐藏节点';
                hiddenNodesList.appendChild(emptyDiv);
                console.log('显示空状态提示');
                return;
            }}
            
            console.log('开始创建隐藏节点列表项');
            
            // 为每个隐藏的节点创建列表项
            hiddenNodes.forEach(nodeId => {{
                const node = nodes.get(nodeId);
                if (!node) {{
                    console.log('节点不存在:', nodeId);
                    return;
                }}
                
                console.log('创建列表项:', node.label);
                
                const listItem = document.createElement('div');
                listItem.className = 'hidden-node-item';
                listItem.innerHTML = `
                    <span class="hidden-node-name" title="${{node.label}}">${{node.label}}</span>
                    <div class="hidden-node-actions">
                        <button class="hidden-node-btn" onclick="showNode('${{nodeId}}')" title="显示节点">👁️</button>
                        <button class="hidden-node-btn danger" onclick="deleteNode('${{nodeId}}')" title="删除节点">🗑️</button>
                    </div>
                `;
                
                hiddenNodesList.appendChild(listItem);
            }});
            
            console.log('隐藏节点列表更新完成');
        }}
        
        function showAllHiddenNodes() {{
            const nodeIds = Array.from(hiddenNodes);
            nodeIds.forEach(nodeId => {{
                showNode(nodeId);
            }});
            
            if (nodeIds.length > 0) {{
                showMessage(`已显示 ${{nodeIds.length}} 个隐藏节点`);
            }}
        }}
        
        function clearHiddenNodesList() {{
            if (hiddenNodes.size === 0) {{
                showMessage('没有隐藏的节点');
                return;
            }}
            
            if (confirm(`确定要删除所有 ${{hiddenNodes.size}} 个隐藏节点吗？此操作不可撤销。`)) {{
                const nodeIds = Array.from(hiddenNodes);
                nodeIds.forEach(nodeId => {{
                    deleteNode(nodeId);
                }});
                showMessage(`已删除 ${{nodeIds.length}} 个隐藏节点`);
            }}
        }}
        
        // 🔥 测试函数
        function testHideNode() {{
            const allNodes = nodes.get();
            if (allNodes.length === 0) {{
                showMessage('没有可隐藏的节点');
                return;
            }}
            
            const firstNode = allNodes[0];
            console.log('测试隐藏节点:', firstNode.id, firstNode.label);
            hideNode(firstNode.id);
        }}
        
        // 🔥 更新节点选择UI状态
        function updateNodeSelectionUI() {{
            const hasSelection = selectedNodeId !== null;
            
            // 启用/禁用移动按钮
            document.getElementById('moveUpBtn').disabled = !hasSelection;
            document.getElementById('moveDownBtn').disabled = !hasSelection;
            document.getElementById('moveLeftBtn').disabled = !hasSelection;
            document.getElementById('moveRightBtn').disabled = !hasSelection;
            document.getElementById('resetPositionBtn').disabled = !hasSelection;
            
            // 显示/隐藏选中节点信息
            const infoDiv = document.getElementById('selectedNodeInfo');
            const nameSpan = document.getElementById('selectedNodeName');
            
            if (hasSelection) {{
                const node = nodes.get(selectedNodeId);
                const nodeName = node ? node.label : '未知节点';
                nameSpan.textContent = nodeName;
                infoDiv.style.display = 'block';
            }} else {{
                infoDiv.style.display = 'none';
            }}
        }}
        
        // 🔥 移动节点函数
        function moveNode(direction) {{
            if (!selectedNodeId) {{
                console.log('⚠️ 请先选择一个节点');
                return;
            }}
            
            console.log(`🎯 尝试移动节点 ${{selectedNodeId}} 向 ${{direction}}`);
            
            const positions = network.getPositions([selectedNodeId]);
            if (!positions[selectedNodeId]) {{
                console.log('❌ 无法获取节点位置');
                return;
            }}
            
            const currentPos = positions[selectedNodeId];
            let newX = currentPos.x;
            let newY = currentPos.y;
            
            console.log(`📍 当前位置: (${{newX}}, ${{newY}})`);
            
            switch (direction) {{
                case 'up':
                    newY -= MOVE_STEP;
                    break;
                case 'down':
                    newY += MOVE_STEP;
                    break;
                case 'left':
                    newX -= MOVE_STEP;
                    break;
                case 'right':
                    newX += MOVE_STEP;
                    break;
            }}
            
            console.log(`🎯 目标位置: (${{newX}}, ${{newY}})`);
            
            // 🔥 检查节点是否被固定
            const nodeData = nodes.get(selectedNodeId);
            if (nodeData && nodeData.fixed) {{
                console.log('⚠️ 节点被固定，尝试解除固定状态');
                // 解除固定状态
                const updatedNode = {{
                    ...nodeData,
                    fixed: {{x: false, y: false}}
                }};
                nodes.update(updatedNode);
            }}
            
            // 🔥 更新节点位置
            try {{
                if (typeof network.moveNode === 'function') {{
                    network.moveNode(selectedNodeId, newX, newY);
                    console.log(`✅ 节点已向 ${{direction}} 移动 ${{MOVE_STEP}} 像素`);
                }} else {{
                    // 备选方案：直接更新节点数据
                    const updatedNode = {{
                        ...nodeData,
                        x: newX,
                        y: newY,
                        fixed: {{x: false, y: false}}
                    }};
                    nodes.update(updatedNode);
                    console.log(`✅ 节点已向 ${{direction}} 移动 ${{MOVE_STEP}} 像素 (备选方案)`);
                }}
            }} catch (e) {{
                console.error('❌ 移动节点失败:', e);
            }}
        }}
        
        // 🔥 重置节点位置函数
        function resetNodePosition() {{
            if (!selectedNodeId) {{
                console.log('请先选择一个节点');
                return;
            }}
            
            // 重新应用布局算法来重置位置
            if (isHierarchicalLayout) {{
                // 层级布局：重新稳定化
                network.setOptions({{
                    physics: {{
                        enabled: true,
                        stabilization: {{enabled: true, iterations: 50, fit: false}}  // 🔥 不自动调整视图
                    }}
                }});
            }} else {{
                // 自由布局：重新应用物理引擎
                network.setOptions({{
                    physics: {{
                        enabled: true,
                        stabilization: {{enabled: true, iterations: 100, fit: false}}  // 🔥 不自动调整视图
                    }}
                }});
            }}
            
            console.log('节点位置已重置');
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
                            const nodeWidth = node.widthConstraint ? node.widthConstraint.maximum || 100 : 100;
                            const nodeHeight = node.heightConstraint ? node.heightConstraint.minimum || 57 : 57;
                            
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
            // 初始化隐藏节点管理列表
            updateHiddenNodesList();
            console.log('节点大小调整功能已加载');
        }}, 1000);
        
        // 🔥 智能层级分布算法，减少连线交叉，优化视觉效果
        function distributeLevels() {{
            try {{
                console.log('🔄 智能层级分布开始执行...');
                
                const GAP = Math.max(300, {node_spacing} || 0);  // 增加间距
                const LEVEL_GAP = Math.max(250, {level_separation} || 0);  // 层级间距
                
                console.log('📏 间距设置:', {{GAP, LEVEL_GAP}});

                // 获取所有节点和边
                const allNodes = nodes.get();
                const allEdges = edges.get();
                
                if (allNodes.length === 0) {{
                    console.log('⚠️ 没有节点需要分布');
                    return;
                }}

                // 构建层级映射和连接关系
                const levelMap = new Map();
                const connections = new Map(); // 存储连接关系
                
                allNodes.forEach(node => {{
                    const lvl = (typeof node.level === 'number') ? node.level : 0;
                    if (!levelMap.has(lvl)) levelMap.set(lvl, []);
                    levelMap.get(lvl).push(node);
                }});
                
                // 分析连接关系
                allEdges.forEach(edge => {{
                    if (!connections.has(edge.from)) connections.set(edge.from, []);
                    if (!connections.has(edge.to)) connections.set(edge.to, []);
                    connections.get(edge.from).push(edge.to);
                    connections.get(edge.to).push(edge.from);
                }});

                console.log('📊 节点统计:', {{totalNodes: allNodes.length, levels: levelMap.size}});

                // 🔥 智能排序：考虑连接关系，减少交叉
                const sortedLevels = Array.from(levelMap.keys()).sort((a, b) => a - b);
                let movedNodes = 0;
                
                sortedLevels.forEach(level => {{
                    const levelNodes = levelMap.get(level);
                    if (levelNodes.length <= 1) {{
                        console.log(`📌 层级 ${{level}}: 节点数量 ${{levelNodes.length}}，跳过`);
                        return;
                    }}

                    console.log(`🎯 处理层级 ${{level}}，节点数量: ${{levelNodes.length}}`);

                    // 🔥 智能排序：优先考虑连接数，然后考虑连接关系
                    levelNodes.sort((a, b) => {{
                        const aConnections = connections.get(a.id) || [];
                        const bConnections = connections.get(b.id) || [];
                        
                        // 首先按连接数排序
                        if (aConnections.length !== bConnections.length) {{
                            return bConnections.length - aConnections.length;
                        }}
                        
                        // 连接数相同时，按ID排序保持稳定性
                        return a.id - b.id;
                    }});

                    // 🔥 计算层级中心位置
                    const levelCenterX = 0;
                    const levelY = level * LEVEL_GAP; // 确保层级间距

                    // 🔥 从中心向两边分布，但考虑连接关系
                    const half = (levelNodes.length - 1) / 2;
                    levelNodes.forEach((node, index) => {{
                        let targetX = levelCenterX + (index - half) * GAP;
                        
                        // 🔥 微调位置以减少连线交叉
                        const nodeConnections = connections.get(node.id) || [];
                        if (nodeConnections.length > 0) {{
                            // 根据连接关系微调位置
                            const avgConnectionX = nodeConnections.reduce((sum, connId) => {{
                                const connNode = allNodes.find(n => n.id === connId);
                                return sum + (connNode ? connNode.x || 0 : 0);
                            }}, 0) / nodeConnections.length;
                            
                            // 轻微向连接中心偏移
                            targetX = targetX * 0.8 + avgConnectionX * 0.2;
                        }}
                        
                        // 🔥 更新节点位置
                        if (typeof network.moveNode === 'function') {{
                            network.moveNode(node.id, targetX, levelY);
                        }} else {{
                            const updatedNode = {{
                                ...node,
                                x: targetX,
                                y: levelY
                            }};
                            nodes.update(updatedNode);
                        }}
                        
                        console.log(`🔄 节点 ${{node.id}}: 移动到 (${{targetX}}, ${{levelY}})`);
                        movedNodes++;
                    }});
                }});
                
                // 🔥 强制网络重新绘制
                if (typeof network.redraw === 'function') {{
                    network.redraw();
                }}
                
                console.log(`✅ 智能层级分布完成，移动了 ${{movedNodes}} 个节点`);
            }} catch (e) {{
                console.error('❌ distributeLevels 失败:', e);
            }}
        }}
        
        // 🔥 简单分布函数（保守方案）
        function simpleRedistribute() {{
            try {{
                console.log('🔄 简单分布开始执行...');
                
                const GAP = Math.max(200, {node_spacing} || 0);
                
                // 获取所有节点
                const allNodes = nodes.get();
                if (allNodes.length === 0) return;
                
                // 按层级分组
                const levelMap = new Map();
                allNodes.forEach(node => {{
                    const lvl = (typeof node.level === 'number') ? node.level : 0;
                    if (!levelMap.has(lvl)) levelMap.set(lvl, []);
                    levelMap.get(lvl).push(node);
                }});
                
                let movedNodes = 0;
                levelMap.forEach((levelNodes, level) => {{
                    if (levelNodes.length <= 1) return;
                    
                    // 简单按ID排序
                    levelNodes.sort((a, b) => a.id - b.id);
                    
                    // 从中心向两边分布
                    const half = (levelNodes.length - 1) / 2;
                    levelNodes.forEach((node, index) => {{
                        const targetX = (index - half) * GAP;
                        
                        if (typeof network.moveNode === 'function') {{
                            network.moveNode(node.id, targetX, node.y || 0);
                        }} else {{
                            const updatedNode = {{ ...node, x: targetX }};
                            nodes.update(updatedNode);
                        }}
                        movedNodes++;
                    }});
                }});
                
                if (typeof network.redraw === 'function') {{
                    network.redraw();
                }}
                
                showMessage('简单分布完成');
                console.log(`✅ 简单分布完成，移动了 ${{movedNodes}} 个节点`);
            }} catch (e) {{
                console.error('❌ 简单分布失败:', e);
            }}
        }}
        
        // 🔥 智能股权布局算法：按最大比例原则，中心对称，每层3-4个节点
        function optimizeLayout() {{
            try {{
                console.log('🎯 开始智能股权布局...');
                
                const GAP = Math.max(300, {node_spacing} || 0);  // 节点间距
                const LEVEL_GAP = Math.max(250, {level_separation} || 0);  // 层级间距
                const MAX_NODES_PER_LEVEL = 8;  // 每层最大节点数（原为4，提升以减少拥挤）
                
                // 获取所有节点和边
                const allNodes = nodes.get();
                const allEdges = edges.get();
                
                if (allNodes.length === 0) return;
                
                // 🔥 构建层级映射和连接关系
                const levelMap = new Map();
                const nodeConnections = new Map(); // 存储每个节点的连接信息
                const nodePercentages = new Map(); // 存储每个节点的最大比例
                
                allNodes.forEach(node => {{
                    const lvl = (typeof node.level === 'number') ? node.level : 0;
                    if (!levelMap.has(lvl)) levelMap.set(lvl, []);
                    levelMap.get(lvl).push(node);
                    nodeConnections.set(node.id, {{incoming: [], outgoing: []}});
                    nodePercentages.set(node.id, 0);
                }});
                
                // 🔥 分析连接关系和比例
                allEdges.forEach(edge => {{
                    const fromConnections = nodeConnections.get(edge.from);
                    const toConnections = nodeConnections.get(edge.to);
                    
                    if (fromConnections) {{
                        fromConnections.outgoing.push({{
                            to: edge.to,
                            percentage: parseFloat(edge.label) || 0
                        }});
                    }}
                    
                    if (toConnections) {{
                        toConnections.incoming.push({{
                            from: edge.from,
                            percentage: parseFloat(edge.label) || 0
                        }});
                    }}
                    
                    // 更新最大比例
                    const percentage = parseFloat(edge.label) || 0;
                    const currentMax = nodePercentages.get(edge.from) || 0;
                    nodePercentages.set(edge.from, Math.max(currentMax, percentage));
                }});
                
                console.log('📊 节点连接分析完成');
                
                // 🔥 按层级智能布局
                const sortedLevels = Array.from(levelMap.keys()).sort((a, b) => a - b);
                let movedNodes = 0;
                
                sortedLevels.forEach(level => {{
                    const levelNodes = levelMap.get(level);
                    if (levelNodes.length <= 1) return;
                    
                    console.log(`🎯 处理层级 ${{level}}，节点数量: ${{levelNodes.length}}`);
                    
                    // 🔥 按最大比例排序（从大到小）
                    levelNodes.sort((a, b) => {{
                        const aPercentage = nodePercentages.get(a.id) || 0;
                        const bPercentage = nodePercentages.get(b.id) || 0;
                        
                        // 首先按最大比例排序
                        if (aPercentage !== bPercentage) {{
                            return bPercentage - aPercentage;
                        }}
                        
                        // 比例相同时，按连接数排序
                        const aConnections = nodeConnections.get(a.id);
                        const bConnections = nodeConnections.get(b.id);
                        const aConnCount = (aConnections?.outgoing?.length || 0) + (aConnections?.incoming?.length || 0);
                        const bConnCount = (bConnections?.outgoing?.length || 0) + (bConnections?.incoming?.length || 0);
                        
                        if (aConnCount !== bConnCount) {{
                            return bConnCount - aConnCount;
                        }}
                        
                        // 最后按ID排序保持稳定性
                        return a.id - b.id;
                    }});
                    
                    // 🔥 限制每层节点数量，优先保留比例大的节点
                    const limitedNodes = levelNodes.slice(0, MAX_NODES_PER_LEVEL);
                    
                    // 🔥 中心对称布局
                    const levelCenterX = 0;
                    const levelY = level * LEVEL_GAP;
                    
                    const half = (limitedNodes.length - 1) / 2;
                    limitedNodes.forEach((node, index) => {{
                        const targetX = levelCenterX + (index - half) * GAP;
                        
                        if (typeof network.moveNode === 'function') {{
                            network.moveNode(node.id, targetX, levelY);
                        }} else {{
                            const updatedNode = {{
                                ...node,
                                x: targetX,
                                y: levelY
                            }};
                            nodes.update(updatedNode);
                        }}
                        
                        const percentage = nodePercentages.get(node.id) || 0;
                        console.log(`🔄 节点 ${{node.id}} (比例: ${{percentage}}%): 移动到 (${{targetX}}, ${{levelY}})`);
                        movedNodes++;
                    }});
                    
                    // 🔥 处理超出限制的节点（隐藏或放在边缘）
                    if (levelNodes.length > MAX_NODES_PER_LEVEL) {{
                        const extraNodes = levelNodes.slice(MAX_NODES_PER_LEVEL);
                        console.log(`⚠️ 层级 ${{level}} 有 ${{extraNodes.length}} 个节点超出限制，将被隐藏`);
                        
                        extraNodes.forEach(node => {{
                            // 可以选择隐藏这些节点
                            // hideNode(node.id);
                            
                            // 或者放在边缘位置
                            const edgeX = levelCenterX + (MAX_NODES_PER_LEVEL / 2) * GAP + 200;
                            if (typeof network.moveNode === 'function') {{
                                network.moveNode(node.id, edgeX, levelY);
                            }} else {{
                                const updatedNode = {{ ...node, x: edgeX, y: levelY }};
                                nodes.update(updatedNode);
                            }}
                        }});
                    }}
                }});
                
                if (typeof network.redraw === 'function') {{
                    network.redraw();
                }}
                
                showMessage('智能股权布局完成');
                console.log(`🎯 智能股权布局完成，调整了 ${{movedNodes}} 个节点`);
            }} catch (e) {{
                console.error('❌ 智能股权布局失败:', e);
            }}
        }}
        
        // 🔥 解除所有节点固定状态函数
        function unfixAllNodes() {{
            try {{
                console.log('🔓 解除所有节点的固定状态...');
                
                const allNodes = nodes.get();
                let unfixedCount = 0;
                
                allNodes.forEach(node => {{
                    if (node.fixed) {{
                        const updatedNode = {{
                            ...node,
                            fixed: {{x: false, y: false}}
                        }};
                        nodes.update(updatedNode);
                        unfixedCount++;
                        console.log(`🔓 解除节点 ${{node.id}} 的固定状态`);
                    }}
                }});
                
                if (typeof network.redraw === 'function') {{
                    network.redraw();
                }}
                
                showMessage(`已解除 ${{unfixedCount}} 个节点的固定状态`);
                console.log(`✅ 解除固定状态完成，共处理 ${{unfixedCount}} 个节点`);
            }} catch (e) {{
                console.error('❌ 解除固定状态失败:', e);
            }}
        }}
        
        // 🔥 连线样式控制函数
        function setEdgeStyle(style) {{
            try {{
                console.log(`🎨 设置连线样式: ${{style}}`);
                
                const allEdges = edges.get();
                const updatedEdges = allEdges.map(edge => ({{
                    ...edge,
                    smooth: getSmoothConfig(style)
                }}));
                
                edges.update(updatedEdges);
                
                if (typeof network.redraw === 'function') {{
                    network.redraw();
                }}
                
                showMessage(`连线样式已设置为: ${{getStyleName(style)}}`);
                console.log(`✅ 连线样式更新完成: ${{style}}`);
            }} catch (e) {{
                console.error('❌ 设置连线样式失败:', e);
            }}
        }}
        
        // 🔥 获取平滑配置
        function getSmoothConfig(style) {{
            const configs = {{
                'straight': false,  // 直线
                'smooth': {{ type: 'continuous', forceDirection: 'none' }},  // 平滑曲线
                'dynamic': {{ type: 'dynamic' }},  // 动态曲线
                'continuous': {{ type: 'continuous' }},  // 连续曲线
                'discrete': {{ type: 'discrete' }},  // 离散曲线
                'diagonalCross': {{ type: 'diagonalCross' }},  // 对角交叉
                'straightCross': {{ type: 'straightCross' }},  // 直线交叉
                'horizontal': {{ type: 'continuous', forceDirection: 'horizontal' }},  // 水平
                'vertical': {{ type: 'continuous', forceDirection: 'vertical' }}  // 垂直
            }};
            return configs[style] || false;
        }}
        
        // 🔥 获取样式名称
        function getStyleName(style) {{
            const names = {{
                'straight': '直线',
                'smooth': '平滑',
                'dynamic': '动态',
                'continuous': '连续',
                'discrete': '离散',
                'diagonalCross': '对角交叉',
                'straightCross': '直线交叉',
                'horizontal': '水平',
                'vertical': '垂直'
            }};
            return names[style] || style;
        }}
        
        // 🔥 连线颜色控制函数
        function setEdgeColor(colorTheme) {{
            try {{
                console.log(`🎨 设置连线颜色: ${{colorTheme}}`);
                
                const allEdges = edges.get();
                const updatedEdges = allEdges.map(edge => ({{
                    ...edge,
                    color: getColorConfig(colorTheme, edge)
                }}));
                
                edges.update(updatedEdges);
                
                if (typeof network.redraw === 'function') {{
                    network.redraw();
                }}
                
                showMessage(`连线颜色已设置为: ${{getColorName(colorTheme)}}`);
                console.log(`✅ 连线颜色更新完成: ${{colorTheme}}`);
            }} catch (e) {{
                console.error('❌ 设置连线颜色失败:', e);
            }}
        }}
        
        // 🔥 获取颜色配置
        function getColorConfig(theme, edge) {{
            const percentage = parseFloat(edge.label) || 0;
            
            const colorThemes = {{
                'blue': {{
                    color: '#2B7CE9',
                    highlight: '#5A96F5',
                    hover: '#5A96F5'
                }},
                'red': {{
                    color: '#E74C3C',
                    highlight: '#EC7063',
                    hover: '#EC7063'
                }},
                'green': {{
                    color: '#27AE60',
                    highlight: '#58D68D',
                    hover: '#58D68D'
                }},
                'purple': {{
                    color: '#8E44AD',
                    highlight: '#BB8FCE',
                    hover: '#BB8FCE'
                }},
                'orange': {{
                    color: '#E67E22',
                    highlight: '#F39C12',
                    hover: '#F39C12'
                }},
                'gray': {{
                    color: '#7F8C8D',
                    highlight: '#A6ACAF',
                    hover: '#A6ACAF'
                }}
            }};
            
            const baseColor = colorThemes[theme] || colorThemes['blue'];
            
            // 🔥 根据比例调整颜色深度
            if (percentage > 50) {{
                return {{
                    ...baseColor,
                    color: adjustColorBrightness(baseColor.color, -20)
                }};
            }} else if (percentage > 20) {{
                return baseColor;
            }} else {{
                return {{
                    ...baseColor,
                    color: adjustColorBrightness(baseColor.color, 20)
                }};
            }}
        }}
        
        // 🔥 调整颜色亮度
        function adjustColorBrightness(hex, percent) {{
            const num = parseInt(hex.replace('#', ''), 16);
            const amt = Math.round(2.55 * percent);
            const R = (num >> 16) + amt;
            const G = (num >> 8 & 0x00FF) + amt;
            const B = (num & 0x0000FF) + amt;
            return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
                (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
                (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
        }}
        
        // 🔥 获取颜色名称
        function getColorName(theme) {{
            const names = {{
                'blue': '蓝色',
                'red': '红色',
                'green': '绿色',
                'purple': '紫色',
                'orange': '橙色',
                'gray': '灰色'
            }};
            return names[theme] || theme;
        }}
        
        // 🔥 用户手动重新分布节点
        function redistributeNodes() {{
            if (typeof distributeLevels === 'function') {{
                console.log('🔄 开始手动重新分布节点...');
                
                // 🔥 临时启用物理引擎以允许节点移动
                network.setOptions({{
                    physics: {{
                        enabled: true,
                        stabilization: {{
                            enabled: false  // 禁用稳定化，避免干扰
                        }}
                    }}
                }});
                
                // 🔥 解除所有节点的固定状态
                const allNodes = nodes.get();
                allNodes.forEach(node => {{
                    if (node.fixed) {{
                        const updatedNode = {{
                            ...node,
                            fixed: {{x: false, y: false}}
                        }};
                        nodes.update(updatedNode);
                    }}
                }});
                
                // 🔥 执行重新分布
                distributeLevels();
                
                // 🔥 延迟后重新禁用物理引擎
                setTimeout(() => {{
                    network.setOptions({{
                        physics: {{
                            enabled: false
                        }}
                    }});
                    console.log('✅ 物理引擎已重新禁用');
                }}, 1000);
                
                showMessage('节点已重新分布');
                console.log('✅ 用户手动触发节点重新分布完成');
            }} else {{
                showMessage('重新分布功能不可用');
                console.error('❌ distributeLevels 函数不存在');
            }}
        }}
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

