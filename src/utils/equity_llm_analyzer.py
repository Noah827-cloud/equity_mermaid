#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构LLM分析模块

该模块提供使用大模型分析已定义股权关系数据的功能，支持：
1. 连接DashScope大模型API
2. 根据用户定义的股权关系生成详细分析报告
3. 按照指定维度分析股权结构
"""

import os
import json
import re
import logging
import time
from typing import Dict, List, Optional, Any, Tuple

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试导入dashscope库
try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
    logger.info(f"已导入dashscope库，版本: {getattr(dashscope, '__version__', '未知')}")
    
    # 设置API密钥
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    if api_key and hasattr(dashscope, 'api_key'):
        dashscope.api_key = api_key
        logger.info("已直接设置dashscope API密钥")
except ImportError:
    logger.warning("DashScope库未安装，将使用模拟分析结果")
    DASHSCOPE_AVAILABLE = False

def create_equity_analysis_prompt(equity_data: Dict[str, Any]) -> str:
    """
    创建股权结构分析的提示词
    
    Args:
        equity_data: 股权关系数据
    
    Returns:
        格式化的提示词字符串
    """
    # 将股权数据转换为易于理解的文本格式
    core_company = equity_data.get('core_company', '未命名公司')
    
    # 提取股东信息
    shareholders_info = []
    top_level_entities = equity_data.get('top_level_entities', [])
    if top_level_entities:
        for entity in top_level_entities:
            name = entity.get('name', '未知')
            percentage = entity.get('percentage', 0)
            entity_type = entity.get('entity_type', '未知类型')
            shareholders_info.append(f"{name}（{entity_type}）: {percentage}%")
    else:
        # 从entity_relationships中提取股东信息
        relationships = equity_data.get('entity_relationships', [])
        for rel in relationships:
            if rel.get('relationship_type') == '持股' and rel.get('to') == core_company:
                percentage_match = rel.get('description', '')
                shareholders_info.append(f"{rel.get('from', '未知')}: {percentage_match}")
    
    # 提取子公司信息
    subsidiaries_info = []
    subsidiaries = equity_data.get('subsidiaries', [])
    if subsidiaries:
        for sub in subsidiaries:
            name = sub.get('name', '未知')
            percentage = sub.get('percentage', 0)
            subsidiaries_info.append(f"{name}: 持股{percentage}%")
    else:
        # 从entity_relationships中提取子公司信息
        relationships = equity_data.get('entity_relationships', [])
        for rel in relationships:
            if rel.get('relationship_type') == '持股' and rel.get('from') == core_company:
                percentage_match = rel.get('description', '')
                subsidiaries_info.append(f"{rel.get('to', '未知')}: {percentage_match}")
    
    # 提取控制关系信息
    control_relationships = equity_data.get('control_relationships', [])
    control_info = []
    for rel in control_relationships:
        parent = rel.get('parent', rel.get('from', '未知'))
        child = rel.get('child', rel.get('to', '未知'))
        desc = rel.get('description', '控制关系')
        control_info.append(f"{parent} → {child}: {desc}")
    
    # 提取关联关系信息
    related_relationships = []
    for rel in equity_data.get('entity_relationships', []):
        if rel.get('relationship_type') not in ['持股', '控股']:
            related_relationships.append(f"{rel.get('from', '未知')} → {rel.get('to', '未知')}: {rel.get('description', '')}")
    
    # 创建完整的提示词
    prompt = f"""
我需要你作为一名专业的股权结构分析专家，对以下公司的股权结构进行详细分析。

核心公司：{core_company}

股东信息：
{"\n".join(shareholders_info) if shareholders_info else "无明确股东信息"}

子公司信息：
{"\n".join(subsidiaries_info) if subsidiaries_info else "无子公司信息"}

控制关系：
{"\n".join(control_info) if control_info else "无明确控制关系"}

关联关系：
{"\n".join(related_relationships) if related_relationships else "无明确关联关系"}

请按照以下维度进行详细分析，格式必须严格遵循示例：

一、核心公司
{core_company}。

二、实际控制人
实际控制人为[实际控制人名称]。
理由：[详细说明判断依据，包括持股比例分析、股权结构特点等]

三、主要股东及其持股比例（合并小于1%的股东）
[列出主要股东及其持股比例，将持股比例低于1%的股东合并为"其他股东"类别]

四、子公司关系
[分析子公司结构、持股比例、控制关系等]

五、关联关系说明
[分析公司内部可能存在的关联关系，如亲属关系、一致行动人等]

总结：
[对公司股权结构进行总体评价，包括股权集中度、控制权稳定性等]

请确保分析内容详细、专业，并严格按照指定格式输出。
"""
    
    return prompt

def analyze_equity_with_llm(equity_data: Dict[str, Any], api_key: Optional[str] = None) -> Tuple[str, List[str]]:
    """
    使用大语言模型分析股权结构数据
    
    Args:
        equity_data: 股权关系数据
        api_key: DashScope API密钥
    
    Returns:
        Tuple[分析报告文本, 错误日志列表]
    """
    error_logs = []
    analysis_report = ""
    
    try:
        # 创建分析提示词
        prompt = create_equity_analysis_prompt(equity_data)
        
        # 检查是否使用真实API
        use_real_api = DASHSCOPE_AVAILABLE and api_key
        
        if use_real_api:
            logger.info("使用真实API进行股权结构分析")
            
            # 设置API密钥
            dashscope.api_key = api_key
            
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "text": "你是一名专业的股权结构分析专家，擅长分析公司的股权结构、实际控制人、关联关系等。请严格按照用户指定的格式输出分析结果。"
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # 调用大模型
            model_to_use = "qwen3-max"
            logger.info(f"准备调用模型: {model_to_use}")
            
            # 简化消息结构
            basic_messages = []
            for msg in messages:
                # 提取纯文本内容
                content = msg["content"]
                if isinstance(content, list):
                    # 如果是列表，尝试提取文本内容
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            text_content = item["text"]
                            break
                    basic_messages.append({
                        "role": msg["role"],
                        "content": text_content
                    })
                else:
                    # 如果是简单文本，直接使用
                    basic_messages.append({
                        "role": msg["role"],
                        "content": content
                    })
            
            try:
                # 使用Generation.call - 纯文本接口
                response = Generation.call(
                    model=model_to_use,
                    messages=basic_messages,
                    temperature=0.01,  # 低温度以确保确定性输出
                    seed=12345
                )
                
                # 检查响应状态
                if response.status_code != 200:
                    error_logs.append(f"API调用失败: {response.code} - {response.message}")
                    logger.error(f"模型调用失败: {response.code} - {response.message}")
                    # 回退到模拟分析
                    use_real_api = False
                else:
                    logger.info("API调用成功，正在解析响应")
                    # 解析模型输出
                    try:
                        text_output = ""
                        if hasattr(response, 'output') and hasattr(response.output, 'choices') and response.output.choices:
                            if hasattr(response.output.choices[0], 'message') and hasattr(response.output.choices[0].message, 'content'):
                                contents = response.output.choices[0].message.content
                                if isinstance(contents, str):
                                    # 如果content是字符串，直接使用
                                    text_output = contents.strip()
                                elif isinstance(contents, list):
                                    # 如果是列表，尝试提取文本内容
                                    for item in contents:
                                        if isinstance(item, dict) and item.get("text"):
                                            text_output = item["text"].strip()
                                            break
                                else:
                                    # 尝试将内容转换为字符串
                                    text_output = str(contents).strip()
                        
                        if not text_output:
                            raise ValueError("模型返回为空或格式异常")
                        
                        analysis_report = text_output
                        
                    except Exception as e:
                        error_logs.append(f"解析模型输出失败: {str(e)}")
                        logger.error(f"解析响应失败: {str(e)}")
                        use_real_api = False
            except Exception as e:
                # 捕获API调用过程中的所有异常
                error_msg = f"模型调用异常: {str(e)}"
                error_logs.append(error_msg)
                logger.error(error_msg)
                use_real_api = False
        
        # 如果不使用真实API或API调用失败，使用模拟分析
        if not use_real_api:
            logger.info("使用模拟分析生成股权结构报告")
            analysis_report = generate_mock_analysis_report(equity_data, error_logs)
        
    except Exception as e:
        error_msg = f"分析过程中发生错误: {str(e)}"
        logger.error(error_msg)
        error_logs.append(error_msg)
        analysis_report = f"分析失败: {str(e)}"
    
    return analysis_report, error_logs

def generate_mock_analysis_report(equity_data: Dict[str, Any], error_logs: List[str]) -> str:
    """
    生成模拟的股权分析报告
    
    Args:
        equity_data: 股权关系数据
        error_logs: 错误日志列表
    
    Returns:
        模拟的分析报告文本
    """
    error_logs.append("使用模拟分析结果，实际部署时请配置有效的API密钥")
    
    core_company = equity_data.get('core_company', '未命名公司')
    
    # 从top_level_entities中获取股东信息
    top_level_entities = equity_data.get('top_level_entities', [])
    # 如果没有top_level_entities，尝试从entity_relationships中提取
    if not top_level_entities and 'entity_relationships' in equity_data:
        shareholders_set = set()
        for rel in equity_data['entity_relationships']:
            if rel.get('relationship_type') == '持股' and rel.get('to') == core_company:
                percentage_match = rel.get('description', '')
                shareholders_set.add((rel.get('from', '未知'), percentage_match))
        
        top_level_entities = []
        for name, percentage_desc in shareholders_set:
            # 尝试从描述中提取百分比数字
            import re
            percentage_match = re.search(r'\d+(?:\.\d+)?', percentage_desc)
            percentage = float(percentage_match.group()) if percentage_match else 0
            top_level_entities.append({
                "name": name,
                "percentage": percentage,
                "entity_type": "自然人"
            })
    
    # 按持股比例排序
    sorted_entities = sorted(top_level_entities, key=lambda x: x.get('percentage', 0), reverse=True)
    
    # 确定实际控制人
    actual_controller = ""
    controller_reason = ""
    if sorted_entities:
        actual_controller = sorted_entities[0].get('name', '未知')
        top_percentage = sorted_entities[0].get('percentage', 0)
        
        if top_percentage > 50:
            controller_reason = f"{actual_controller}直接持有公司{top_percentage}%的股份，为第一大股东，持股比例超过50%，对公司拥有绝对控股权。"
        elif len(sorted_entities) >= 2 and top_percentage > sorted_entities[1].get('percentage', 0) * 2:
            second_percentage = sorted_entities[1].get('percentage', 0)
            controller_reason = f"{actual_controller}持有公司{top_percentage}%的股份，为第一大股东，其持股比例是第二大股东（{sorted_entities[1].get('name', '未知')}持股{second_percentage}%）的两倍以上，相对控股地位明显。"
        else:
            controller_reason = f"{actual_controller}持有公司{top_percentage}%的股份，为第一大股东，结合公司股权结构，可合理判断其对公司拥有控制性表决权。"
    
    # 构建主要股东信息
    major_shareholders = []
    other_shareholders = []
    other_percentage = 0
    
    for entity in sorted_entities:
        percentage = entity.get('percentage', 0)
        if percentage >= 1:
            major_shareholders.append(f"{entity.get('name', '未知')}（{entity.get('entity_type', '自然人')}）：{percentage}%")
        else:
            other_shareholders.append(entity.get('name', '未知'))
            other_percentage += percentage
    
    # 处理其他股东
    if other_shareholders:
        major_shareholders.append(f"其他股东（包括{', '.join(other_shareholders[:3])}{'等' if len(other_shareholders) > 3 else ''}）：合计约{other_percentage:.2f}%")
    
    # 获取子公司信息
    subsidiaries = equity_data.get('subsidiaries', [])
    # 如果没有subsidiaries，尝试从entity_relationships中提取
    if not subsidiaries and 'entity_relationships' in equity_data:
        subsidiary_set = set()
        for rel in equity_data['entity_relationships']:
            if rel.get('relationship_type') == '持股' and rel.get('from') == core_company:
                percentage_match = rel.get('description', '')
                subsidiary_set.add((rel.get('to', '未知'), percentage_match))
        
        subsidiaries = []
        for name, percentage_desc in subsidiary_set:
            # 尝试从描述中提取百分比数字
            import re
            percentage_match = re.search(r'\d+(?:\.\d+)?', percentage_desc)
            percentage = float(percentage_match.group()) if percentage_match else 0
            subsidiaries.append({
                "name": name,
                "parent_entity": core_company,
                "percentage": percentage
            })
    
    subsidiary_info = []
    if subsidiaries:
        for sub in subsidiaries:
            subsidiary_info.append(f"{sub.get('name', '未知')}：持股{sub.get('percentage', 0)}%")
    
    # 构建关联关系说明
    related_info = []
    for rel in equity_data.get('entity_relationships', []):
        if rel.get('relationship_type') not in ['持股', '控股']:
            related_info.append(f"{rel.get('from', '未知')}与{rel.get('to', '未知')}之间存在{rel.get('description', '关联关系')}")
    
    # 生成总结
    if sorted_entities:
        top_3_percentage = sum(entity.get('percentage', 0) for entity in sorted_entities[:3])
        if top_3_percentage > 70:
            concentration = "股权高度集中"
        elif top_3_percentage > 50:
            concentration = "股权相对集中"
        else:
            concentration = "股权较为分散"
        
        summary = f"{core_company}{concentration}，{actual_controller}"
        if top_3_percentage > 50:
            summary += f"处于相对控股地位，前三大股东合计持股约{top_3_percentage:.2f}%，控制权较为稳定"
        else:
            summary += f"为主要股东，前三大股东合计持股约{top_3_percentage:.2f}%，可能存在股权制衡关系"
        
        if subsidiaries:
            summary += f"。公司拥有{len(subsidiaries)}家子公司，形成一定规模的企业集团结构"
        
        summary += "。建议关注公司章程中关于重大事项表决机制的规定，以及是否存在一致行动协议等特殊安排，这些因素可能对公司实际控制权产生重要影响。"
    else:
        summary = f"{core_company}股权结构信息不足，无法提供有效分析。"
    
    # 构建完整报告
    report_sections = [
        f"一、核心公司\n{core_company}。\n",
        f"二、实际控制人\n实际控制人为{actual_controller}。\n理由：{controller_reason}\n",
        f"三、主要股东及其持股比例（合并小于1%的股东）\n{'\n'.join(major_shareholders) if major_shareholders else '未获取到股东信息'}\n",
        f"四、子公司关系\n{'\n'.join(subsidiary_info) if subsidiary_info else '未获取到子公司信息'}\n",
        f"五、关联关系说明\n{'\n'.join(related_info) if related_info else '未发现明确的关联关系'}\n",
        f"总结：\n{summary}"
    ]
    
    return '\n'.join(report_sections)

if __name__ == "__main__":
    # 测试代码
    test_data = {
        "core_company": "示例科技有限公司",
        "actual_controller": "张三",
        "top_level_entities": [
            {"name": "张三", "percentage": 45.0, "entity_type": "自然人"},
            {"name": "李四", "percentage": 25.0, "entity_type": "自然人"},
            {"name": "投资机构A", "percentage": 20.0, "entity_type": "法人"},
            {"name": "投资机构B", "percentage": 10.0, "entity_type": "法人"}
        ],
        "subsidiaries": [
            {"name": "子公司A", "parent_entity": "示例科技有限公司", "percentage": 80.0},
            {"name": "子公司B", "parent_entity": "示例科技有限公司", "percentage": 60.0}
        ],
        "entity_relationships": [
            {"from": "张三", "to": "李四", "relationship_type": "合作伙伴", "description": "共同创始人"}
        ],
        "control_relationships": [
            {"parent": "张三", "child": "示例科技有限公司", "relationship_type": "实际控制", "description": "张三是示例科技有限公司的实际控制人"}
        ]
    }
    
    report, errors = analyze_equity_with_llm(test_data)
    print("分析报告:")
    print(report)
    if errors:
        print("\n错误日志:")
        for error in errors:
            print(f"- {error}")