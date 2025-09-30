import os
import json
import re
import base64
import dashscope
from dashscope import MultiModalConversation

# === 配置 ===
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
if not dashscope.api_key:
    dashscope.api_key = "your_dashscope_api_key_here"  # ← 替换为你的 API Key

# === 辅助函数 ===
def extract_json_from_text(text: str):
    """从任意文本中提取第一个合法 JSON"""
    try:
        return json.loads(text.strip())
    except:
        pass

    # 尝试 ```json ... ``` 或 {...}
    patterns = [r"```(?:json)?\s*({.*?})\s*```", r"({.*})"]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                continue
    raise ValueError(f"无法提取 JSON: {text[:200]}...")

def escape_mermaid_text(text: str) -> str:
    text = str(text)
    text = text.replace("\\", "\\\\")
    text = text.replace("\n", "\\n")
    text = text.replace('"', '\\"')
    return text

# === 核心：图像转结构化股权数据 ===
def image_to_structured_equity(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = (
        "你是一名顶级企业尽调专家，请严格按以下步骤分析股权结构图：\n\n"
        
        "【步骤1】识别所有实体节点，包括：\n"
        "- 自然人（如 Mr. Ho Kuk Sing）\n"
        "- 境外公司（标注注册地，如 HK, JP）\n"
        "- 境内公司（含 Shanghai, Yunnan 等）\n"
        "- 上市公司（标注股票代码）\n\n"
        
        "【步骤2】识别所有直接持股关系，格式为：[出资方] --[持股比例%]--> [被投资方]\n"
        "注意：只提取图中明确画出的箭头关系，不要推断间接关系。\n\n"
        
        "【步骤3】确定核心运营公司（通常是境内主体，名称含 'Shanghai' 或 'Medical Equipment'）\n\n"
        
        "【步骤4】输出一个 JSON，包含：\n"
        "- 'entities': 列表，每个元素为 {'id': 'E1', 'name': '...', 'type': 'person/company'}\n"
        "- 'relations': 列表，每个元素为 {'from': 'E1', 'to': 'E2', 'ratio': 0.2729}\n"
        "- 'core_company_id': 'E5'\n\n"
        
        "【重要】\n"
        "- 不要合并节点！每个方框是一个独立实体。\n"
        "- 比例必须是小数（如 27.29% → 0.2729）\n"
        "- 名称必须完整，不得缩写（如 'Mr. Leung King Sun' 不能写成 'Mr. Leung King'）\n"
        "- 不要添加任何解释，只输出 JSON\n\n"
        
        "示例格式：\n"
        "{\n"
        '  "entities": [\n'
        '    {"id": "P1", "name": "Mr. Ho Kuk Sing", "type": "person"},\n'
        '    {"id": "C1", "name": "IVD Medical Holding Limited (HKEX: 01931)", "type": "company"}\n'
        "  ],\n"
        '  "relations": [\n'
        '    {"from": "P1", "to": "C1", "ratio": 0.1129}\n'
        "  ],\n"
        '  "core_company_id": "C5"\n'
        "}"
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"image": f"data:image/png;base64,{img_base64}"},
                {"text": prompt}
            ]
        }
    ]

    response = MultiModalConversation.call(
        model='qwen3-vl-plus',
        messages=messages,
        temperature=0.01,
        seed=12345
    )

    if response.status_code != 200:
        raise Exception(f"API Error: {response.code} - {response.message}")

    text_output = ""
    try:
        contents = response.output.choices[0].message.content
        for item in contents:
            if item.get("text"):
                text_output = item["text"].strip()
                break
    except Exception as e:
        raise Exception(f"解析模型输出失败: {e}")

    if not text_output:
        raise Exception("模型返回为空")

    return extract_json_from_text(text_output)

# === 生成 Mermaid ===
def generate_mermaid_from_structured(data: dict) -> str:
    entity_map = {e["id"]: e for e in data["entities"]}
    core_id = data["core_company_id"]
    
    lines = ["graph TD"]
    
    # 添加所有关系
    for rel in data["relations"]:
        src = entity_map[rel["from"]]
        tgt = entity_map[rel["to"]]
        src_name = escape_mermaid_text(src["name"])
        tgt_name = escape_mermaid_text(tgt["name"])
        ratio = rel["ratio"]
        lines.append(f'    {rel["from"]}["{src_name}"] -->|{ratio:.4%}| {rel["to"]}["{tgt_name}"]')
    
    # 样式定义
    lines.extend([
        "",
        "    classDef person fill:#ffebee,stroke:#f44336;",
        "    classDef company fill:#bbdefb,stroke:#1976d2;",
        "    classDef sub fill:#e0f7fa,stroke:#00bcd4;"
    ])
    
    # 应用样式
    for eid, ent in entity_map.items():
        cls = "person" if ent["type"] == "person" else "company"
        lines.append(f"    class {eid} {cls}")
    
    return "\n".join(lines)

# === 主函数 ===
def main(image_path: str):
    print("🧠 Qwen-VL 正在分析复杂股权结构图（结构化模式）...")
    try:
        structured_data = image_to_structured_equity(image_path)
        print("✅ 结构化数据提取成功：")
        print(json.dumps(structured_data, ensure_ascii=False, indent=2))

        mermaid_code = generate_mermaid_from_structured(structured_data)
        print("\n🎨 Mermaid 代码：\n")
        print(mermaid_code)

        output_file = image_path.rsplit(".", 1)[0] + "_structured.mmd"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print(f"\n💾 已保存至: {output_file}")
        print("🌐 复制代码到 https://mermaid.live 预览")
    except Exception as e:
        print("❌ 错误：", str(e))

# === 运行入口 ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("用法: python equity_structured.py 股权图.png")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.isfile(image_path):
        print(f"❌ 文件不存在: {image_path}")
        sys.exit(1)

    main(image_path)