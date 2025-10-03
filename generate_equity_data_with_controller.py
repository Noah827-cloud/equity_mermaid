import json
import os

# 创建包含实控人信息的完整equity_data JSON文件
def create_equity_data_with_controller():
    # 基本数据结构
    equity_data = {
        "actual_controller": "方庆熙",
        "core_company": "福建南方路面机械股份有限公司",
        "shareholders": [],
        "subsidiaries": [],
        "all_entities": ["方庆熙", "福建南方路面机械股份有限公司"],
        "entity_relationships": [],
        "control_relationships": [
            {
                "parent": "方庆熙",
                "child": "福建南方路面机械股份有限公司",
                "relationship_type": "实际控制",
                "description": "方庆熙为福建南方路面机械股份有限公司的识别出实际控制人"
            }
        ]
    }
    
    # 保存到文件
    output_file = "equity_data_with_controller.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(equity_data, f, ensure_ascii=False, indent=2)
        print(f"已成功生成 {output_file}")
        return output_file
    except Exception as e:
        print(f"保存文件时出错: {e}")
        return None

# 显示导入说明
def display_import_instructions(file_path):
    print("\n=== 导入实控人信息指南 ===")
    print(f"已生成包含实控人信息的完整equity_data文件: {file_path}")
    print("\n使用步骤：")
    print("1. 在Streamlit应用中，进入'手动编辑模式'")
    print("2. 点击'导入数据'按钮")
    print("3. 选择刚刚生成的'equity_data_with_controller.json'文件")
    print("4. 点击'上传'按钮完成导入")
    print("5. 进入'定义关系'步骤，您将看到实控人关系已添加")
    
    print("\n或者，您也可以手动添加控制关系：")
    print("1. 确保'方庆熙'和'福建南方路面机械股份有限公司'都已添加为实体")
    print("2. 进入'定义关系'步骤")
    print("3. 在'添加控制关系'部分，选择：")
    print("   - 控制方: 方庆熙")
    print("   - 被控制方: 福建南方路面机械股份有限公司")
    print("   - 关系描述: 方庆熙为福建南方路面机械股份有限公司的识别出实际控制人")
    print("4. 点击'添加控制关系'按钮")

# 主函数
def main():
    print("=== 实控人数据生成工具 ===")
    
    # 创建equity_data文件
    file_path = create_equity_data_with_controller()
    if file_path:
        display_import_instructions(file_path)

if __name__ == "__main__":
    main()