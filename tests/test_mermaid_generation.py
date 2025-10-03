import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入Mermaid图表生成函数
from src.utils.mermaid_function import generate_mermaid_from_data

# 用户提供的JSON数据
equity_data = {
    "name": "A公司",
    "equity_structure": [
        {
            "shareholder_name": "张三",
            "shareholding_percentage": 30,
            "shareholder_type": "自然人",
            "equity_structure": [
                {
                    "shareholder_name": "李四",
                    "shareholding_percentage": 50,
                    "shareholder_type": "自然人"
                },
                {
                    "shareholder_name": "王五",
                    "shareholding_percentage": 50,
                    "shareholder_type": "自然人"
                }
            ]
        },
        {
            "shareholder_name": "B公司",
            "shareholding_percentage": 70,
            "shareholder_type": "法人",
            "equity_structure": [
                {
                    "shareholder_name": "赵六",
                    "shareholding_percentage": 60,
                    "shareholder_type": "自然人"
                },
                {
                    "shareholder_name": "钱七",
                    "shareholding_percentage": 40,
                    "shareholder_type": "自然人"
                }
            ]
        }
    ]
}

# 调用函数生成Mermaid图表
mermaid_code = generate_mermaid_from_data(equity_data)

# 打印生成的Mermaid图表代码
print("生成的Mermaid图表代码:")
print(mermaid_code)

# 将Mermaid代码保存到文件
output_file = 'tests/test_mermaid_output.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(mermaid_code)

print(f"\nMermaid图表代码已保存到 {output_file}")