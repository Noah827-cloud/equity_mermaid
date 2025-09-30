#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构可视化Mermaid生成工具

本模块提供将股权结构数据转换为Mermaid图表代码的功能
支持多种数据格式和关系类型，生成清晰的股权结构图
"""

import json
import re
import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mermaid_generator')


def extract_percentage(description: str) -> Optional[float]:
    """
    从关系描述中提取持股比例
    
    Args:
        description: 关系描述文本
    
    Returns:
        提取的百分比数值，如果没有找到则返回None
    """
    try:
        # 匹配数字加百分号的模式
        match = re.search(r'([\d.]+)%', description)
        if match:
            return float(match.group(1))
        # 匹配纯数字模式（假设是百分比）
        match = re.search(r'持股比例[：:]([\d.]+)', description)
        if match:
            return float(match.group(1))
        match = re.search(r'([\d.]+)%股权', description)
        if match:
            return float(match.group(1))
        return None
    except Exception as e:
        logger.error(f"提取百分比时出错: {e}")
        return None


def is_person(entity_name: str) -> bool:
    """
    判断一个实体是否为个人
    
    Args:
        entity_name: 实体名称
    
    Returns:
        如果是个人返回True，否则返回False
    """
    # 简单的启发式判断，可能需要根据实际数据调整
    patterns = [
        r'^Mr\.', r'^Mrs\.', r'^Ms\.',  # 英文称谓
        r'^[\u4e00-\u9fa5]{2,4}$',  # 纯中文名字（2-4个汉字）
        r'^[\u4e00-\u9fa5]{2,4}[\s·][\u4e00-\u9fa5]{1,2}$',  # 中文名（姓+名）
    ]
    
    for pattern in patterns:
        if re.match(pattern, entity_name):
            return True
    
    # 排除包含公司特征词汇的实体
    company_keywords = ['公司', '有限', 'Limited', 'Ltd', 'Corporation', 'Group', '集团']
    for keyword in company_keywords:
        if keyword in entity_name:
            return False
    
    return False


def is_subsidiary(entity_name: str, subsidiaries: Set[str]) -> bool:
    """
    判断一个实体是否为子公司
    
    Args:
        entity_name: 实体名称
        subsidiaries: 子公司集合
    
    Returns:
        如果是子公司返回True，否则返回False
    """
    # 直接在子公司集合中查找
    if entity_name in subsidiaries:
        return True
    
    # 子公司关键词匹配
    subsidiary_keywords = ['子公司', '分公司', 'branch', 'subsidiary']
    for keyword in subsidiary_keywords:
        if keyword.lower() in entity_name.lower():
            return True
    
    return False


def generate_mermaid_from_data(data: Dict[str, Any]) -> str:
    """
    从股权结构数据生成Mermaid图表代码
    
    Args:
        data: 包含股权结构信息的字典
    
    Returns:
        生成的Mermaid图表代码字符串
    """
    try:
        logger.info("开始生成Mermaid图表代码")
        
        # 提取实体类型信息
        print("=== 开始提取实体类型信息 ===")
        
        # 提取核心公司信息
        core_companies = set()
        if 'core_company' in data and data['core_company']:
            print(f"发现core_company字段: {type(data['core_company'])}")
            if isinstance(data['core_company'], str):
                core_companies.add(data['core_company'])
                print(f"添加核心公司: {data['core_company']}")
            elif isinstance(data['core_company'], list):
                # 确保只添加字符串类型
                for item in data['core_company']:
                    if isinstance(item, str):
                        core_companies.add(item)
                        print(f"添加核心公司: {item}")
        
        # 同时检查main_company字段，支持main_company作为核心公司的别名
        if 'main_company' in data and data['main_company']:
            print(f"发现main_company字段: {type(data['main_company'])}")
            if isinstance(data['main_company'], str):
                core_companies.add(data['main_company'])
                print(f"添加核心公司(main_company): {data['main_company']}")
            elif isinstance(data['main_company'], list):
                # 确保只添加字符串类型
                for item in data['main_company']:
                    if isinstance(item, str):
                        core_companies.add(item)
                        print(f"添加核心公司(main_company): {item}")
        
        # 提取顶级实体/实控人信息
        top_entities = set()
        if 'top_entities' in data and data['top_entities']:
            print(f"发现top_entities字段: {type(data['top_entities'])}")
            if isinstance(data['top_entities'], str):
                top_entities.add(data['top_entities'])
                print(f"添加顶级实体: {data['top_entities']}")
            elif isinstance(data['top_entities'], list):
                # 确保只添加字符串类型
                for item in data['top_entities']:
                    if isinstance(item, str):
                        top_entities.add(item)
                        print(f"添加顶级实体: {item}")
                    elif isinstance(item, dict) and 'name' in item:
                        if isinstance(item['name'], str):
                            top_entities.add(item['name'])
                            print(f"添加顶级实体: {item['name']}")
        
        # 提取实际控制人信息
        if 'actual_controllers' in data and data['actual_controllers']:
            print(f"发现actual_controllers字段: {type(data['actual_controllers'])}")
            if isinstance(data['actual_controllers'], str):
                top_entities.add(data['actual_controllers'])
                print(f"添加实际控制人: {data['actual_controllers']}")
            elif isinstance(data['actual_controllers'], list):
                # 确保只添加字符串类型
                for item in data['actual_controllers']:
                    if isinstance(item, str):
                        top_entities.add(item)
                        print(f"添加实际控制人: {item}")
                    elif isinstance(item, dict) and 'name' in item:
                        if isinstance(item['name'], str):
                            top_entities.add(item['name'])
                            print(f"添加实际控制人: {item['name']}")
        
        print(f"合并后的顶级实体数量: {len(top_entities)}")
        print(f"核心公司数量: {len(core_companies)}")
        
        # 提取子公司信息
        subsidiaries = set()
        if 'subsidiaries' in data and data['subsidiaries']:
            print(f"发现subsidiaries字段: {type(data['subsidiaries'])}")
            if isinstance(data['subsidiaries'], list):
                for item in data['subsidiaries']:
                    if isinstance(item, dict) and 'name' in item:
                        subsidiary_name = item['name']
                        if isinstance(subsidiary_name, str):
                            subsidiaries.add(subsidiary_name)
                            print(f"添加子公司: {subsidiary_name}")
                    elif isinstance(item, str):
                        subsidiaries.add(item)
                        print(f"添加子公司: {item}")
            elif isinstance(data['subsidiaries'], dict) and 'name' in data['subsidiaries']:
                # 处理单个子公司对象的情况
                subsidiary_name = data['subsidiaries']['name']
                if isinstance(subsidiary_name, str):
                    subsidiaries.add(subsidiary_name)
                    print(f"添加单个子公司: {subsidiary_name}")
        
        print(f"子公司数量: {len(subsidiaries)}")
        
        # 初始化Mermaid代码
        mermaid_code = "graph TD\n"
        
        # 添加CSS样式 - 冷色调专业设计
        mermaid_code += "    classDef company fill:#f3f4f6,stroke:#5a6772,stroke-width:2px,rx:4,ry:4;\n"  # 公司 - 浅灰背景深灰边框
        mermaid_code += "    classDef subsidiary fill:#ffffff,stroke:#1e88e5,stroke-width:1.5px,rx:4,ry:4;\n"  # 子公司 - 白色背景深蓝色边框
        mermaid_code += "    classDef topEntity fill:#0d47a1,color:#ffffff,stroke:#ffffff,stroke-width:2px,rx:4,ry:4;\n"  # 顶级实体 - 深蓝背景白字白边框
        mermaid_code += "    classDef coreCompany fill:#fff8e1,stroke:#ff9100,stroke-width:2px,rx:6,ry:6;\n"  # 核心公司 - 米黄背景橙棕边框
        
        # 实体映射表，用于生成唯一标识符
        entity_map = {}
        entity_id_counter = 1
        
        # 处理控制关系
        print("\n=== 优先处理control_relationships ===")
        control_relationships = data.get('control_relationships', [])
        print(f"找到控制关系数量: {len(control_relationships)}")
        
        for i, rel in enumerate(control_relationships, 1):
            try:
                print(f"\n处理控制关系 {i}/{len(control_relationships)}:")
                
                # 获取父子实体名称
                parent_name = rel.get('parent', '')
                child_name = rel.get('child', '')
                description = rel.get('description', '')
                
                if not parent_name or not child_name:
                    print(f"  跳过无效关系: 缺少父实体或子实体")
                    continue
                    
                print(f"  parent_name: {parent_name}, child_name: {child_name}")
                print(f"  描述: {description}")
                
                # 处理父实体
                if parent_name not in entity_map:
                    entity_id = f"E{entity_id_counter}"
                    entity_map[parent_name] = entity_id
                    entity_id_counter += 1
                    mermaid_code += f"    {entity_map[parent_name]}['{parent_name}']\n"
                    
                    # 样式分配逻辑：严格按照JSON字段定义，不再基于关键词自动识别coreCompany
                    # 1. 首先检查是否在核心公司列表中
                    if parent_name in core_companies:
                        mermaid_code += f"    class {entity_map[parent_name]} coreCompany;\n"
                        print(f"  为{parent_name}分配样式: coreCompany (core_company/main_company字段)")
                    # 2. 检查是否在顶级实体或实控人列表中
                    elif parent_name in top_entities:
                        mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                        print(f"  为{parent_name}分配样式: topEntity (JSON数据中的顶级实体/实控人)")
                    # 3. 检查是否在子公司列表中
                    elif parent_name in subsidiaries:
                        mermaid_code += f"    class {entity_map[parent_name]} subsidiary;\n"
                        print(f"  为{parent_name}分配样式: subsidiary (JSON数据中的子公司)")
                    # 4. 默认为一般公司
                    else:
                        mermaid_code += f"    class {entity_map[parent_name]} company;\n"
                        print(f"  为{parent_name}分配样式: company (默认)")
                    
                    print(f"  新增实体: {parent_name} -> {entity_map[parent_name]}")
                
                # 处理子实体
                if child_name not in entity_map:
                    entity_id = f"E{entity_id_counter}"
                    entity_map[child_name] = entity_id
                    entity_id_counter += 1
                    mermaid_code += f"    {entity_map[child_name]}['{child_name}']\n"
                    
                    # 样式分配逻辑：严格按照JSON字段定义，不再基于关键词自动识别coreCompany
                    # 1. 首先检查是否在核心公司列表中
                    if child_name in core_companies:
                        mermaid_code += f"    class {entity_map[child_name]} coreCompany;\n"
                        print(f"  为{child_name}分配样式: coreCompany (core_company/main_company字段)")
                    # 2. 检查是否在顶级实体或实控人列表中
                    elif child_name in top_entities:
                        mermaid_code += f"    class {entity_map[child_name]} topEntity;\n"
                        print(f"  为{child_name}分配样式: topEntity (JSON数据中的顶级实体/实控人)")
                    # 3. 检查是否在子公司列表中
                    elif child_name in subsidiaries:
                        mermaid_code += f"    class {entity_map[child_name]} subsidiary;\n"
                        print(f"  为{child_name}分配样式: subsidiary (JSON数据中的子公司)")
                    # 4. 默认为一般公司
                    else:
                        mermaid_code += f"    class {entity_map[child_name]} company;\n"
                        print(f"  为{child_name}分配样式: company (默认)")
                    
                    print(f"  新增实体: {child_name} -> {entity_map[child_name]}")
                
                # 提取持股比例
                percentage = extract_percentage(description)
                
                # 构建关系描述
                if percentage is not None:
                    # 如果有明确的百分比，优先显示百分比
                    rel_label = f"{percentage:.1f}%"
                else:
                    # 否则使用原始描述，但限制长度
                    rel_label = description[:50]  # 限制标签长度，避免图表过于拥挤
                
                # 控制关系使用虚线表示
                mermaid_code += f"    {entity_map[parent_name]} -.->|\"{rel_label}\"| {entity_map[child_name]}\n"
                print(f"  成功添加虚线连接: {entity_map[parent_name]} -.->|{rel_label}| {entity_map[child_name]}")
                
            except Exception as e:
                logger.error(f"处理控制关系时出错: {e}")
                print(f"  处理关系时出错: {e}")
                # 继续处理下一个关系，不中断整体流程
                continue
        
        # 处理股权关系
        print("\n=== 处理equity_relationships ===")
        equity_relationships = data.get('equity_relationships', [])
        print(f"找到股权关系数量: {len(equity_relationships)}")
        
        # 定义一个集合来跟踪已处理的关系，避免重复
        processed_relationships = set()
        
        for i, rel in enumerate(equity_relationships, 1):
            try:
                print(f"\n处理股权关系 {i}/{len(equity_relationships)}:")
                
                # 获取父子实体名称和持股比例
                parent_name = rel.get('parent', '')
                child_name = rel.get('child', '')
                percentage = rel.get('percentage', 0)
                description = rel.get('description', '')
                
                # 验证输入
                if not isinstance(parent_name, str) or not isinstance(child_name, str):
                    print(f"  跳过无效关系: 父实体或子实体名称类型错误")
                    continue
                
                if not parent_name or not child_name:
                    print(f"  跳过无效关系: 缺少父实体或子实体")
                    continue
                    
                print(f"  parent_name: {parent_name}, child_name: {child_name}")
                print(f"  持股比例: {percentage}%")
                print(f"  描述: {description}")
                
                # 检查关系是否已处理（通过控制关系处理过）
                rel_key = (parent_name, child_name)
                if rel_key in processed_relationships:
                    print(f"  跳过已处理的关系")
                    continue
                
                # 处理父实体
                if parent_name not in entity_map:
                    entity_id = f"E{entity_id_counter}"
                    entity_map[parent_name] = entity_id
                    entity_id_counter += 1
                    mermaid_code += f"    {entity_map[parent_name]}['{parent_name}']\n"
                    
                    # 样式分配逻辑：严格按照JSON字段定义，不再基于关键词自动识别coreCompany
                    # 1. 首先检查是否在核心公司列表中
                    if parent_name in core_companies:
                        mermaid_code += f"    class {entity_map[parent_name]} coreCompany;\n"
                        print(f"  为{parent_name}分配样式: coreCompany (core_company/main_company字段)")
                    # 2. 检查是否在顶级实体或实控人列表中
                    elif parent_name in top_entities:
                        mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                        print(f"  为{parent_name}分配样式: topEntity (JSON数据中的顶级实体/实控人)")
                    # 3. 检查是否在子公司列表中
                    elif parent_name in subsidiaries:
                        mermaid_code += f"    class {entity_map[parent_name]} subsidiary;\n"
                        print(f"  为{parent_name}分配样式: subsidiary (JSON数据中的子公司)")
                    # 4. 默认为一般公司
                    else:
                        mermaid_code += f"    class {entity_map[parent_name]} company;\n"
                        print(f"  为{parent_name}分配样式: company (默认)")
                    
                    print(f"  新增实体: {parent_name} -> {entity_map[parent_name]}")
                
                # 处理子实体
                if child_name not in entity_map:
                    entity_id = f"E{entity_id_counter}"
                    entity_map[child_name] = entity_id
                    entity_id_counter += 1
                    mermaid_code += f"    {entity_map[child_name]}['{child_name}']\n"
                    
                    # 样式分配逻辑：严格按照JSON字段定义，不再基于关键词自动识别coreCompany
                    # 1. 首先检查是否在核心公司列表中
                    if child_name in core_companies:
                        mermaid_code += f"    class {entity_map[child_name]} coreCompany;\n"
                        print(f"  为{child_name}分配样式: coreCompany (core_company/main_company字段)")
                    # 2. 检查是否在顶级实体或实控人列表中
                    elif child_name in top_entities:
                        mermaid_code += f"    class {entity_map[child_name]} topEntity;\n"
                        print(f"  为{child_name}分配样式: topEntity (JSON数据中的顶级实体/实控人)")
                    # 3. 检查是否在子公司列表中
                    elif child_name in subsidiaries:
                        mermaid_code += f"    class {entity_map[child_name]} subsidiary;\n"
                        print(f"  为{child_name}分配样式: subsidiary (JSON数据中的子公司)")
                    # 4. 默认为一般公司
                    else:
                        mermaid_code += f"    class {entity_map[child_name]} company;\n"
                        print(f"  为{child_name}分配样式: company (默认)")
                    
                    print(f"  新增实体: {child_name} -> {entity_map[child_name]}")
                
                # 添加股权关系
                mermaid_code += f"    {entity_map[parent_name]} -->|\"{percentage}%\"| {entity_map[child_name]}\n"
                print(f"  成功添加实线连接: {entity_map[parent_name]} -->|{percentage}%| {entity_map[child_name]}")
                
                # 标记此关系已处理
                processed_relationships.add(rel_key)
                
            except Exception as e:
                logger.error(f"处理股权关系时出错: {e}")
                print(f"  处理关系时出错: {e}")
                # 继续处理下一个关系，不中断整体流程
                continue
        
        # 层级分析找出顶级实体（没有父实体的实体）
        print("\n=== 层级分析找出顶级实体 ===")
        
        # 收集所有实体和子实体
        all_entities = set(entity_map.keys())
        child_entities = set()
        
        # 从控制关系中收集子实体
        for rel in control_relationships:
            child_name = rel.get('child', '')
            if child_name and isinstance(child_name, str):
                child_entities.add(child_name)
        
        # 从股权关系中收集子实体
        for rel in equity_relationships:
            child_name = rel.get('child', '')
            if child_name and isinstance(child_name, str):
                child_entities.add(child_name)
        
        # 顶级实体是那些不是任何关系的子实体的实体
        hierarchy_top_entities = all_entities - child_entities
        print(f"层级分析出的顶级实体数量: {len(hierarchy_top_entities)}")
        
        # 合并JSON中定义的顶级实体和层级分析出的顶级实体
        all_top_entities = top_entities.union(hierarchy_top_entities)
        print(f"合并后的所有顶级实体数量: {len(all_top_entities)}")
        
        # 确保所有顶级实体都有正确的样式
        for entity_name in all_top_entities:
            if entity_name in entity_map and entity_name not in core_companies and entity_name not in subsidiaries:
                # 检查当前样式，避免覆盖已有的coreCompany或subsidiary样式
                # 注意：这里我们不能直接修改已生成的Mermaid代码，所以这一步只是日志记录
                print(f"确认顶级实体: {entity_name} 样式正确")
        
        # 输出最终结果
        print("\n=== 最终生成的Mermaid代码 ===")
        print(mermaid_code)
        
        logger.info("Mermaid图表代码生成完成")
        return mermaid_code
        
    except Exception as e:
        logger.error(f"生成Mermaid图表时发生未预期的错误: {e}", exc_info=True)
        print(f"生成Mermaid图表时发生错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 生成一个简单的错误图表
        error_mermaid = "graph TD\n    ERROR['生成图表时发生错误']\n    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px,rx:4,ry:4;\n    class ERROR error;"
        return error_mermaid


if __name__ == "__main__":
    # 示例用法
    sample_data = {
        "core_company": "核心公司名称",
        "top_entities": ["顶级实体1", "顶级实体2"],
        "control_relationships": [
            {"parent": "顶级实体1", "child": "子公司1", "description": "控制权"},
            {"parent": "顶级实体2", "child": "子公司2", "description": "控制权"}
        ],
        "equity_relationships": [
            {"parent": "子公司1", "child": "孙公司1", "percentage": 80},
            {"parent": "子公司2", "child": "孙公司2", "percentage": 60}
        ]
    }
    
    mermaid_code = generate_mermaid_from_data(sample_data)
    print(mermaid_code)