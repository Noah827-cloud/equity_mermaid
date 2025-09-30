# 辅助函数：从字符串中提取百分比
def extract_percentage(percentage):
    """从字符串或数字中提取百分比值"""
    import re
    if isinstance(percentage, (int, float)):
        return float(percentage)
    elif isinstance(percentage, str):
        # 尝试从字符串中提取数字
        match = re.search(r'(\d+(?:\.\d+)?)%?', percentage)
        if match:
            return float(match.group(1))
    return 0

# 辅助函数：检查实体是否为个人
def is_person(name):
    """判断实体是否为个人"""
    # 简单判断：如果包含特定关键词，则认为是个人
    person_keywords = ["Mr.", "Mrs.", "Ms.", "Dr.", "博士", "教授", "先生", "女士", "小姐", "董事"]
    return any(keyword in name for keyword in person_keywords)

# 辅助函数：检查实体是否为子公司
def is_subsidiary(name, entity_relationships, main_company):
    """判断实体是否为子公司"""
    # 如果entity_relationships中存在从其他公司（包括主公司）到该实体的关系，则认为是子公司
    for relationship in entity_relationships:
        if relationship.get("child") == name:
            return True
    return False

def generate_mermaid_from_data(data):
    """
    从股权结构数据生成Mermaid图表代码
    
    Args:
        data (dict): 包含股权结构信息的字典
        
    Returns:
        str: Mermaid图表代码
    """
    try:
        # 初始化Mermaid代码
        mermaid_code = "graph TD\n"
        
        # 添加CSS样式 - 冷色调专业设计
        mermaid_code += "    classDef company fill:#f3f4f6,stroke:#5a6772,stroke-width:2px,rx:4,ry:4;\n"  # 公司 - 浅灰背景深灰边框
        mermaid_code += "    classDef subsidiary fill:#ffffff,stroke:#1e88e5,stroke-width:1.5px,rx:4,ry:4;\n"  # 子公司 - 白色背景深蓝色边框
        mermaid_code += "    classDef topEntity fill:#0d47a1,color:#ffffff,stroke:#ffffff,stroke-width:2px,rx:4,ry:4;\n"  # 顶级实体 - 深蓝背景白字白边框
        mermaid_code += "    classDef coreCompany fill:#fff8e1,stroke:#ff9100,stroke-width:2px,rx:6,ry:6;\n"  # 核心公司 - 米黄背景橙棕边框
        
        # 创建实体映射，用于存储实体ID和名称
        entity_map = {}
        entity_id_counter = 1
        
        # 存储已添加的关系，避免重复
        added_relationships = set()
        
        # 存储所有实体，用于后续分析
        all_entities = set()
        
        # 从JSON数据中提取实体类型信息
        core_companies = set()
        top_entities = set()
        subsidiaries = set()
        actual_controllers = set()
        
        print("=== 开始提取实体类型信息 ===")
        
        # 提取核心公司信息
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
        
        # 提取子公司信息
        subsidiaries_set = set()
        if 'subsidiaries' in data and data['subsidiaries']:
            print(f"发现subsidiaries字段: {type(data['subsidiaries'])}")
            if isinstance(data['subsidiaries'], list):
                for item in data['subsidiaries']:
                    if isinstance(item, dict) and 'name' in item and isinstance(item['name'], str):
                        subsidiaries_set.add(item['name'])
                        print(f"添加子公司: {item['name']}")
                    elif isinstance(item, str):
                        subsidiaries_set.add(item)
                        print(f"添加子公司: {item}")
            elif isinstance(data['subsidiaries'], dict):
                # 处理单个子公司对象的情况
                if 'name' in data['subsidiaries'] and isinstance(data['subsidiaries']['name'], str):
                    subsidiary_name = data['subsidiaries']['name']
                    subsidiaries_set.add(subsidiary_name)
                    print(f"添加单个子公司: {subsidiary_name}")
                # 处理字典格式，尝试获取名称字段
                else:
                    for sub_key, sub_value in data['subsidiaries'].items():
                        try:
                            if isinstance(sub_value, dict) and 'name' in sub_value and isinstance(sub_value['name'], str):
                                subsidiaries_set.add(sub_value['name'])
                                print(f"添加子公司: {sub_value['name']}")
                            elif isinstance(sub_value, str):
                                subsidiaries_set.add(sub_value)
                                print(f"添加子公司: {sub_value}")
                        except Exception as e:
                            print(f"处理子公司字典项时出错: {e}")
            elif isinstance(data['subsidiaries'], str):
                subsidiaries_set.add(data['subsidiaries'])
                print(f"添加子公司: {data['subsidiaries']}")
        # 合并到subsidiaries集合
        subsidiaries.update(subsidiaries_set)
        
        # 提取实际控制人信息
        if 'actual_controllers' in data and data['actual_controllers']:
            print(f"发现actual_controllers字段: {type(data['actual_controllers'])}")
            if isinstance(data['actual_controllers'], str):
                actual_controllers.add(data['actual_controllers'])
                print(f"添加实际控制人: {data['actual_controllers']}")
            elif isinstance(data['actual_controllers'], list):
                # 确保只添加字符串类型
                for item in data['actual_controllers']:
                    if isinstance(item, str):
                        actual_controllers.add(item)
                        print(f"添加实际控制人: {item}")
        
        # 合并顶级实体和实际控制人
        top_entities.update(actual_controllers)
        print(f"合并后的顶级实体数量: {len(top_entities)}")
        print(f"核心公司数量: {len(core_companies)}")
        print(f"子公司数量: {len(subsidiaries)}")
        
        # 首先收集所有实体，用于分析层级关系
        if 'control_relationships' in data and data['control_relationships']:
            for rel in data['control_relationships']:
                parent_name = rel.get('parent', '')
                child_name = rel.get('child', '')
                if parent_name:
                    all_entities.add(parent_name)
                if child_name:
                    all_entities.add(child_name)
        
        if 'entity_relationships' in data and data['entity_relationships']:
            for rel in data['entity_relationships']:
                parent_name = rel.get('parent', '')
                child_name = rel.get('child', '')
                if parent_name:
                    all_entities.add(parent_name)
                if child_name:
                    all_entities.add(child_name)
        
        # 分析实体层级关系：判断哪些是顶级实体（没有父实体的）
        child_entities = set()
        if 'control_relationships' in data and data['control_relationships']:
            for rel in data['control_relationships']:
                child_name = rel.get('child', '')
                if child_name:
                    child_entities.add(child_name)
        
        if 'entity_relationships' in data and data['entity_relationships']:
            for rel in data['entity_relationships']:
                child_name = rel.get('child', '')
                if child_name:
                    child_entities.add(child_name)
        
        # 顶级实体是那些只作为父实体而不作为子实体的
        hierarchical_top_entities = all_entities - child_entities
        
        # 合并JSON中定义的顶级实体和层级分析出的顶级实体
        all_top_entities = top_entities.union(hierarchical_top_entities)
        print(f"层级分析出的顶级实体数量: {len(hierarchical_top_entities)}")
        print(f"合并后的所有顶级实体数量: {len(all_top_entities)}")
        
        # 首先处理控制关系（优先级高）
        if 'control_relationships' in data and data['control_relationships']:
            print("\n=== 优先处理control_relationships ===")
            control_relationships = data['control_relationships']
            print(f"找到控制关系数量: {len(control_relationships)}")
            
            for i, rel in enumerate(control_relationships):
                try:
                    parent_name = rel.get('parent', '')
                    child_name = rel.get('child', '')
                    description = rel.get('description', '')
                    
                    print(f"\n处理控制关系 {i+1}/{len(control_relationships)}:")
                    print(f"parent_name: {parent_name}, child_name: {child_name}")
                    print(f"描述: {description}")
                    
                    # 确保名称存在且为字符串
                    if not isinstance(parent_name, str) or not isinstance(child_name, str) or not parent_name or not child_name:
                        print("跳过：缺少父或子实体名称，或名称不是字符串类型")
                        continue
                    
                    # 为实体分配ID（如果尚未分配）
                    if parent_name not in entity_map:
                        entity_map[parent_name] = f"E{entity_id_counter}"
                        entity_id_counter += 1
                        # 添加实体定义
                        mermaid_code += f"    {entity_map[parent_name]}[\"{parent_name}\"]\n"
                        
                        # 增强的样式分配逻辑 - 优先基于JSON数据
                        # 1. 首先检查是否在顶级实体或实控人列表中
                        if parent_name in all_top_entities:
                            mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                            print(f"为{parent_name}分配样式: topEntity (JSON数据中的顶级实体/实控人)")
                        # 2. 检查是否在核心公司列表中
                        elif parent_name in core_companies:
                            mermaid_code += f"    class {entity_map[parent_name]} coreCompany;\n"
                            print(f"为{parent_name}分配样式: coreCompany (JSON数据中的核心公司)")
                        # 3. 检查是否在子公司列表中
                        elif parent_name in subsidiaries:
                            mermaid_code += f"    class {entity_map[parent_name]} subsidiary;\n"
                            print(f"为{parent_name}分配样式: subsidiary (JSON数据中的子公司)")
                        # 4. 回退到关键词识别
                        elif is_person(parent_name):
                            mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                            print(f"为{parent_name}分配样式: topEntity (个人实体)")
                        elif "实控" in parent_name or "控制" in parent_name or "控股" in parent_name:
                            mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                            print(f"为{parent_name}分配样式: topEntity (实控人关键词)")
                        elif "财政部" in parent_name or "MOF" in parent_name:
                            mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                            print(f"为{parent_name}分配样式: topEntity (财政部)")
                        # 5. 默认为一般公司
                        else:
                            mermaid_code += f"    class {entity_map[parent_name]} company;\n"
                            print(f"为{parent_name}分配样式: company (一般公司)")
                        
                        print(f"新增实体: {parent_name} -> {entity_map[parent_name]}")
                    
                    if child_name not in entity_map:
                        entity_map[child_name] = f"E{entity_id_counter}"
                        entity_id_counter += 1
                        # 添加实体定义
                        mermaid_code += f"    {entity_map[child_name]}[\"{child_name}\"]\n"
                        
                        # 样式分配逻辑：严格按照JSON字段定义，不再基于关键词自动识别coreCompany
                        # 1. 首先检查是否在核心公司列表中
                        if child_name in core_companies:
                            mermaid_code += f"    class {entity_map[child_name]} coreCompany;\n"
                            print(f"为{child_name}分配样式: coreCompany (core_company/main_company字段)")
                        # 2. 检查是否在顶级实体或实控人列表中
                        elif child_name in all_top_entities:
                            mermaid_code += f"    class {entity_map[child_name]} topEntity;\n"
                            print(f"为{child_name}分配样式: topEntity (JSON数据中的顶级实体/实控人)")
                        # 3. 检查是否在子公司列表中
                        elif child_name in subsidiaries:
                            mermaid_code += f"    class {entity_map[child_name]} subsidiary;\n"
                            print(f"为{child_name}分配样式: subsidiary (JSON数据中的子公司)")
                        # 4. 默认为一般公司
                        else:
                            mermaid_code += f"    class {entity_map[child_name]} company;\n"
                            print(f"为{child_name}分配样式: company (默认)")
                        
                        print(f"新增实体: {child_name} -> {entity_map[child_name]}")
                    
                    # 获取实体ID
                    parent_id = entity_map[parent_name]
                    child_id = entity_map[child_name]
                    
                    # 使用实体名称对作为关系键，确保控制关系优先
                    basic_relationship = (parent_name, child_name)
                    
                    if basic_relationship not in added_relationships:
                        print(f"添加控制关系: {basic_relationship}")
                        
                        # 添加关系对到已添加集合
                        added_relationships.add(basic_relationship)
                        
                        # 使用description作为标签，确保是字符串
                        label = f"\"{str(description)}\"" if description else "\"控制\""
                        
                        # 确保使用虚线连接 - 使用-.->明确指定虚线
                        mermaid_code += f"    {parent_id} -.->|{label}| {child_id}\n"
                        
                        print(f"成功添加虚线连接: {parent_id} -.->|{label}| {child_id}")
                    else:
                        print(f"跳过：关系 {basic_relationship} 已经存在")
                except Exception as e:
                    print(f"处理单个控制关系时出错: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 然后处理实体关系，但忽略已在控制关系中存在的关系
        if 'entity_relationships' in data and data['entity_relationships']:
            print("\n=== 处理entity_relationships（忽略已存在的控制关系）===")
            entity_relationships = data['entity_relationships']
            print(f"找到实体关系数量: {len(entity_relationships)}")
            
            for i, relationship in enumerate(entity_relationships):
                try:
                    parent_name = relationship.get('parent', '')
                    child_name = relationship.get('child', '')
                    percentage = extract_percentage(relationship.get('percentage', 0))
                    
                    print(f"\n处理实体关系 {i+1}/{len(entity_relationships)}:")
                    print(f"parent_name: {parent_name}, child_name: {child_name}, percentage: {percentage}")
                    
                    # 确保名称存在且为字符串
                    if not isinstance(parent_name, str) or not isinstance(child_name, str) or not parent_name or not child_name:
                        print("跳过：缺少父或子实体名称，或名称不是字符串类型")
                        continue
                    
                    # 检查是否已在控制关系中存在
                    basic_relationship = (parent_name, child_name)
                    if basic_relationship in added_relationships:
                        print(f"跳过实体关系: {basic_relationship} (已在控制关系中存在)")
                        continue
                    
                    # 为实体分配ID（如果尚未分配）
                    if parent_name not in entity_map:
                        entity_map[parent_name] = f"E{entity_id_counter}"
                        entity_id_counter += 1
                        # 添加实体定义
                        mermaid_code += f"    {entity_map[parent_name]}[\"{parent_name}\"]\n"
                        
                        # 增强的样式分配逻辑 - 优先基于JSON数据
                        # 1. 首先检查是否在顶级实体或实控人列表中
                        if parent_name in all_top_entities:
                            mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                            print(f"为{parent_name}分配样式: topEntity (JSON数据中的顶级实体/实控人)")
                        # 2. 检查是否在核心公司列表中
                        elif parent_name in core_companies:
                            mermaid_code += f"    class {entity_map[parent_name]} coreCompany;\n"
                            print(f"为{parent_name}分配样式: coreCompany (JSON数据中的核心公司)")
                        # 3. 检查是否在子公司列表中
                        elif parent_name in subsidiaries:
                            mermaid_code += f"    class {entity_map[parent_name]} subsidiary;\n"
                            print(f"为{parent_name}分配样式: subsidiary (JSON数据中的子公司)")
                        # 4. 回退到关键词识别
                        elif is_person(parent_name):
                            mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                            print(f"为{parent_name}分配样式: topEntity (个人实体)")
                        elif "实控" in parent_name or "控制" in parent_name or "控股" in parent_name:
                            mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                            print(f"为{parent_name}分配样式: topEntity (实控人关键词)")
                        elif "财政部" in parent_name or "MOF" in parent_name:
                            mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                            print(f"为{parent_name}分配样式: topEntity (财政部)")
                        # 5. 默认为一般公司
                        else:
                            mermaid_code += f"    class {entity_map[parent_name]} company;\n"
                            print(f"为{parent_name}分配样式: company (一般公司)")
                        
                        print(f"新增实体: {parent_name} -> {entity_map[parent_name]}")
                    
                    if child_name not in entity_map:
                        entity_map[child_name] = f"E{entity_id_counter}"
                        entity_id_counter += 1
                        # 添加实体定义
                        mermaid_code += f"    {entity_map[child_name]}[\"{child_name}\"]\n"
                        
                        # 样式分配逻辑：严格按照JSON字段定义，不再基于关键词自动识别coreCompany
                        # 1. 首先检查是否在核心公司列表中
                        if child_name in core_companies:
                            mermaid_code += f"    class {entity_map[child_name]} coreCompany;\n"
                            print(f"为{child_name}分配样式: coreCompany (core_company/main_company字段)")
                        # 2. 检查是否在顶级实体或实控人列表中
                        elif child_name in all_top_entities:
                            mermaid_code += f"    class {entity_map[child_name]} topEntity;\n"
                            print(f"为{child_name}分配样式: topEntity (JSON数据中的顶级实体/实控人)")
                        # 3. 检查是否在子公司列表中
                        elif child_name in subsidiaries:
                            mermaid_code += f"    class {entity_map[child_name]} subsidiary;\n"
                            print(f"为{child_name}分配样式: subsidiary (JSON数据中的子公司)")
                        # 4. 默认为一般公司
                        else:
                            mermaid_code += f"    class {entity_map[child_name]} company;\n"
                            print(f"为{child_name}分配样式: company (默认)")
                        
                        print(f"新增实体: {child_name} -> {entity_map[child_name]}")
                    
                    # 获取实体ID
                    parent_id = entity_map[parent_name]
                    child_id = entity_map[child_name]
                    
                    # 添加关系对到已添加集合
                    added_relationships.add(basic_relationship)
                    print(f"添加实体关系: {basic_relationship}")
                    
                    # 添加实线连接
                    mermaid_code += f"    {parent_id} -->|{percentage:.1f}%| {child_id}\n"
                    print(f"成功添加实线连接: {parent_id} -->|{percentage:.1f}%| {child_id}")
                except Exception as e:
                    print(f"处理单个实体关系时出错: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 移除图例说明，按照用户要求
        
        # 添加缺失的子公司 - 确保subsidiaries列表中的实体都被渲染
        print("\n=== 处理缺失的子公司 ===")
        # 先创建一个字典，存储子公司名称到百分比的映射
        subsidiary_percentage_map = {}
        if 'subsidiaries' in data and data['subsidiaries']:
            if isinstance(data['subsidiaries'], list):
                for item in data['subsidiaries']:
                    if isinstance(item, dict) and 'name' in item and 'percentage' in item:
                        subsidiary_percentage_map[item['name']] = item['percentage']
                    
        for subsidiary_name in subsidiaries:
            if subsidiary_name not in entity_map and subsidiary_name not in core_companies:
                print(f"为子公司添加实体定义: {subsidiary_name}")
                entity_map[subsidiary_name] = f"E{entity_id_counter}"
                entity_id_counter += 1
                
                # 添加实体定义
                mermaid_code += f"    {entity_map[subsidiary_name]}[\"{subsidiary_name}\"]\n"
                mermaid_code += f"    class {entity_map[subsidiary_name]} subsidiary;\n"
                
                # 如果有核心公司，默认与核心公司建立关系
                if core_companies:
                    core_company_name = next(iter(core_companies))  # 获取第一个核心公司
                    if core_company_name in entity_map:
                        core_company_id = entity_map[core_company_name]
                        subsidiary_id = entity_map[subsidiary_name]
                        
                        # 检查这个关系是否已经存在
                        relationship_key = (core_company_name, subsidiary_name)
                        if relationship_key not in added_relationships:
                            print(f"添加核心公司到子公司的默认关系: {core_company_name} -> {subsidiary_name}")
                            
                            # 使用子公司数据中的百分比值，如果有的话
                            if subsidiary_name in subsidiary_percentage_map:
                                percentage = extract_percentage(subsidiary_percentage_map[subsidiary_name])
                                mermaid_code += f"    {core_company_id} -->|{percentage:.1f}%| {subsidiary_id}\n"
                            else:
                                mermaid_code += f"    {core_company_id} -->|未指定| {subsidiary_id}\n"
                            
                            added_relationships.add(relationship_key)
        
        # 打印最终的mermaid代码用于调试
        print("\n=== 最终生成的Mermaid代码 ===")
        print(mermaid_code)
        
        return mermaid_code
    
    except Exception as e:
        print(f"生成Mermaid图表时出错: {str(e)}")
        import traceback
        traceback.print_exc()  # 打印完整的错误堆栈
        # 返回基本的错误图表
        return f"graph TD\n    error[\"生成图表时出错: {str(e)}\"]\n    classDef error fill:#ffebee,stroke:#f44336,stroke-width:2px\n    class error error"