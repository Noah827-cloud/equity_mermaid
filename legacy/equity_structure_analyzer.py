import requests
import json
from typing import Dict, List

def analyze_equity_structure(
    input_text: str,
    api_endpoint: str = None,
    api_key: str = None,
    model: str = None,
    timeout: int = 30
) -> Dict:
    """
    分析股权结构文本，返回结构化JSON
    """
    from config import API_KEY, API_ENDPOINT, MODEL, TIMEOUT

    api_key = api_key or API_KEY
    api_endpoint = api_endpoint or API_ENDPOINT
    model = model or MODEL
    timeout = timeout or TIMEOUT

    prompt = f"""
你是一个专业的财务股权结构分析师，请严格按照以下规则解析输入的股权结构图或描述：

### 📌 一、扫描顺序：
- 从上到下、从左到右逐层扫描所有实体节点。
- 每一层按“左侧 → 右侧”顺序处理，避免跳层或遗漏。

### 📌 二、连接线类型识别：
- 实线（Solid Line）→ 表示直接持股或控制关系，必须标注持股比例。
- 虚线（Dashed Line）→ 表示集体控制、关联方、非直接持股但具有控制权的关系。
- 无连线实体 → 若某实体上方无任何连接线，标记为“独立股东”或“外部投资方”。

### 📌 三、实体类型与属性提取：
对每个实体，提取以下字段：
1. 实体名称
2. 注册地/上市地
3. 持股比例（若有）
4. 控制类型（直接持股 / 集体控制 / 合资 / 投资合伙等）
5. 特殊标签（如 A/R seller, A/R debtor 1 等）
6. 子节点列表（向下控股的实体名称 + 持股比例）

### 📌 四、特别注意事项：
- 若某节点上方无持股比例且无连接线 → 判定为“顶层独立实体”。
- 若持股比例未标明但有连接线 → 标注“比例未明”。
- 合资结构 → 必须同时列出所有出资方及其持股比例。
- 多级控制 → 明确每一层的控制路径。

### 📌 五、输出格式要求（严格JSON）：
{{
  "top_level": [
    {{
      "name": "Mr. Ho Kuk Sing",
      "type": "natural_person",
      "control_type": "collective_control",
      "ownership_ratio": "11.29%",
      "connects_to": ["IVD Medical Holding Limited"]
    }}
  ],
  "structure_tree": [
    {{
      "parent": "IVD Medical Holding Limited",
      "children": [
        {{
          "name": "Vastec Medical Limited",
          "ownership_ratio": "100%",
          "registration": "HK registered"
        }}
      ]
    }}
  ]
}}

现在请分析以下股权结构描述：

---
{input_text}
---
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的财务股权结构分析师，只输出结构化JSON，不加任何解释或说明。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()

        ai_output = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        parsed_json = json.loads(ai_output)

        return parsed_json

    except Exception as e:
        raise RuntimeError(f"股权结构分析失败: {str(e)}") from e
