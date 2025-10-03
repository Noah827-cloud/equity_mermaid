import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from src.utils.mermaid_function import generate_mermaid_from_data

def test_mermaid_generation_with_provided_data():
    """
    使用用户提供的JSON数据测试Mermaid图表生成功能
    """
    # 用户提供的JSON数据
    equity_data = {
        "main_company": "Fujian South Pavement Machinery Co., Ltd.",
        "shareholders": [
            {
                "name": "Fang Qingxi",
                "percentage": 42.71
            },
            {
                "name": "Chen Guihua",
                "percentage": 12.79
            },
            {
                "name": "Fang Kai",
                "percentage": 5.41
            },
            {
                "name": "Quanzhou Zhicheng Investment Partnership (Limited Partnership)",
                "percentage": 4.4
            },
            {
                "name": "Quanzhou Fangyao Investment Partnership (Limited Partnership)",
                "percentage": 3.75
            },
            {
                "name": "Quanzhou Zhixin Investment Partnership (Limited Partnership)",
                "percentage": 3.21
            },
            {
                "name": "Quanzhou Fanghua Investment Partnership (Limited Partnership)",
                "percentage": 1.96
            },
            {
                "name": "Jiang Fenfen",
                "percentage": 0.44
            },
            {
                "name": "Zhu Caiqin",
                "percentage": 0.35
            },
            {
                "name": "UBS AG",
                "percentage": 0.23
            },
            {
                "name": "Weng Rushan",
                "percentage": 0.2162
            },
            {
                "name": "Zhang upright post",
                "percentage": 0.19999
            },
            {
                "name": "Cao Yong",
                "percentage": 0.188
            },
            {
                "name": "You",
                "percentage": 0.1829
            },
            {
                "name": "BARCLAYS BANK PLC",
                "percentage": 0.1712
            },
            {
                "name": "Chen Guoshan",
                "percentage": 0.1641
            },
            {
                "name": "Cathay Pacific Haitong Securities Co., Ltd.",
                "percentage": 0.1344
            }
        ],
        "subsidiaries": [
            {
                "name": "Southern Pavement Machinery (Xiantao) Co., Ltd.",
                "percentage": 100.0
            },
            {
                "name": "Quanzhou Nanfang Road Machine Mobile Crushing Equipment Co., Ltd.",
                "percentage": 100.0
            },
            {
                "name": "Fujian Nante Building Materials Equipment Research Institute Co., Ltd.",
                "percentage": 100.0
            }
        ],
        "controller": "Fang Qingxi",
        "top_level_entities": [
            {
                "name": "Fang Qingxi",
                "percentage": 42.71
            },
            {
                "name": "Chen Guihua",
                "percentage": 12.79
            },
            {
                "name": "Fang Kai",
                "percentage": 5.41
            },
            {
                "name": "Quanzhou Zhicheng Investment Partnership (Limited Partnership)",
                "percentage": 4.4
            },
            {
                "name": "Quanzhou Fangyao Investment Partnership (Limited Partnership)",
                "percentage": 3.75
            },
            {
                "name": "Quanzhou Zhixin Investment Partnership (Limited Partnership)",
                "percentage": 3.21
            },
            {
                "name": "Quanzhou Fanghua Investment Partnership (Limited Partnership)",
                "percentage": 1.96
            }
        ],
        "entity_relationships": [
            {
                "parent": "Fujian South Pavement Machinery Co., Ltd.",
                "child": "Southern Pavement Machinery (Xiantao) Co., Ltd.",
                "percentage": 100
            },
            {
                "parent": "Fujian South Pavement Machinery Co., Ltd.",
                "child": "Quanzhou Nanfang Road Machine Mobile Crushing Equipment Co., Ltd.",
                "percentage": 100
            },
            {
                "parent": "Fujian South Pavement Machinery Co., Ltd.",
                "child": "Fujian Nante Building Materials Equipment Research Institute Co., Ltd.",
                "percentage": 100
            }
        ],
        "control_relationships": [],
        "all_entities": [
            {
                "name": "Fang Qingxi",
                "type": "person"
            },
            {
                "name": "Chen Guihua",
                "type": "person"
            },
            {
                "name": "Fang Kai",
                "type": "person"
            },
            {
                "name": "Quanzhou Zhicheng Investment Partnership (Limited Partnership)",
                "type": "company"
            },
            {
                "name": "Quanzhou Fangyao Investment Partnership (Limited Partnership)",
                "type": "company"
            },
            {
                "name": "Quanzhou Zhixin Investment Partnership (Limited Partnership)",
                "type": "company"
            },
            {
                "name": "Quanzhou Fanghua Investment Partnership (Limited Partnership)",
                "type": "company"
            },
            {
                "name": "Jiang Fenfen",
                "type": "person"
            },
            {
                "name": "Zhu Caiqin",
                "type": "person"
            },
            {
                "name": "UBS AG",
                "type": "company"
            },
            {
                "name": "Weng Rushan",
                "type": "person"
            },
            {
                "name": "Zhang upright post",
                "type": "person"
            },
            {
                "name": "Cao Yong",
                "type": "person"
            },
            {
                "name": "You",
                "type": "person"
            },
            {
                "name": "BARCLAYS BANK PLC",
                "type": "company"
            },
            {
                "name": "Chen Guoshan",
                "type": "person"
            },
            {
                "name": "Cathay Pacific Haitong Securities Co., Ltd.",
                "type": "company"
            },
            {
                "name": "Fujian South Pavement Machinery Co., Ltd.",
                "type": "company"
            },
            {
                "name": "Southern Pavement Machinery (Xiantao) Co., Ltd.",
                "type": "company"
            },
            {
                "name": "Quanzhou Nanfang Road Machine Mobile Crushing Equipment Co., Ltd.",
                "type": "company"
            },
            {
                "name": "Fujian Nante Building Materials Equipment Research Institute Co., Ltd.",
                "type": "company"
            }
        ]
    }

    try:
        # 生成Mermaid图表代码
        print("开始生成Mermaid图表...")
        mermaid_code = generate_mermaid_from_data(equity_data)
        
        # 输出生成的代码
        print("\n生成的Mermaid图表代码:")
        print(mermaid_code)
        
        # 保存到文件
        with open('tests/test_mermaid_output_new.txt', 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        print("\nMermaid图表代码已保存到 tests/test_mermaid_output_new.txt")
        
        # 验证实体数量
        total_entities = len(equity_data['all_entities'])
        print(f"\n验证统计:")
        print(f"- 核心公司: {equity_data['main_company']}")
        print(f"- 股东数量: {len(equity_data['shareholders'])}")
        print(f"- 子公司数量: {len(equity_data['subsidiaries'])}")
        print(f"- 所有实体总数: {total_entities}")
        
        # 验证Mermaid代码中是否包含核心公司
        if equity_data['main_company'] in mermaid_code:
            print("✓ 核心公司已包含在Mermaid图表中")
        else:
            print("✗ 核心公司未包含在Mermaid图表中")
        
        # 验证是否包含股东关系（虽然目前可能只显示子公司关系）
        has_shareholder_connections = False
        for shareholder in equity_data['shareholders']:
            if shareholder['name'] in mermaid_code:
                has_shareholder_connections = True
                break
        
        if has_shareholder_connections:
            print("✓ 股东已包含在Mermaid图表中")
        else:
            print("✗ 股东可能未包含在Mermaid图表中")
            
        return mermaid_code
        
    except Exception as e:
        print(f"生成Mermaid图表时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_mermaid_generation_with_provided_data()