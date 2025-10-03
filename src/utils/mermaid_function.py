import re

# 辅助函数：从字符串中提取百分比
def extract_percentage(percentage):
    """从字符串或数字中提取百分比值"""
    if isinstance(percentage, (int, float)):
        return float(percentage)
    elif isinstance(percentage, str):
        # 尝试从字符串中提取数字，支持多种格式
        # 1. 直接匹配百分比数字，如"12.34%"或"12.34 %"
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', percentage)
        if match:
            return float(match.group(1))
        # 2. 匹配纯数字，如"12.34"
        match = re.search(r'^(\d+(?:\.\d+)?)$', percentage.strip())
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
    
    根据用户要求：
    - 图像生成中核心公司就是main_company
    - top_entity就是股东
    - controller对应actual_controllers
    
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
        mermaid_code += "    classDef topEntity fill:#0d47a1,color:#ffffff,stroke:#ffffff,stroke-width:2px,rx:4,ry:4;\n"  # 顶级实体(股东) - 深蓝背景白字白边框
        mermaid_code += "    classDef coreCompany fill:#fff8e1,stroke:#ff9100,stroke-width:2px,rx:6,ry:6;\n"  # 核心公司 - 米黄背景橙棕边框
        
        # 创建实体映射，用于存储实体ID和名称
        entity_map = {}
        entity_id_counter = 1
        
        # 存储已添加的关系，避免重复
        added_relationships = set()
        
        # 提取核心信息（按照用户要求）
        main_company = data.get('main_company', '')
        shareholders = data.get('shareholders', [])
        controller = data.get('controller', '')
        subsidiaries = data.get('subsidiaries', [])
        
        # 根据用户要求设置：核心公司包括main_company和core_company
        core_companies = set()
        if main_company:
            core_companies.add(main_company)
            print(f"添加main_company到核心公司: {main_company}")
        # 添加core_company字段的值到核心公司集合
        core_company = data.get('core_company', '')
        if core_company:
            core_companies.add(core_company)
            print(f"添加core_company到核心公司: {core_company}")
        
        # 只添加一次核心公司，如果main_company和core_company相同，避免重复
        # 如果core_company存在且与main_company不同，则添加core_company
        if core_company and core_company != main_company and core_company not in entity_map:
            entity_map[core_company] = f"E{entity_id_counter}"
            entity_id_counter += 1
            mermaid_code += f"    {entity_map[core_company]}[\"{core_company}\"]\n"
            mermaid_code += f"    class {entity_map[core_company]} coreCompany;\n"
            print(f"提前添加core_company到图表: {core_company} -> {entity_map[core_company]} (coreCompany)")
        
        # 根据用户要求设置：top_entity就是股东
        # 提取所有股东名称
        shareholder_names = set()
        for shareholder in shareholders:
            if isinstance(shareholder, dict):
                shareholder_name = shareholder.get('name', '')
                if shareholder_name and isinstance(shareholder_name, str):
                    shareholder_names.add(shareholder_name)
            elif isinstance(shareholder, str):
                shareholder_names.add(shareholder)
        
        # 添加对top_level_entities的处理
        top_level_entity_names = set()
        if 'top_level_entities' in data:
            for entity in data['top_level_entities']:
                if isinstance(entity, dict):
                    entity_name = entity.get('name', '')
                    if entity_name and isinstance(entity_name, str):
                        top_level_entity_names.add(entity_name)
                elif isinstance(entity, str):
                    top_level_entity_names.add(entity)
        
        # 处理all_entities中的个人实体，将其标记为topEntity
        person_entity_names = set()
        if 'all_entities' in data:
            for entity in data['all_entities']:
                if isinstance(entity, dict) and entity.get('type') == 'person':
                    entity_name = entity.get('name', '')
                    if entity_name and isinstance(entity_name, str):
                        person_entity_names.add(entity_name)
        
        # 根据用户要求设置：controller对应actual_controllers
        actual_controllers = {controller} if controller else set()
        
        # 合并股东、顶级实体、控制人和个人实体作为顶级实体
        top_entities = shareholder_names.union(top_level_entity_names).union(actual_controllers).union(person_entity_names)
        
        # 提取子公司名称
        subsidiary_names = set()
        for subsidiary in subsidiaries:
            if isinstance(subsidiary, dict):
                subsidiary_name = subsidiary.get('name', '')
                if subsidiary_name and isinstance(subsidiary_name, str):
                    subsidiary_names.add(subsidiary_name)
            elif isinstance(subsidiary, str):
                subsidiary_names.add(subsidiary)
        
        print(f"=== 实体统计信息 ===")
        print(f"核心公司 (main_company): {main_company}")
        print(f"股东数量: {len(shareholder_names)}")
        print(f"控制人 (controller): {controller}")
        print(f"子公司数量: {len(subsidiary_names)}")
        
        # 1. 首先添加核心公司
        if main_company:
            entity_map[main_company] = f"E{entity_id_counter}"
            entity_id_counter += 1
            mermaid_code += f"    {entity_map[main_company]}[\"{main_company}\"]\n"
            mermaid_code += f"    class {entity_map[main_company]} coreCompany;\n"
            print(f"添加核心公司: {main_company} -> {entity_map[main_company]}")
        
        # 2. 添加所有股东（标记为topEntity）
        for shareholder in shareholders:
            if isinstance(shareholder, dict):
                shareholder_name = shareholder.get('name', '')
                percentage = extract_percentage(shareholder.get('percentage', 0))
            else:
                shareholder_name = str(shareholder)
                percentage = 0
            
            if shareholder_name and shareholder_name not in entity_map:
                entity_map[shareholder_name] = f"E{entity_id_counter}"
                entity_id_counter += 1
                mermaid_code += f"    {entity_map[shareholder_name]}[\"{shareholder_name}\"]\n"
                mermaid_code += f"    class {entity_map[shareholder_name]} topEntity;\n"
                print(f"添加股东: {shareholder_name} -> {entity_map[shareholder_name]} (topEntity)")
            
            # 建立股东与核心公司的关系
            if main_company and shareholder_name and main_company in entity_map and shareholder_name in entity_map:
                relationship_key = (shareholder_name, main_company)
                if relationship_key not in added_relationships:
                    shareholder_id = entity_map[shareholder_name]
                    main_company_id = entity_map[main_company]
                    
                    if percentage > 0:
                        mermaid_code += f"    {shareholder_id} -->|{percentage:.1f}%| {main_company_id}\n"
                    else:
                        mermaid_code += f"    {shareholder_id} -->|持股| {main_company_id}\n"
                    
                    added_relationships.add(relationship_key)
                    print(f"添加股东关系: {shareholder_name} -> {main_company} ({percentage:.1f}%)")
        
        # 3. 添加所有子公司（标记为subsidiary）
        for subsidiary in subsidiaries:
            if isinstance(subsidiary, dict):
                subsidiary_name = subsidiary.get('name', '')
                percentage = extract_percentage(subsidiary.get('percentage', 0))
            else:
                subsidiary_name = str(subsidiary)
                percentage = 0
            
            if subsidiary_name and subsidiary_name not in entity_map:
                entity_map[subsidiary_name] = f"E{entity_id_counter}"
                entity_id_counter += 1
                mermaid_code += f"    {entity_map[subsidiary_name]}[\"{subsidiary_name}\"]\n"
                mermaid_code += f"    class {entity_map[subsidiary_name]} subsidiary;\n"
                print(f"添加子公司: {subsidiary_name} -> {entity_map[subsidiary_name]} (subsidiary)")
            
            # 建立核心公司与子公司的关系
            if main_company and subsidiary_name and main_company in entity_map and subsidiary_name in entity_map:
                relationship_key = (main_company, subsidiary_name)
                if relationship_key not in added_relationships:
                    main_company_id = entity_map[main_company]
                    subsidiary_id = entity_map[subsidiary_name]
                    
                    if percentage > 0:
                        mermaid_code += f"    {main_company_id} -->|{percentage:.1f}%| {subsidiary_id}\n"
                    else:
                        mermaid_code += f"    {main_company_id} -->|控股| {subsidiary_id}\n"
                    
                    added_relationships.add(relationship_key)
                    print(f"添加子公司关系: {main_company} -> {subsidiary_name} ({percentage:.1f}%)")
        
        # 4. 处理entity_relationships中的关系（先处理，后面control_relationships优先级更高）
        entity_relationship_lines = []  # 存储entity_relationships生成的关系行
        if 'entity_relationships' in data and data['entity_relationships']:
            print("\n=== 处理entity_relationships ===")
            entity_relationships = data['entity_relationships']
            for i, relationship in enumerate(entity_relationships):
                # 支持两种格式：parent/child 和 from/to
                parent_name = relationship.get('parent', relationship.get('from', ''))
                child_name = relationship.get('child', relationship.get('to', ''))
                
                # 尝试从多个地方提取百分比：直接的percentage字段或description中的数字
                percentage = 0
                relationship_desc = relationship.get('description', '')
                
                # 优先从percentage字段提取
                if relationship.get('percentage'):
                    percentage = extract_percentage(relationship.get('percentage'))
                # 如果没有percentage字段或提取失败，尝试从description中提取
                elif relationship_desc:
                    # 1. 尝试直接匹配百分比模式，如"持股12.34%"或"12.34%股权"
                    percentage_match = re.search(r'(\d+(?:\.\d+)?)\s*%', relationship_desc)
                    if percentage_match:
                        percentage = float(percentage_match.group(1))
                    else:
                        # 2. 尝试匹配数字+持股模式，如"持股12.34"
                        percentage_match = re.search(r'(\d+(?:\.\d+)?)\s*[持占]', relationship_desc)
                        if percentage_match:
                            percentage = float(percentage_match.group(1))
                
                # 记录完整的关系描述，用于后续使用
                full_description = relationship_desc
                
                if not parent_name or not child_name:
                    continue
                
                print(f"处理实体关系 {i+1}/{len(entity_relationships)}: {parent_name} -> {child_name}")
                
                # 添加父实体
                if parent_name not in entity_map:
                    entity_map[parent_name] = f"E{entity_id_counter}"
                    entity_id_counter += 1
                    mermaid_code += f"    {entity_map[parent_name]}[\"{parent_name}\"]\n"
                    
                    # 根据用户要求分配样式
                    if parent_name in core_companies:
                        mermaid_code += f"    class {entity_map[parent_name]} coreCompany;\n"
                    elif parent_name in top_entities:
                        mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                    elif parent_name in subsidiary_names:
                        mermaid_code += f"    class {entity_map[parent_name]} subsidiary;\n"
                    else:
                        mermaid_code += f"    class {entity_map[parent_name]} company;\n"
                    
                    print(f"添加实体: {parent_name} -> {entity_map[parent_name]}")
                
                # 添加子实体
                if child_name not in entity_map:
                    entity_map[child_name] = f"E{entity_id_counter}"
                    entity_id_counter += 1
                    mermaid_code += f"    {entity_map[child_name]}[\"{child_name}\"]\n"
                    
                    # 根据用户要求分配样式
                    if child_name in core_companies:
                        mermaid_code += f"    class {entity_map[child_name]} coreCompany;\n"
                    elif child_name in top_entities:
                        mermaid_code += f"    class {entity_map[child_name]} topEntity;\n"
                    elif child_name in subsidiary_names:
                        mermaid_code += f"    class {entity_map[child_name]} subsidiary;\n"
                    else:
                        mermaid_code += f"    class {entity_map[child_name]} company;\n"
                    
                    print(f"添加实体: {child_name} -> {entity_map[child_name]}")
                
                # 暂时不添加关系，先记录下来，等control_relationships处理完后再处理
                relationship_key = (parent_name, child_name)
                parent_id = entity_map[parent_name]
                child_id = entity_map[child_name]
                
                if percentage > 0:
                    rel_line = f"    {parent_id} -->|{percentage:.1f}%| {child_id}"
                elif relationship_desc:
                    # 如果有描述但没有百分比，使用描述的前几个字符作为标签
                    short_desc = relationship_desc[:20] + ('...' if len(relationship_desc) > 20 else '')
                    rel_line = f"    {parent_id} -->|{short_desc}| {child_id}"
                else:
                    rel_line = f"    {parent_id} -->|关系| {child_id}"
                
                entity_relationship_lines.append((relationship_key, rel_line))
                print(f"记录实体关系: {parent_name} -> {child_name} ({percentage:.1f}% - {relationship_desc[:30]}...)")
        
        # 5. 处理控制关系（优先级高于entity_relationships）
        if 'control_relationships' in data and data['control_relationships']:
            print("\n=== 处理control_relationships ===")
            control_relationships = data['control_relationships']
            for i, relationship in enumerate(control_relationships):
                # 支持两种格式：{controller, controlled_entity} 或 {parent, child}
                controller_name = relationship.get('controller', relationship.get('parent', ''))
                controlled_entity = relationship.get('controlled_entity', relationship.get('child', ''))
                
                if not controller_name or not controlled_entity:
                    continue
                
                print(f"处理控制关系 {i+1}/{len(control_relationships)}: {controller_name} -> {controlled_entity}")
                
                # 添加控制人
                if controller_name not in entity_map:
                    entity_map[controller_name] = f"E{entity_id_counter}"
                    entity_id_counter += 1
                    mermaid_code += f"    {entity_map[controller_name]}[\"{controller_name}\"]\n"
                    mermaid_code += f"    class {entity_map[controller_name]} topEntity;\n"  # 控制人也是topEntity
                    print(f"添加控制人: {controller_name} -> {entity_map[controller_name]} (topEntity)")
                
                # 添加被控制实体
                if controlled_entity not in entity_map:
                    entity_map[controlled_entity] = f"E{entity_id_counter}"
                    entity_id_counter += 1
                    mermaid_code += f"    {entity_map[controlled_entity]}[\"{controlled_entity}\"]\n"
                    
                    # 根据用户要求分配样式
                    if controlled_entity in core_companies:
                        mermaid_code += f"    class {entity_map[controlled_entity]} coreCompany;\n"
                    elif controlled_entity in top_entities:
                        mermaid_code += f"    class {entity_map[controlled_entity]} topEntity;\n"
                    elif controlled_entity in subsidiary_names:
                        mermaid_code += f"    class {entity_map[controlled_entity]} subsidiary;\n"
                    else:
                        mermaid_code += f"    class {entity_map[controlled_entity]} company;\n"
                    
                    print(f"添加实体: {controlled_entity} -> {entity_map[controlled_entity]}")
                
                # 获取关系描述，如果有则使用，否则默认为"控制"
                relationship_desc = relationship.get('description', '控制')
                
                # 添加控制关系（使用虚线）
                relationship_key = (controller_name, controlled_entity)
                controller_id = entity_map[controller_name]
                controlled_id = entity_map[controlled_entity]
                
                # 直接添加控制关系，不检查是否已存在
                # 因为我们会在后面处理entity_relationships时跳过这些关系
                mermaid_code += f"    {controller_id} -.->|{relationship_desc}| {controlled_id}\n"
                added_relationships.add(relationship_key)
                print(f"添加控制关系: {controller_name} -.->|{relationship_desc}| {controlled_entity}")
        
        # 6. 现在添加entity_relationships中未被control_relationships覆盖的关系
        print("\n=== 处理剩余的entity_relationships ===")
        for relationship_key, rel_line in entity_relationship_lines:
            if relationship_key not in added_relationships:
                mermaid_code += rel_line + "\n"
                added_relationships.add(relationship_key)
                parent_name, child_name = relationship_key
                print(f"添加实体关系: {parent_name} -> {child_name}")
            else:
                print(f"跳过重复关系: {relationship_key[0]} -> {relationship_key[1]}（已由控制关系覆盖）")
        
        print(f"\n生成的Mermaid图表包含 {len(entity_map)} 个实体")
        print(f"生成的Mermaid图表包含 {len(added_relationships)} 个关系")
        
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

# 为了保持向后兼容性，提供原始函数名的别名
def generate_mermaid_from_equity_data(data):
    """为了向后兼容的别名"""
    return generate_mermaid_from_data(data)