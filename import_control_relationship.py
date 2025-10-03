import json
import os

# 读取控制关系JSON文件
def load_control_relationship():
    file_path = 'control_relationship.json'
    if not os.path.exists(file_path):
        print(f"错误：找不到文件 {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            relationship = json.load(f)
        return relationship
    except json.JSONDecodeError as e:
        print(f"错误：JSON解析失败 - {e}")
        return None

# 转换为系统可用的格式
def prepare_relationship_for_system(relationship):
    # 确保包含所有必要的字段
    system_relationship = {
        "parent": relationship.get("parent", ""),
        "child": relationship.get("child", ""),
        "description": relationship.get("description", ""),
        # 可选字段
        "relationship_type": relationship.get("relationship_type", "实际控制")
    }
    return system_relationship

# 显示如何使用这个关系
def display_usage_instructions(relationship):
    print("\n控制关系已成功加载：")
    print(f"实际控制人: {relationship['parent']}")
    print(f"被控制实体: {relationship['child']}")
    print(f"关系类型: {relationship['relationship_type']}")
    print(f"描述: {relationship['description']}")
    
    print("\n使用说明：")
    print("1. 在Streamlit应用中，进入'手动编辑模式'")
    print("2. 确保'方庆熙'和'福建南方路面机械股份有限公司'都已添加为实体")
    print("3. 进入'定义关系'步骤")
    print("4. 在'添加控制关系'部分，选择：")
    print(f"   - 控制方: {relationship['parent']}")
    print(f"   - 被控制方: {relationship['child']}")
    print(f"   - 关系描述: {relationship['description']}")
    print("5. 点击'添加控制关系'按钮")
    
    print("\n或者，如果您想通过代码导入，请将以下数据添加到st.session_state.equity_data['control_relationships']中：")
    print(json.dumps(relationship, ensure_ascii=False, indent=2))

# 主函数
def main():
    print("=== 实控人关系导入工具 ===")
    
    # 加载控制关系
    relationship = load_control_relationship()
    if not relationship:
        return
    
    # 准备系统格式
    system_relationship = prepare_relationship_for_system(relationship)
    
    # 显示使用说明
    display_usage_instructions(system_relationship)

if __name__ == "__main__":
    main()