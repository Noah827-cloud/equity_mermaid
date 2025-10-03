import sys
import os
import json
import io
import contextlib

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入我们修复过的翻译模块
from src.utils.alicloud_translator import translate_with_alicloud

# 用户提供的中文股权数据（修正为有效的JSON格式）
chinese_equity_data = '''
{
  "core_company": "深圳市美鹏健康管理有限公司 (Lessee)",
  "shareholders": [
    {
      "name": "南通美富健康产业发展合伙企业 (有限合伙)",
      "percentage": 48.5
    },
    {
      "name": "深圳美年大健康健康管理有限公司",
      "percentage": 43.9
    },
    {
      "name": "Ms. Wang Ting",
      "percentage": 7.6
    }
  ],
  "subsidiaries": [],
  "controller": "Mr. Yu Rong",
  "top_level_entities": [
    {
      "name": "MOF(财政部)",
      "percentage": 0.1
    },
    {
      "name": "Mr. Yu Rong",
      "percentage": 10.53
    }
  ],
  "entity_relationships": [
    {
      "parent": "MOF(财政部)",
      "child": "北京东富通达投资管理中心 (有限合伙)",
      "percentage": 0.1
    },
    {
      "parent": "Mr. Yu Rong",
      "child": "美年大健康产业控股股份有限公司",
      "percentage": 10.53
    },
    {
      "parent": "北京东富通达投资管理中心 (有限合伙)",
      "child": "南通美富健康产业发展合伙企业 (有限合伙)",
      "percentage": 80.8
    },
    {
      "parent": "北京东富通达投资管理中心 (有限合伙)",
      "child": "深圳美年大健康健康管理有限公司",
      "percentage": 18.9
    },
    {
      "parent": "美年大健康产业控股股份有限公司",
      "child": "深圳美年大健康健康管理有限公司",
      "percentage": 100
    },
    {
      "parent": "南通美富健康产业发展合伙企业 (有限合伙)",
      "child": "深圳市美鹏健康管理有限公司 (Lessee)",
      "percentage": 48.5
    },
    {
      "parent": "深圳美年大健康健康管理有限公司",
      "child": "深圳市美鹏健康管理有限公司 (Lessee)",
      "percentage": 43.9
    },
    {
      "parent": "Ms. Wang Ting",
      "child": "深圳市美鹏健康管理有限公司 (Lessee)",
      "percentage": 7.6
    }
  ],
  "control_relationships": [
    {
      "parent": "MOF(财政部)",
      "child": "北京东富通达投资管理中心 (有限合伙)",
      "relationship_type": "ultimate_control",
      "description": "ultimate control"
    }
  ],
  "all_entities": [
    {
      "name": "MOF(财政部)",
      "type": "company"
    },
    {
      "name": "Mr. Yu Rong",
      "type": "person"
    },
    {
      "name": "北京东富通达投资管理中心 (有限合伙)",
      "type": "company"
    },
    {
      "name": "美年大健康产业控股股份有限公司",
      "type": "company"
    },
    {
      "name": "南通美富健康产业发展合伙企业 (有限合伙)",
      "type": "company"
    },
    {
      "name": "深圳美年大健康健康管理有限公司",
      "type": "company"
    },
    {
      "name": "Ms. Wang Ting",
      "type": "person"
    },
    {
      "name": "深圳市美鹏健康管理有限公司 (Lessee)",
      "type": "company"
    }
  ]
}
'''

# 翻译股权数据的函数（模拟enhanced_equity_to_mermaid.py中的实现）
def translate_equity_data(data):
    """
    翻译股权结构数据中的所有中文实体名称
    """
    translation_map = {}
    successfully_translated = 0
    failed_translations = []
    
    # 提取所有需要翻译的中文名称
    names_to_translate = []
    
    # 添加core_company
    if "core_company" in data and isinstance(data["core_company"], str) and any('\u4e00'-'\u9fff' in name for name in data["core_company"]):
        names_to_translate.append(data["core_company"])
    
    # 添加shareholders
    if "shareholders" in data:
        for shareholder in data["shareholders"]:
            if "name" in shareholder and isinstance(shareholder["name"], str) and any('\u4e00'-'\u9fff' in name for name in shareholder["name"]):
                names_to_translate.append(shareholder["name"])
    
    # 添加top_level_entities
    if "top_level_entities" in data:
        for entity in data["top_level_entities"]:
            if "name" in entity and isinstance(entity["name"], str) and any('\u4e00'-'\u9fff' in name for name in entity["name"]):
                names_to_translate.append(entity["name"])
    
    # 添加entity_relationships中的parent和child
    if "entity_relationships" in data:
        for rel in data["entity_relationships"]:
            if "parent" in rel and isinstance(rel["parent"], str) and any('\u4e00'-'\u9fff' in name for name in rel["parent"]):
                names_to_translate.append(rel["parent"])
            if "child" in rel and isinstance(rel["child"], str) and any('\u4e00'-'\u9fff' in name for name in rel["child"]):
                names_to_translate.append(rel["child"])
    
    # 添加control_relationships中的parent和child
    if "control_relationships" in data:
        for rel in data["control_relationships"]:
            if "parent" in rel and isinstance(rel["parent"], str) and any('\u4e00'-'\u9fff' in name for name in rel["parent"]):
                names_to_translate.append(rel["parent"])
            if "child" in rel and isinstance(rel["child"], str) and any('\u4e00'-'\u9fff' in name for name in rel["child"]):
                names_to_translate.append(rel["child"])
    
    # 添加all_entities
    if "all_entities" in data:
        for entity in data["all_entities"]:
            if "name" in entity and isinstance(entity["name"], str) and any('\u4e00'-'\u9fff' in name for name in entity["name"]):
                names_to_translate.append(entity["name"])
    
    # 去重
    unique_names = list(set(names_to_translate))
    total_chinese_entities = len(unique_names)
    
    # 执行翻译
    for name in unique_names:
        try:
            print(f"正在翻译: {name}")
            success, translated_name, error_msg = translate_with_alicloud(
                name,
                source_language="zh",
                target_language="en"
            )
            
            if success:
                translation_map[name] = translated_name
                successfully_translated += 1
                print(f"翻译成功: {translated_name}")
            else:
                failed_translations.append({"name": name, "error": error_msg})
                print(f"翻译失败: {error_msg}")
        except Exception as e:
            failed_translations.append({"name": name, "error": str(e)})
            print(f"翻译异常: {str(e)}")
    
    # 计算翻译覆盖率
    translation_coverage = (successfully_translated / total_chinese_entities * 100) if total_chinese_entities > 0 else 0
    
    # 返回翻译结果
    return {
        "translation_map": translation_map,
        "total_chinese_entities": total_chinese_entities,
        "successfully_translated": successfully_translated,
        "failed_translations": failed_translations,
        "translation_coverage": translation_coverage
    }

# 执行翻译
try:
    # 解析JSON数据
    equity_data = json.loads(chinese_equity_data)
    
    # 执行翻译
    print("开始翻译股权数据...")
    translation_result = translate_equity_data(equity_data)
    
    # 打印翻译结果
    print("\n翻译结果:")
    print(json.dumps(translation_result, ensure_ascii=False, indent=2))
    
    # 保存翻译结果到文件
    output_file = 'tests/user_equity_translation_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translation_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n翻译结果已保存到 {output_file}")
    
    # 显示翻译覆盖率
    print(f"\n翻译覆盖率: {translation_result['translation_coverage']:.1f}%")
    
    # 如果有失败的翻译，显示错误信息
    if translation_result['failed_translations']:
        print("\n失败的翻译:")
        for failure in translation_result['failed_translations']:
            print(f"- {failure['name']}: {failure['error']}")

except Exception as e:
    print(f"翻译过程中出错: {str(e)}")
    import traceback
    traceback.print_exc()