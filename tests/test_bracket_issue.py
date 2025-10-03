import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入阿里云翻译功能
from src.utils.alicloud_translator import translate_with_alicloud

# 测试带括号的中文实体翻译
def test_bracket_entities():
    print("=== 测试带括号的中文实体翻译 ===\n")
    
    # 包含各种括号和特殊格式的中文实体
    bracket_entities = [
        "泉州市志成投资合伙企业 (有限合伙)",
        "深圳市美鹏健康管理有限公司 (Lessee)",
        "MOF(财政部)",
        "中国建设银行股份有限公司(上海分行)",
        "(有限责任公司)",
        "北京(中关村)科技有限公司",
        "[国资委]控股企业集团"
    ]
    
    # 执行翻译测试
    results = []
    success_count = 0
    failure_count = 0
    
    for entity in bracket_entities:
        print(f"翻译: '{entity}'")
        try:
            # 尝试直接翻译整个实体
            success, translated, error = translate_with_alicloud(entity, "zh", "en")
            
            if success:
                print(f"  成功: '{translated}'")
                success_count += 1
            else:
                print(f"  失败: {error}")
                failure_count += 1
                
                # 尝试分解翻译（如果有括号）
                if '(' in entity or ')' in entity:
                    print("  尝试分解翻译:")
                    # 简单分解 - 提取括号外的部分
                    outer_part = entity.split('(')[0].strip()
                    if outer_part:
                        success, translated_outer, error = translate_with_alicloud(outer_part, "zh", "en")
                        if success:
                            print(f"    括号外部分: '{outer_part}' → '{translated_outer}'")
                    
                    # 提取括号内的部分
                    inner_parts = []
                    temp = entity
                    while '(' in temp and ')' in temp:
                        start = temp.find('(')
                        end = temp.find(')')
                        if start < end:
                            inner = temp[start+1:end]
                            inner_parts.append(inner)
                            temp = temp[end+1:]
                        else:
                            break
                    
                    # 翻译括号内的部分
                    for i, inner in enumerate(inner_parts):
                        success, translated_inner, error = translate_with_alicloud(inner, "zh", "en")
                        if success:
                            print(f"    括号内部分 {i+1}: '{inner}' → '{translated_inner}'")
            
            results.append({
                "original": entity,
                "translated": translated if success else None,
                "success": success,
                "error": error if not success else None
            })
            
        except Exception as e:
            print(f"  异常: {str(e)}")
            failure_count += 1
            results.append({
                "original": entity,
                "translated": None,
                "success": False,
                "error": str(e)
            })
    
    # 统计结果
    print(f"\n翻译统计:")
    print(f"总测试实体: {len(bracket_entities)}")
    print(f"成功翻译: {success_count}")
    print(f"翻译失败: {failure_count}")
    print(f"成功率: {success_count/len(bracket_entities)*100:.1f}%")
    
    # 保存测试结果
    with open('tests/bracket_entity_translation_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            "test_results": results,
            "statistics": {
                "total": len(bracket_entities),
                "success": success_count,
                "failure": failure_count,
                "success_rate": success_count/len(bracket_entities)*100
            }
        }, f, ensure_ascii=False, indent=2)
    
    print("\n测试结果已保存到 tests/bracket_entity_translation_results.json")
    
    return success_count, failure_count

# 执行测试
if __name__ == "__main__":
    test_bracket_entities()