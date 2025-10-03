import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入我们修复过的翻译模块
from src.utils.alicloud_translator import translate_with_alicloud

# 简单的中文实体名称列表用于测试
chinese_entities = [
    "深圳市美鹏健康管理有限公司 (Lessee)",
    "南通美富健康产业发展合伙企业 (有限合伙)",
    "深圳美年大健康健康管理有限公司",
    "北京东富通达投资管理中心 (有限合伙)",
    "美年大健康产业控股股份有限公司",
    "MOF(财政部)"
]

# 执行翻译并记录结果
translation_results = {
    "translations": {},
    "successful_count": 0,
    "failed_count": 0,
    "failures": []
}

print("开始测试翻译功能...\n")

for entity in chinese_entities:
    print(f"翻译实体: {entity}")
    try:
        # 调用修复后的翻译函数
        success, translated, error_msg = translate_with_alicloud(
            entity,
            source_language="zh",
            target_language="en"
        )
        
        if success:
            translation_results["translations"][entity] = translated
            translation_results["successful_count"] += 1
            print(f"✓ 成功: {translated}")
        else:
            translation_results["failures"].append({
                "entity": entity,
                "error": error_msg
            })
            translation_results["failed_count"] += 1
            print(f"✗ 失败: {error_msg}")
    except Exception as e:
        translation_results["failures"].append({
            "entity": entity,
            "error": str(e)
        })
        translation_results["failed_count"] += 1
        print(f"✗ 异常: {str(e)}")
    print()

# 计算翻译成功率
total = len(chinese_entities)
success_rate = (translation_results["successful_count"] / total * 100) if total > 0 else 0

# 输出总结
print("\n翻译测试总结:")
print(f"总实体数: {total}")
print(f"成功数量: {translation_results['successful_count']}")
print(f"失败数量: {translation_results['failed_count']}")
print(f"成功率: {success_rate:.1f}%")

# 保存结果到文件
results_file = os.path.join(os.path.dirname(__file__), 'simple_translation_test_results.json')
with open(results_file, 'w', encoding='utf-8') as f:
    json.dump(translation_results, f, ensure_ascii=False, indent=2)

print(f"\n详细结果已保存到: {results_file}")

# 如果有失败的翻译，显示错误详情
if translation_results['failures']:
    print("\n失败详情:")
    for idx, failure in enumerate(translation_results['failures'], 1):
        print(f"{idx}. {failure['entity']}: {failure['error']}")