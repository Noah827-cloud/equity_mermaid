import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_equity_data_for_relationships():
    """
    测试AI分析生成的股权数据是否可以正确进入关系设置步骤
    """
    # 读取测试结果文件
    result_file = "c:\\Users\\z001syzk\\Downloads\\equity_mermaid\\test_results\\result_2_福建南方路面机械股份有限公司-股东信息最新公示-20250930090121.json"
    
    print(f"正在读取测试结果文件: {result_file}")
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 获取股权数据
        equity_data = data.get('equity_data', {})
        
        # 检查关系设置步骤所需的关键字段
        print("\n===== 检查关系设置步骤所需的关键字段 =====")
        
        # 1. 检查核心公司
        core_company = equity_data.get('core_company')
        print(f"核心公司: {'✓ 存在' if core_company else '✗ 缺失'}")
        
        # 2. 检查顶级实体
        top_level_entities = equity_data.get('top_level_entities', [])
        print(f"顶级实体数量: {len(top_level_entities)}")
        print(f"顶级实体格式: {'✓ 有效' if all(isinstance(e, dict) and 'name' in e for e in top_level_entities) else '✗ 无效'}")
        
        # 3. 检查实体关系
        entity_relationships = equity_data.get('entity_relationships', [])
        print(f"实体关系数量: {len(entity_relationships)}")
        print(f"实体关系格式: {'✓ 有效' if all(isinstance(r, dict) for r in entity_relationships) else '✗ 无效'}")
        
        # 4. 检查所有实体
        all_entities = equity_data.get('all_entities', [])
        print(f"所有实体数量: {len(all_entities)}")
        print(f"所有实体格式: {'✓ 有效' if all(isinstance(e, dict) and 'name' in e for e in all_entities) else '✗ 无效'}")
        
        # 5. 转换数据格式以匹配manual_equity_editor.py的要求
        print("\n===== 转换数据格式以匹配manual_equity_editor.py的要求 =====")
        
        # 检查并转换top_level_entities格式
        print("转换顶级实体格式...")
        transformed_top_level_entities = []
        for entity in top_level_entities:
            transformed_entity = {
                "name": entity.get("name", ""),
                "type": "company" if entity.get("entity_type", "").lower() == "法人" else "person",
                "percentage": entity.get("percentage", 0.0)
            }
            transformed_top_level_entities.append(transformed_entity)
        
        # 检查并转换entity_relationships格式
        print("转换实体关系格式...")
        transformed_relationships = []
        for rel in entity_relationships:
            # 从'from'和'to'转换为'parent'和'child'
            if 'from' in rel and 'to' in rel:
                # 如果是从股东到核心公司的关系，设置为股权关系
                if rel['from'] in [e['name'] for e in top_level_entities] and rel['to'] == core_company:
                    # 查找该股东的持股比例
                    percentage = 0.0
                    for entity in top_level_entities:
                        if entity['name'] == rel['from']:
                            percentage = entity.get('percentage', 0.0)
                            break
                    
                    transformed_rel = {
                        "parent": rel['from'],
                        "child": rel['to'],
                        "percentage": percentage
                    }
                    transformed_relationships.append(transformed_rel)
                    print(f"  - 转换关系: {rel['from']} → {rel['to']} ({percentage}%)")
        
        # 检查并转换all_entities格式
        print("转换所有实体格式...")
        transformed_all_entities = []
        for entity in all_entities:
            transformed_entity = {
                "name": entity.get("name", ""),
                "type": "company" if entity.get("entity_type", "").lower() == "法人" else "person"
            }
            transformed_all_entities.append(transformed_entity)
        
        # 添加核心公司到所有实体
        if core_company not in [e['name'] for e in transformed_all_entities]:
            transformed_all_entities.append({
                "name": core_company,
                "type": "company"
            })
        
        # 构建完整的转换后数据
        transformed_data = {
            "core_company": core_company,
            "controller": equity_data.get('actual_controller'),
            "top_level_entities": transformed_top_level_entities,
            "subsidiaries": equity_data.get('subsidiaries', []),
            "entity_relationships": transformed_relationships,
            "control_relationships": [],  # 如果没有控制关系，使用空列表
            "all_entities": transformed_all_entities,
            "shareholders": []  # 兼容旧版本
        }
        
        # 验证转换后的数据是否满足进入关系设置步骤的要求
        print("\n===== 验证转换后的数据是否满足进入关系设置步骤的要求 =====")
        
        # 检查必要字段
        required_fields = ['core_company', 'top_level_entities', 'entity_relationships', 'all_entities']
        all_fields_present = all(field in transformed_data for field in required_fields)
        print(f"必要字段完整性: {'✓ 完整' if all_fields_present else '✗ 不完整'}")
        
        # 检查是否有顶级实体
        has_top_entities = len(transformed_data['top_level_entities']) > 0
        print(f"顶级实体存在: {'✓ 有' if has_top_entities else '✗ 无'}")
        
        # 检查是否有至少一个关系
        has_relationships = len(transformed_data['entity_relationships']) > 0
        print(f"实体关系存在: {'✓ 有' if has_relationships else '✗ 无'}")
        
        # 检查核心公司是否已设置
        core_company_set = bool(transformed_data['core_company'])
        print(f"核心公司已设置: {'✓ 是' if core_company_set else '✗ 否'}")
        
        # 综合评估
        can_enter_relationships = all_fields_present and has_top_entities and core_company_set
        print(f"\n===== 综合评估结果 =====")
        print(f"是否可以进入关系设置步骤: {'✓ 可以' if can_enter_relationships else '✗ 不可以'}")
        
        if can_enter_relationships:
            print("\n✓ 测试通过! AI分析生成的数据可以正确进入关系设置步骤")
            print(f"- 核心公司: {transformed_data['core_company']}")
            print(f"- 顶级实体数量: {len(transformed_data['top_level_entities'])}")
            print(f"- 实体关系数量: {len(transformed_data['entity_relationships'])}")
            print(f"- 所有实体数量: {len(transformed_data['all_entities'])}")
            
            # 保存转换后的数据用于测试
            output_file = "test_results\transformed_equity_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(transformed_data, f, ensure_ascii=False, indent=2)
            print(f"\n转换后的数据已保存到: {output_file}")
            
            return True
        else:
            print("\n✗ 测试失败! AI分析生成的数据不能直接进入关系设置步骤")
            missing = []
            if not all_fields_present:
                missing.extend([f for f in required_fields if f not in transformed_data])
            if not has_top_entities:
                missing.append("顶级实体")
            if not core_company_set:
                missing.append("核心公司")
            print(f"缺失或不满足要求的项: {', '.join(missing)}")
            return False
            
    except FileNotFoundError:
        print(f"错误: 找不到测试结果文件 {result_file}")
        return False
    except json.JSONDecodeError:
        print(f"错误: 无法解析JSON文件 {result_file}")
        return False
    except Exception as e:
        print(f"错误: {str(e)}")
        return False

if __name__ == "__main__":
    print("===== 测试AI分析生成的数据是否可以正确进入关系设置步骤 =====")
    success = test_equity_data_for_relationships()
    sys.exit(0 if success else 1)