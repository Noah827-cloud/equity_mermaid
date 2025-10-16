import re
import sys
from typing import Dict

# 安全的打印函数，避免Windows控制台编码问题
def _safe_print(msg):
    """安全地打印消息，避免编码错误"""
    try:
        print(msg)
    except UnicodeEncodeError:
        # 如果出现编码错误，尝试使用ASCII编码
        try:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        except:
            # 如果还是失败，就不打印了
            pass


def _escape_mermaid_text(text):
    """Escape text for safe use inside Mermaid labels."""
    if not isinstance(text, str):
        text = str(text)

    # 🔥 保留<br>标签用于换行
    placeholder = "__MERMAID_BR__"
    for br_tag in ("<br>", "<br/>", "<BR>", "<BR/>"):
        if br_tag in text:
            text = text.replace(br_tag, placeholder)

    # 🔥 只转义双引号，因为标签在双引号内，其他字符不需要转义
    # Mermaid在双引号内的文本中，只有双引号和换行符需要处理
    escaped = text.replace("\"", "\\\"")
    
    # 🔥 移除换行符（保留<br>作为换行）
    escaped = escaped.replace("\n", " ")
    escaped = escaped.replace("\r", " ")
    escaped = escaped.replace("\t", " ")

    # 压缩多余空格
    escaped = " ".join(escaped.split())
    
    # 🔥 恢复<br>为实际换行符
    if placeholder in escaped:
        escaped = escaped.replace(placeholder, "<br>")

    return escaped

def _escape_label_with_linebreaks(text: str) -> str:
    """转义Mermaid标签文本，保留<br>标签用于换行"""
    # 直接使用_escape_mermaid_text，它会保留<br>标签
    return _escape_mermaid_text(text)


# 格式化顶层实体名称为多行，使用<br>换行，提升可读性
def _format_top_entity_label(name: str, entity: Dict = None) -> str:
    if not name:
        return name
    # 已经包含<br>则直接返回
    if "<br>" in name:
        return name
    
    # 如果提供了entity字典,添加额外信息
    if entity:
        lines = [name]  # 第一行:中文名
        
        # 第二行:英文名(如果存在) - 应用英文自动换行
        english_name = entity.get('english_name')
        if english_name:
            # 检查英文名是否需要分行（2个或更多单词）
            words = english_name.split()
            if len(words) >= 2:
                # 将英文部分分成两部分
                mid_point = len(words) // 2
                eng_line1 = ' '.join(words[:mid_point])
                eng_line2 = ' '.join(words[mid_point:])
                lines.append(eng_line1)
                lines.append(eng_line2)
            else:
                # 英文部分很短，不需要分行
                lines.append(english_name)
        
        # 注册资本(如果存在)
        reg_capital = entity.get('registration_capital') or entity.get('registered_capital')
        if reg_capital:
            lines.append(f"注册资本 {reg_capital}")
        
        # 成立日期(如果存在)
        est_date = entity.get('establishment_date') or entity.get('established_date')
        if est_date:
            lines.append(f"成立日期 {est_date}")
        
        return "<br>".join(lines)
    
    # 如果没有提供entity,使用原有逻辑处理名称格式化
    # 检查是否为中英文混合文本
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in name)
    has_english = any(char.isalpha() and ord(char) < 128 for char in name)
    
    # 中英文混合处理
    if has_chinese and has_english:
        # 首先检查是否有类似 "(Obligor)" 这样的后缀描述
        suffix_desc = ""
        main_name = name
        
        # 匹配最后的括号内容，如 "(Obligor)"
        suffix_match = re.search(r'(\s*\([A-Za-z\s/]+\))\s*$', name)
        if suffix_match:
            suffix_desc = suffix_match.group(1).strip()
            main_name = name[:name.rfind(suffix_desc)].strip()
        
        # 处理主要名称部分（不含后缀描述）
        chinese_part = ""
        english_part = ""
        
        # 检查是否有括号分隔的模式（中英文互译）
        paren_match = re.search(r'(.*?)[\(（](.*?)[\)）]', main_name)
        if paren_match:
            # 提取括号外和括号内的内容
            part1 = paren_match.group(1).strip()
            part2 = paren_match.group(2).strip()
            
            # 判断哪部分是中文，哪部分是英文
            if any('\u4e00' <= char <= '\u9fff' for char in part1):
                chinese_part = part1
                english_part = part2
            else:
                english_part = part1
                chinese_part = part2
        else:
            # 如果没有明显的括号分隔，尝试按字符类型分离
            english_chars = []
            chinese_chars = []
            
            for char in main_name:
                if '\u4e00' <= char <= '\u9fff':
                    chinese_chars.append(char)
                elif char.isalpha() or char.isspace() or char in ".,'-":
                    english_chars.append(char)
                else:
                    # 其他字符（如标点）根据上下文决定
                    if chinese_chars and not english_chars:
                        chinese_chars.append(char)
                    else:
                        english_chars.append(char)
            
            chinese_part = ''.join(chinese_chars).strip()
            english_part = ''.join(english_chars).strip()
        
        # 格式化英文部分（英文通常分两行）
        result = ""
        if english_part:
            words = english_part.split()
            if len(words) >= 2:
                # 简单地将英文部分分成两部分
                mid_point = len(words) // 2
                eng_line1 = ' '.join(words[:mid_point])
                eng_line2 = ' '.join(words[mid_point:])
                
                # 如果有中文，则作为第三行
                if chinese_part:
                    result = f"{eng_line1}<br>{eng_line2}<br>{chinese_part}"
                else:
                    result = f"{eng_line1}<br>{eng_line2}"
            else:
                # 英文部分很短，不需要分行
                if chinese_part:
                    result = f"{english_part}<br>{chinese_part}"
                else:
                    result = english_part
        else:
            # 如果没有提取出有效的英文部分，只处理中文
            if chinese_part:
                # 中文通常只需要一行
                if len(chinese_part) <= 15:
                    result = chinese_part
                else:
                    # 中文较长时分两行
                    mid = len(chinese_part) // 2
                    result = f"{chinese_part[:mid]}<br>{chinese_part[mid:]}"
            else:
                result = main_name
        
        # 如果有后缀描述，添加到最后一行
        if suffix_desc:
            result += f"<br>{suffix_desc}"
            
        return result
    
    # 纯中文处理
    elif has_chinese:
        # 计算字符总长度
        total_len = len(name)
        if total_len <= 10:  # 短名称不分行
            return name
            
        # 优先在特定位置换行
        special_markers = ["有限公司", "有限责任公司", "股份有限公司", "（有限合伙）", "(有限合伙)", "合伙企业"]
        
        # 尝试在特定标记处分行
        for marker in special_markers:
            pos = name.find(marker)
            if pos > 0:
                # 找到标记，在标记前换行
                remaining_len = total_len - pos
                if pos > total_len // 3 and remaining_len > 5:  # 确保分割点不会太靠前或太靠后
                    # 将剩余部分再次分割
                    first_part = name[:pos].strip()
                    second_part = name[pos:].strip()
                    
                    # 如果第一部分太长，再分一次
                    if len(first_part) > total_len // 2:
                        mid = len(first_part) // 2
                        line1 = first_part[:mid].strip()
                        line2 = first_part[mid:].strip()
                        line3 = second_part
                    else:
                        line1 = first_part
                        
                        # 如果第二部分很长，再分一次
                        if len(second_part) > total_len // 3:
                            mid = len(second_part) // 2
                            line2 = second_part[:mid].strip()
                            line3 = second_part[mid:].strip()
                        else:
                            line2 = second_part
                            line3 = ""
                    
                    return "<br>".join([ln for ln in (line1, line2, line3) if ln])
        
        # 如果没有找到特定标记，按字符数三等分
        third = max(1, total_len // 3)
        line1 = name[:third].strip()
        line2 = name[third:2*third].strip()
        line3 = name[2*third:].strip()
        return "<br>".join([ln for ln in (line1, line2, line3) if ln])
    
    # 纯英文处理 - 优先分成两行而不是三行，更美观
    words = name.split()
    if len(words) >= 2:
        # 简单地将英文部分分成两部分
        mid_point = len(words) // 2
        line1 = ' '.join(words[:mid_point])
        line2 = ' '.join(words[mid_point:])
        return f"{line1}<br>{line2}"
    
    # 如果只有一个单词但很长，尝试分行
    elif len(words) == 1 and len(name) > 15:
        mid = len(name) // 2
        return f"{name[:mid]}<br>{name[mid:]}"
    
    # 短名称不分行
    return name

def generate_mermaid_html_with_security(mermaid_code: str) -> str:
    """
    生成包含安全配置的完整Mermaid HTML代码
    
    Args:
        mermaid_code: 纯Mermaid图表代码
        
    Returns:
        str: 包含安全配置的完整HTML代码
    """
    # 🔒 安全配置：使用antiscript安全级别和禁用htmlLabels
    mermaid_config = {
        "startOnLoad": False,
        "theme": "default",
        "securityLevel": "antiscript",  # 防止脚本注入
        "flowchart": {
            "useMaxWidth": False,
            "htmlLabels": False,  # 禁用HTML标签，防止XSS
            "curve": "linear"
        },
        "fontFamily": '"Segoe UI", sans-serif'
    }
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="mermaid">
{mermaid_code}
    </div>
    <script>
        mermaid.initialize({mermaid_config});
    </script>
</body>
</html>
"""


def generate_mermaid_from_data(data):
    """
    从数据生成Mermaid图表代码
    
    Args:
        data: 包含股权结构数据的字典
        
    Returns:
        str: 纯Mermaid图表代码（兼容streamlit_mermaid）
    """
    # 提取数据
    main_company = data.get("main_company", "")
    core_company = data.get("core_company", "")  # 可能与main_company相同或不同
    subsidiaries = data.get("subsidiaries", [])
    controller = data.get("controller", "")
    top_entities = data.get("top_entities", [])
    entity_relationships = data.get("entity_relationships", [])
    control_relationships = data.get("control_relationships", [])
    all_entities = data.get("all_entities", [])
    
    # 调试信息
    _safe_print(f"Mermaid函数接收到的controller: '{controller}'")
    _safe_print(f"top_entities: {[e.get('name', '') for e in top_entities]}")
    
    # 创建实体映射表
    entity_map = {}
    entity_id_counter = 1
    
        # 初始化Mermaid代码
    mermaid_code = "flowchart TD\n"
    
    # 添加样式类定义
    mermaid_code += "    classDef coreCompany fill:#1B3A57,stroke:#0F2439,stroke-width:2px,color:#ffffff,font-weight:600;\n"
    mermaid_code += "    classDef subsidiary fill:#E6EEF5,stroke:#4B6A88,stroke-width:1.5px,color:#1F2F3D;\n"
    mermaid_code += "    classDef topEntity fill:#F4F1E8,stroke:#B0854C,stroke-width:1.5px,color:#2F342E;\n"
    mermaid_code += "    classDef company fill:#DDE2E7,stroke:#7A8A99,stroke-width:1.3px,color:#1C2A36;\n"
    mermaid_code += "    classDef person fill:#F5E8EC,stroke:#C27084,stroke-width:1.3px,color:#3A1F2B;\n"
    mermaid_code += "    classDef controller fill:#0C63CE,stroke:#0A4FA6,stroke-width:3px,color:#ffffff,font-weight:600;\n"
    
    # 跟踪已添加的实体和关系
    added_entities = set()
    added_relationships = set()
    
    # 创建一个辅助函数来添加实体
    def add_entity(entity_name, entity_type="company"):
        nonlocal entity_id_counter
        
        # 如果实体已添加，直接返回
        if entity_name in added_entities:
            return
            
        # 如果实体不在映射表中，添加它
        if entity_name not in entity_map:
            entity_map[entity_name] = f"E{entity_id_counter}"
            entity_id_counter += 1
        
        # 转义特殊字符以避免Mermaid语法错误
        # 从all_entities中查找对应的entity对象
        entity_obj = None
        for e in all_entities:
            if e.get("name") == entity_name:
                entity_obj = e
                break
        formatted = _format_top_entity_label(entity_name, entity_obj)
        escaped_name = _escape_label_with_linebreaks(formatted)
        
        # 添加实体节点
        mermaid_code_addition = f"    {entity_map[entity_name]}[\"{escaped_name}\"]\n"
        
        # 检查all_entities中是否有该实体的类型信息
        entity_type_from_all = None
        for e in all_entities:
            if e.get("name") == entity_name:
                entity_type_from_all = e.get("type")
                break
        
        # 添加样式类 - 调整优先级，实控人优先，然后是person类型
        if entity_name == main_company or entity_name == core_company:
            mermaid_code_addition += f"    class {entity_map[entity_name]} coreCompany;\n"
        elif entity_name == controller:
            # 实控人使用特殊的controller样式
            mermaid_code_addition += f"    class {entity_map[entity_name]} controller;\n"
        elif entity_name in [s.get("name", "") for s in subsidiaries]:
            mermaid_code_addition += f"    class {entity_map[entity_name]} subsidiary;\n"
        elif entity_type == "person" or entity_type_from_all == "person":
            mermaid_code_addition += f"    class {entity_map[entity_name]} person;\n"
        elif entity_name in [e.get("name", "") for e in top_entities]:
            mermaid_code_addition += f"    class {entity_map[entity_name]} topEntity;\n"
        else:
            mermaid_code_addition += f"    class {entity_map[entity_name]} company;\n"
        
        # 标记实体为已添加
        added_entities.add(entity_name)
        
        return mermaid_code_addition
    
    # 处理主要数据
    try:
        # 1. 首先添加核心公司
        if main_company:
            entity_map[main_company] = f"E{entity_id_counter}"
            entity_id_counter += 1
            # 添加实体节点
            # 从all_entities中查找对应的entity对象
            entity_obj = None
            for e in all_entities:
                if e.get("name") == main_company:
                    entity_obj = e
                    break
            formatted = _format_top_entity_label(main_company, entity_obj)
            escaped_name = _escape_label_with_linebreaks(formatted)
            mermaid_code += f"    {entity_map[main_company]}[\"{escaped_name}\"]\n"
            mermaid_code += f"    class {entity_map[main_company]} coreCompany;\n"
            _safe_print(f"添加核心公司: {main_company} -> {entity_map[main_company]}")
            
            # 标记为已添加
            added_entities.add(main_company)
        
        # 只添加一次核心公司，如果main_company和core_company相同，避免重复
        # 如果core_company存在且与main_company不同，则添加core_company
        if core_company and core_company != main_company and core_company not in entity_map:
            entity_map[core_company] = f"E{entity_id_counter}"
            entity_id_counter += 1
            # 添加实体节点
            # 从all_entities中查找对应的entity对象
            entity_obj = None
            for e in all_entities:
                if e.get("name") == core_company:
                    entity_obj = e
                    break
            formatted = _format_top_entity_label(core_company, entity_obj)
            escaped_name = _escape_label_with_linebreaks(formatted)
            mermaid_code += f"    {entity_map[core_company]}[\"{escaped_name}\"]\n"
            mermaid_code += f"    class {entity_map[core_company]} coreCompany;\n"
            _safe_print(f"提前添加core_company到图表: {core_company} -> {entity_map[core_company]} (coreCompany)")
        
            # 标记为已添加
            added_entities.add(core_company)
        
        # 2. 添加子公司和关系
        for subsidiary in subsidiaries:
            subsidiary_name = subsidiary.get("name", "")
            percentage = subsidiary.get("percentage", 0)
            
            if not subsidiary_name or subsidiary_name in added_entities:
                continue
                
            if subsidiary_name not in entity_map:
                entity_map[subsidiary_name] = f"E{entity_id_counter}"
                entity_id_counter += 1
                
                # 添加实体节点（所有实体统一多行显示）
                # 转义特殊字符以避免Mermaid语法错误
                # 从all_entities中查找对应的entity对象
                entity_obj = None
                for e in all_entities:
                    if e.get("name") == subsidiary_name:
                        entity_obj = e
                        break
                formatted = _format_top_entity_label(subsidiary_name, entity_obj)
                escaped_name = _escape_label_with_linebreaks(formatted)
                mermaid_code += f"    {entity_map[subsidiary_name]}[\"{escaped_name}\"]\n"
                mermaid_code += f"    class {entity_map[subsidiary_name]} subsidiary;\n"
                _safe_print(f"添加子公司: {subsidiary_name} -> {entity_map[subsidiary_name]} (subsidiary)")
                
                # 标记为已添加
                added_entities.add(subsidiary_name)
            
            # 添加与核心公司的关系（如果核心公司存在且持股比例大于0）
            if main_company and main_company in entity_map and percentage > 0:
                relationship_key = f"{main_company}_{subsidiary_name}"
                if relationship_key not in added_relationships:
                    mermaid_code += f"    {entity_map[main_company]} -->|{percentage}%| {entity_map[subsidiary_name]}\n"
                    added_relationships.add(relationship_key)
                    _safe_print(f"添加关系: {main_company} -> {subsidiary_name} ({percentage}%)")
        
        # 3. 添加顶级实体（股东）
        for entity in top_entities:
            shareholder_name = entity.get("name", "")
            percentage = entity.get("percentage", 0)
            entity_type = entity.get("type", "company")
            
            if not shareholder_name or shareholder_name in added_entities:
                continue
                
            if shareholder_name not in entity_map:
                entity_map[shareholder_name] = f"E{entity_id_counter}"
                entity_id_counter += 1
                
                # 添加实体节点（顶层实体统一多行显示）
                # 转义特殊字符以避免Mermaid语法错误
                # 从all_entities中查找对应的entity对象
                entity_obj = None
                for e in all_entities:
                    if e.get("name") == shareholder_name:
                        entity_obj = e
                        break
                formatted = _format_top_entity_label(shareholder_name, entity_obj)
                escaped_name = _escape_label_with_linebreaks(formatted)
                mermaid_code += f"    {entity_map[shareholder_name]}[\"{escaped_name}\"]\n"
                
                # 检查实体类型和是否为实控人
                is_person = False
                for e in all_entities:
                    if e.get("name") == shareholder_name and e.get("type") == "person":
                        is_person = True
                        break
                
                # 优先检查是否为实控人
                _safe_print(f"检查实控人: shareholder_name='{shareholder_name}', controller='{controller}', 是否匹配: {shareholder_name == controller}")
                if shareholder_name == controller:
                    mermaid_code += f"    class {entity_map[shareholder_name]} controller;\n"
                    _safe_print(f"添加实控人: {shareholder_name} -> {entity_map[shareholder_name]} (controller)")
                elif is_person:
                    mermaid_code += f"    class {entity_map[shareholder_name]} person;\n"
                    _safe_print(f"添加股东: {shareholder_name} -> {entity_map[shareholder_name]} (person)")
                else:
                    mermaid_code += f"    class {entity_map[shareholder_name]} topEntity;\n"
                    _safe_print(f"添加股东: {shareholder_name} -> {entity_map[shareholder_name]} (topEntity)")
                
                # 标记为已添加
                added_entities.add(shareholder_name)
            
            # 添加与核心公司的关系（如果核心公司存在且持股比例大于0）
            # 🔥 关键修复：检查是否为合并实体，如果是则自动生成关系
            has_explicit_equity_relationship = False
            is_merged_entity = False
            
            # 检查是否有显式关系
            for equity_rel in entity_relationships:
                from_entity = equity_rel.get("parent", equity_rel.get("from", ""))
                to_entity = equity_rel.get("child", equity_rel.get("to", ""))
                if from_entity == shareholder_name and to_entity == main_company:
                    has_explicit_equity_relationship = True
                    break
            
            # 检查是否为合并实体（通过名称特征判断）
            merged_entity_keywords = ["其他股东", "其他投资者", "其他", "合并", "集团"]
            is_merged_entity = any(keyword in shareholder_name for keyword in merged_entity_keywords)
            
            # 🔥 关键修复：严格按照entity_relationships生成关系，不自动生成
            # 只有当关系在entity_relationships中明确存在时才生成
            should_add_relationship = has_explicit_equity_relationship
            
            if main_company and main_company in entity_map and percentage > 0 and should_add_relationship:
                # 检查是否会有控制关系，如果有则跳过股权关系
                has_control_relationship = False
                for control_rel in control_relationships:
                    controller_name = control_rel.get("parent", control_rel.get("from", ""))
                    controlled_entity = control_rel.get("child", control_rel.get("to", ""))
                    if controller_name == shareholder_name and controlled_entity == main_company:
                        has_control_relationship = True
                        break
                
                if not has_control_relationship:
                    relationship_key = f"{shareholder_name}_{main_company}"
                    if relationship_key not in added_relationships:
                        mermaid_code += f"    {entity_map[shareholder_name]} -->|{percentage}%| {entity_map[main_company]}\n"
                        added_relationships.add(relationship_key)
                        if is_merged_entity:
                            _safe_print(f"添加合并实体关系: {shareholder_name} -> {main_company} ({percentage}%)")
                        elif has_explicit_equity_relationship:
                            _safe_print(f"添加显式关系: {shareholder_name} -> {main_company} ({percentage}%)")
                        else:
                            _safe_print(f"添加自动生成关系: {shareholder_name} -> {main_company} ({percentage}%)")
                else:
                    _safe_print(f"跳过股权关系 {shareholder_name} -> {main_company}，因为存在控制关系")
            elif shareholder_name and main_company and percentage > 0:
                if not has_explicit_equity_relationship:
                    _safe_print(f"跳过自动生成股权关系 {shareholder_name} -> {main_company}，因为关系不在entity_relationships中（用户已删除）")
                else:
                    _safe_print(f"跳过自动生成股权关系 {shareholder_name} -> {main_company}，因为其他原因")
        
        # 4. 添加控制人和控制关系
        if controller:
            if controller not in entity_map:
                entity_map[controller] = f"E{entity_id_counter}"
                entity_id_counter += 1
                
                # 添加控制人（视为顶层实体，多行格式化）
                    # 转义特殊字符以避免Mermaid语法错误
                # 从all_entities中查找对应的entity对象
                entity_obj = None
                for e in all_entities:
                    if e.get("name") == controller:
                        entity_obj = e
                        break
                formatted = _format_top_entity_label(controller, entity_obj)
                escaped_name = _escape_label_with_linebreaks(formatted)
                mermaid_code += f"    {entity_map[controller]}[\"{escaped_name}\"]\n"
                mermaid_code += f"    class {entity_map[controller]} person;\n"
                _safe_print(f"添加控制人: {controller} -> {entity_map[controller]} (person)")
                
                # 标记为已添加
                added_entities.add(controller)
            
            # 添加与核心公司的控制关系（如果核心公司存在）
            # 🔥 关键修复：只有在control_relationships中明确存在时才添加控制关系
            # 避免自动生成用户已删除的关系
            has_explicit_control_relationship = False
            for control_rel in control_relationships:
                controller_name = control_rel.get("parent", control_rel.get("from", ""))
                controlled_entity = control_rel.get("child", control_rel.get("to", ""))
                if controller_name == controller and controlled_entity == main_company:
                    has_explicit_control_relationship = True
                    break
            
            if main_company and main_company in entity_map and has_explicit_control_relationship:
                relationship_key = f"{controller}_{main_company}_control"
                if relationship_key not in added_relationships:
                    mermaid_code += f"    {entity_map[controller]} -.-> {entity_map[main_company]}\n"
                    added_relationships.add(relationship_key)
                    _safe_print(f"添加控制关系: {controller} -.-> {main_company}")
            elif controller and main_company:
                _safe_print(f"跳过自动生成控制关系 {controller} -.-> {main_company}，因为用户已删除或未明确设置")
        
        # 5. 处理实体关系
        for relationship in entity_relationships:
            # 支持两种格式：parent/child和from/to
            parent_name = relationship.get("parent", relationship.get("from", ""))
            child_name = relationship.get("child", relationship.get("to", ""))
            percentage = relationship.get("percentage", 0)
            
            if not parent_name or not child_name:
                continue
            
            # 检查是否会有控制关系，如果有则跳过股权关系
            has_control_relationship = False
            for control_rel in control_relationships:
                controller_name = control_rel.get("parent", control_rel.get("from", ""))
                controlled_entity = control_rel.get("child", control_rel.get("to", ""))
                if controller_name == parent_name and controlled_entity == child_name:
                    has_control_relationship = True
                    break
            
            if has_control_relationship:
                _safe_print(f"跳过股权关系 {parent_name} -> {child_name}，因为存在控制关系")
                continue
                    
            # 确保两个实体都存在于映射表中
            if parent_name not in entity_map:
                # 尝试从all_entities中获取实体类型
                entity_type = "company"  # 默认为公司
                for entity in all_entities:
                    if entity.get("name") == parent_name:
                        entity_type = entity.get("type", "company")
                        break
                    
                    # 添加父实体
                entity_map[parent_name] = f"E{entity_id_counter}"
                entity_id_counter += 1
                
                # 添加实体节点（所有实体类型都做多行格式化）
                        # 转义特殊字符以避免Mermaid语法错误
                # 从all_entities中查找对应的entity对象
                entity_obj = None
                for e in all_entities:
                    if e.get("name") == parent_name:
                        entity_obj = e
                        break
                label = _format_top_entity_label(parent_name, entity_obj)  # 所有实体都应用多行格式化
                escaped_name = _escape_label_with_linebreaks(label)
                mermaid_code += f"    {entity_map[parent_name]}[\"{escaped_name}\"]\n"
                        
                # 检查是否为person类型
                is_person = False
                # 检查传入的entity_type
                if entity_type == "person":
                    is_person = True
                # 检查all_entities中的类型
                else:
                    for e in all_entities:
                        if e.get("name") == parent_name and e.get("type") == "person":
                            is_person = True
                            break
                
                # 根据实体类型添加样式类
                if is_person:
                    mermaid_code += f"    class {entity_map[parent_name]} person;\n"
                elif parent_name in [e.get("name", "") for e in top_entities]:
                    mermaid_code += f"    class {entity_map[parent_name]} topEntity;\n"
                else:
                    mermaid_code += f"    class {entity_map[parent_name]} company;\n"
                        
                # 标记为已添加
                added_entities.add(parent_name)
            
            if child_name not in entity_map:
                # 尝试从all_entities中获取实体类型
                entity_type = "company"  # 默认为公司
                for entity in all_entities:
                    if entity.get("name") == child_name:
                        entity_type = entity.get("type", "company")
                        break
                    
                # 添加子实体
                entity_map[child_name] = f"E{entity_id_counter}"
                entity_id_counter += 1
                
                # 添加实体节点（所有实体类型都做多行格式化）
                # 转义特殊字符以避免Mermaid语法错误
                # 从all_entities中查找对应的entity对象
                entity_obj = None
                for e in all_entities:
                    if e.get("name") == child_name:
                        entity_obj = e
                        break
                label = _format_top_entity_label(child_name, entity_obj)  # 所有实体都应用多行格式化
                escaped_name = _escape_label_with_linebreaks(label)
                mermaid_code += f"    {entity_map[child_name]}[\"{escaped_name}\"]\n"
                        
                # 检查是否为person类型
                is_person = False
                # 检查传入的entity_type
                if entity_type == "person":
                    is_person = True
                # 检查all_entities中的类型
                else:
                    for e in all_entities:
                        if e.get("name") == child_name and e.get("type") == "person":
                            is_person = True
                            break
                
                # 根据实体类型添加样式类
                if is_person:
                    mermaid_code += f"    class {entity_map[child_name]} person;\n"
                elif child_name in [s.get("name", "") for s in subsidiaries]:
                    mermaid_code += f"    class {entity_map[child_name]} subsidiary;\n"
                else:
                    mermaid_code += f"    class {entity_map[child_name]} company;\n"
                        
                # 标记为已添加
                added_entities.add(child_name)
            
            # 添加关系（只有持股比例大于0时才添加）
            relationship_key = f"{parent_name}_{child_name}"
            if relationship_key not in added_relationships and percentage > 0:
                mermaid_code += f"    {entity_map[parent_name]} -->|{percentage}%| {entity_map[child_name]}\n"
                added_relationships.add(relationship_key)
                _safe_print(f"添加关系: {parent_name} -> {child_name} ({percentage}%)")
        
        # 6. 处理控制关系
        for relationship in control_relationships:
            # 支持两种格式：parent/child和from/to
            controller_name = relationship.get("parent", relationship.get("from", ""))
            controlled_entity = relationship.get("child", relationship.get("to", ""))
            description = relationship.get("description", "")
            
            if not controller_name or not controlled_entity:
                continue
                    
            # 确保控制人存在于映射表中
            if controller_name not in entity_map:
                entity_map[controller_name] = f"E{entity_id_counter}"
                entity_id_counter += 1
                
                # 添加控制人（视为顶层实体，多行格式化）
                # 转义特殊字符以避免Mermaid语法错误
                # 从all_entities中查找对应的entity对象
                entity_obj = None
                for e in all_entities:
                    if e.get("name") == controller_name:
                        entity_obj = e
                        break
                formatted = _format_top_entity_label(controller_name, entity_obj)
                escaped_name = _escape_label_with_linebreaks(formatted)
                mermaid_code += f"    {entity_map[controller_name]}[\"{escaped_name}\"]\n"
                # 检查是否为实控人，如果是则使用controller样式
                if controller_name == controller:
                    mermaid_code += f"    class {entity_map[controller_name]} controller;\n"
                    _safe_print(f"添加实控人: {controller_name} -> {entity_map[controller_name]} (controller)")
                else:
                    mermaid_code += f"    class {entity_map[controller_name]} person;\n"
                    _safe_print(f"添加控制人: {controller_name} -> {entity_map[controller_name]} (person)")
                
                # 标记为已添加
                added_entities.add(controller_name)
            
            # 确保被控制实体存在于映射表中
            if controlled_entity not in entity_map:
                entity_map[controlled_entity] = f"E{entity_id_counter}"
                entity_id_counter += 1
                
                # 添加被控制实体（所有实体统一多行显示）
                # 转义特殊字符以避免Mermaid语法错误
                # 从all_entities中查找对应的entity对象
                entity_obj = None
                for e in all_entities:
                    if e.get("name") == controlled_entity:
                        entity_obj = e
                        break
                formatted = _format_top_entity_label(controlled_entity, entity_obj)
                escaped_name = _escape_label_with_linebreaks(formatted)
                mermaid_code += f"    {entity_map[controlled_entity]}[\"{escaped_name}\"]\n"
                mermaid_code += f"    class {entity_map[controlled_entity]} company;\n"
                _safe_print(f"添加被控制实体: {controlled_entity} -> {entity_map[controlled_entity]} (company)")
                
                # 标记为已添加
                added_entities.add(controlled_entity)
            
            # 添加控制关系
            control_relationship_key = f"{controller_name}_{controlled_entity}_control"
            
            if control_relationship_key not in added_relationships:
                # 如果有描述，添加到关系标签中
                if description:
                    # 🔥 关键修复：转义描述文本中的特殊字符，避免Mermaid语法错误
                    escaped_description = _escape_label_with_linebreaks(description)
                    mermaid_code += f"    {entity_map[controller_name]} -.->|\"{escaped_description}\"| {entity_map[controlled_entity]}\n"
                else:
                    mermaid_code += f"    {entity_map[controller_name]} -.-> {entity_map[controlled_entity]}\n"
                
                added_relationships.add(control_relationship_key)
                _safe_print(f"添加控制关系: {controller_name} -.-> {controlled_entity} ({description})")
    
    except Exception as e:
        import traceback
        error_msg = f"生成Mermaid代码时出错: {str(e)}\n{traceback.format_exc()}"
        _safe_print(error_msg)
        mermaid_code = f"flowchart TD\n    E1[\"Error: {str(e)}\"]"
    
    # 🔒 返回纯Mermaid图表代码（streamlit_mermaid兼容）
    # 注意：安全配置需要在HTML环境中单独设置
    return mermaid_code

