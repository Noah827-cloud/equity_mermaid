import os
import json
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入所需的函数
try:
    from src.utils.alicloud_translator import translate_with_alicloud
    from src.utils.mermaid_function import generate_mermaid_from_data as generate_mermaid_diagram
    # 如果translate_equity_data函数不在导入路径中，则直接在脚本中定义
    def translate_equity_data(data, translate_names=False):
        """
        翻译股权结构数据
        data: 包含core_company、shareholders和subsidiaries的字典
        translate_names: 是否翻译公司名称和股东名称
        """
        if not translate_names or not data:
            return data
        
        # 深拷贝数据以避免修改原始数据
        translated_data = json.loads(json.dumps(data))
        
        # 创建缓存字典来存储已翻译的内容，避免重复翻译和保持一致性
        translation_cache = {}
        
        # 辅助函数：翻译文本，如果已经翻译过则从缓存获取
        def translate_text(text):
            # 检查是否已经在缓存中
            if text in translation_cache:
                return translation_cache[text]
            
            # 如果不在缓存中，调用翻译API
            try:
                success, translated_name, error_msg = translate_with_alicloud(
                    text, 
                    source_language="zh", 
                    target_language="en"
                )
                if success:
                    # 将翻译结果存入缓存
                    translation_cache[text] = translated_name
                    return translated_name
                else:
                    print(f"⚠️ 翻译 '{text}' 失败: {error_msg}")
                    # 翻译失败时返回原文并缓存
                    translation_cache[text] = text
                    return text
            except Exception as e:
                print(f"⚠️ 翻译 '{text}' 时发生异常: {str(e)}")
                # 发生异常时返回原文并缓存
                translation_cache[text] = text
                return text
        
        # 翻译主公司名称
        if "core_company" in translated_data:
            translated_data["core_company"] = translate_text(translated_data["core_company"])
        # 兼容main_company字段
        elif "main_company" in translated_data:
            translated_data["main_company"] = translate_text(translated_data["main_company"])
        
        # 翻译股东名称
        if "shareholders" in translated_data:
            for shareholder in translated_data["shareholders"]:
                if "name" in shareholder:
                    shareholder["name"] = translate_text(shareholder["name"])
        
        # 翻译子公司名称
        if "subsidiaries" in translated_data:
            for subsidiary in translated_data["subsidiaries"]:
                if "name" in subsidiary:
                    subsidiary["name"] = translate_text(subsidiary["name"])
        
        # 翻译实际控制人
        if "controller" in translated_data and translated_data["controller"]:
            translated_data["controller"] = translate_text(translated_data["controller"])
        
        # 翻译顶层实体名称
        if "top_level_entities" in translated_data:
            for entity in translated_data["top_level_entities"]:
                if "name" in entity:
                    entity["name"] = translate_text(entity["name"])
        
        # 翻译控制关系中的实体名称
        if "control_relationships" in translated_data:
            for rel in translated_data["control_relationships"]:
                if "parent" in rel:
                    rel["parent"] = translate_text(rel["parent"])
                if "child" in rel:
                    rel["child"] = translate_text(rel["child"])
        
        # 翻译实体关系中的实体名称
        if "entity_relationships" in translated_data:
            for rel in translated_data["entity_relationships"]:
                if "parent" in rel:
                    rel["parent"] = translate_text(rel["parent"])
                if "child" in rel:
                    rel["child"] = translate_text(rel["child"])
        
        # 翻译所有实体名称
        if "all_entities" in translated_data:
            for entity in translated_data["all_entities"]:
                if "name" in entity:
                    entity["name"] = translate_text(entity["name"])
        
        return translated_data
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

# 用户提供的原始股权数据
raw_equity_data = {
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

# 测试函数
def test_translation_and_mermaid_generation():
    """
    测试从翻译到生成Mermaid图表的完整流程
    """
    print("=== 开始测试股权数据翻译和Mermaid图表生成 ===")
    
    # 1. 保存原始数据
    with open("original_equity_data.json", "w", encoding="utf-8") as f:
        json.dump(raw_equity_data, f, ensure_ascii=False, indent=2)
    print("✓ 原始股权数据已保存到 original_equity_data.json")
    
    # 2. 执行翻译
    print("\n正在执行股权数据翻译...")
    try:
        translated_data = translate_equity_data(raw_equity_data, translate_names=True)
        
        # 保存翻译后的数据
        with open("translated_equity_data.json", "w", encoding="utf-8") as f:
            json.dump(translated_data, f, ensure_ascii=False, indent=2)
        print("✓ 翻译后的数据已保存到 translated_equity_data.json")
        
        # 打印翻译结果对比
        print("\n翻译结果对比:")
        print(f"原始主公司名称: {raw_equity_data['core_company']}")
        print(f"翻译后主公司名称: {translated_data['core_company']}")
        
        print("\n股东名称翻译:")
        for i, (orig, trans) in enumerate(zip(raw_equity_data['shareholders'], translated_data['shareholders'])):
            if orig['name'] != trans['name']:  # 只打印有变化的
                print(f"  - {orig['name']} -> {trans['name']}")
                
    except Exception as e:
        print(f"❌ 翻译过程中发生错误: {str(e)}")
        translated_data = raw_equity_data  # 使用原始数据继续
        print("⚠️ 将使用原始数据生成Mermaid图表")
    
    # 3. 生成Mermaid图表
    print("\n正在生成Mermaid图表...")
    try:
        mermaid_code = generate_mermaid_diagram(translated_data)
        
        # 保存Mermaid代码
        with open("generated_mermaid_diagram.mmd", "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print("✓ Mermaid图表代码已保存到 generated_mermaid_diagram.mmd")
        
        # 显示部分Mermaid代码
        print("\n生成的Mermaid图表代码(前10行):")
        lines = mermaid_code.split('\n')[:10]
        for line in lines:
            print(f"  {line}")
        
    except Exception as e:
        print(f"❌ 生成Mermaid图表时发生错误: {str(e)}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_translation_and_mermaid_generation()