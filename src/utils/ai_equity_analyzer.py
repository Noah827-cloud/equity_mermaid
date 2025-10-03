#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构AI分析模块

该模块提供使用大模型分析上传文件中的股权结构信息功能，支持：
1. 解析Excel等文件中的股东、实控人、子公司信息
2. 根据用户提示词指导分析过程
3. 生成符合前端需要的股权结构数据格式
"""

import os
import json
import re
import base64
import logging
import pandas as pd
import uuid
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
    from dashscope.api_entities.dashscope_response import Message
    DASHSCOPE_AVAILABLE = True
    # 调试：打印dashscope版本和配置
    logger.info(f"已导入dashscope库，版本: {getattr(dashscope, '__version__', '未知')}")
    
    # 设置API密钥
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    if api_key and hasattr(dashscope, 'api_key'):
        dashscope.api_key = api_key
        logger.info("已直接设置dashscope API密钥")
    
    # 注意：不尝试设置任何URL相关配置，让库使用默认URL
    # 手动设置URL可能导致"url error"问题
except ImportError:
    logger.warning("DashScope库未安装，将使用模拟数据")
    DASHSCOPE_AVAILABLE = False

# 导入其他必要的库
import time

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    从文本中提取JSON数据
    
    Args:
        text: 包含JSON的文本
    
    Returns:
        提取的JSON字典
    
    Raises:
        ValueError: 无法从文本中提取有效JSON
    """
    # 尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 尝试匹配 ```json ... ``` 或 ``` ... ``` 格式
    json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试查找最外层的 {...}
    brace_match = re.search(r"({.*})", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    # 如果都失败，抛出错误并显示原始内容
    raise ValueError(f"无法从以下文本中提取JSON:\n{text}")

def read_excel_file(file_content: bytes) -> Optional[pd.DataFrame]:
    """
    读取Excel文件内容
    
    Args:
        file_content: 文件字节内容
    
    Returns:
        解析后的数据框，如果失败则返回None
    """
    try:
        # 使用pandas读取Excel文件
        import io
        excel_file = io.BytesIO(file_content)
        
        # 尝试多种读取方式
        try:
            df = pd.read_excel(excel_file, engine='openpyxl')
        except Exception:
            # 如果openpyxl失败，尝试xlrd
            excel_file.seek(0)
            df = pd.read_excel(excel_file, engine='xlrd')
        
        # 将所有列转换为字符串类型，避免数据类型问题
        df = df.astype(str)
        return df
    except Exception as e:
        logger.error(f"读取Excel文件失败: {str(e)}")
        return None

def analyze_equity_with_ai(
    prompt: str,
    file_content: Optional[bytes] = None,
    file_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """
    使用大模型分析股权结构信息
    
    Args:
        prompt: 用户提示词，说明股东关系设置要求
        file_content: 上传文件的字节内容
        file_name: 文件名
        api_key: DashScope API密钥
    
    Returns:
        Tuple[股权结构数据字典, 错误日志列表]
    """
    error_logs = []
    equity_data = {
        "core_company": "",
        "actual_controller": "",
        "top_level_entities": [],
        "all_entities": [],
        "subsidiaries": [],
        "entity_relationships": []
    }
    
    try:
        # 准备分析提示词
        analysis_prompt = f"""
        请分析以下股权结构信息，并按照指定格式输出JSON数据。
        
        用户需求说明:
        {prompt}
        
        请按照以下步骤进行分析:
        1. 确定核心公司名称和实际控制人
        2. 识别顶级实体/股东及其持股比例
        3. 识别子公司及其持股关系
        4. 分析实体间的关系，特别是控股关系和虚拟关系
        
        请严格按照以下JSON格式输出结果，不要包含任何其他内容:
        {{
            "core_company": "核心公司名称",
            "actual_controller": "实际控制人",
            "top_level_entities": [
                {{
                    "name": "股东名称",
                    "percentage": 持股比例数字,
                    "entity_type": "股东类型（自然人/法人）"
                }}
            ],
            "subsidiaries": [
                {{
                    "name": "子公司名称",
                    "parent_entity": "母公司名称",
                    "percentage": 持股比例数字
                }}
            ],
            "entity_relationships": [
                {{
                    "from": "实体A名称",
                    "to": "实体B名称",
                    "relationship_type": "关系类型",
                    "description": "关系描述"
                }}
            ]
        }}
        """
        
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
                            "text": "你是一名专业的股权结构分析专家，擅长从文件和文本中提取公司股权关系信息。"
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": []
                }
            ]
            
            # 添加用户提示文本
            messages[1]["content"].append({
                "text": analysis_prompt
            })
            
            # 如果有文件，采用纯文本方式处理
            if file_content and file_name:
                file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
                
                try:
                    logger.info(f"开始处理文件: {file_name} (大小: {len(file_content)/1024:.2f}KB)")
                    
                    # 检查文件大小限制
                    max_file_size_mb = 10
                    if len(file_content) > max_file_size_mb * 1024 * 1024:
                        error_logs.append(f"警告：文件大小超过{max_file_size_mb}MB限制")
                        logger.warning(f"文件太大: {len(file_content) / (1024*1024):.2f}MB")
                    
                    # 直接使用文本方式处理Excel文件
                    if file_extension in ['xlsx', 'xls']:
                        logger.info("处理Excel文件，使用pandas读取内容")
                        df = read_excel_file(file_content)
                        if df is not None:
                            # 限制显示行数，避免内容过多
                            max_rows = 50
                            if len(df) > max_rows:
                                file_description = f"Excel文件'{file_name}'内容(前{max_rows}行，共{len(df)}行):\n"
                                df = df.head(max_rows)
                            else:
                                file_description = f"Excel文件'{file_name}'内容:\n"
                            
                            # 将Excel内容转换为字符串并添加到提示中
                            excel_text = df.to_string(index=False)
                            # 限制文本长度
                            max_text_length = 10000
                            if len(excel_text) > max_text_length:
                                excel_text = excel_text[:max_text_length] + "\n...(内容过长，已截断)"
                            
                            messages[1]["content"][0]["text"] += f"\n\n{file_description}{excel_text}"
                            logger.info("成功将Excel文件内容转换为文本格式并添加到提示中")
                        else:
                            error_logs.append("警告：无法读取Excel文件内容")
                            logger.error("无法读取Excel文件")
                    # 对于文本类文件，直接解码
                    elif file_extension in ['txt', 'csv']:
                        try:
                            text_content = file_content.decode('utf-8', errors='replace')
                            # 限制文本长度
                            max_text_length = 10000
                            if len(text_content) > max_text_length:
                                text_content = text_content[:max_text_length] + "\n...(内容过长，已截断)"
                            
                            messages[1]["content"][0]["text"] += f"\n\n文件'{file_name}'内容:\n{text_content}"
                            logger.info("成功将文本文件内容添加到提示中")
                        except Exception as decode_error:
                            error_msg = f"无法解码文本文件: {str(decode_error)}"
                            error_logs.append(error_msg)
                            logger.error(error_msg)
                    else:
                        # 对于其他类型的文件，尝试简单描述
                        error_logs.append(f"警告：不支持的文件类型 '{file_extension}'，将尝试文本转换")
                        logger.warning(f"不支持的文件类型: {file_extension}")
                        
                        # 尝试作为二进制文件描述
                        messages[1]["content"][0]["text"] += f"\n\n收到文件 '{file_name}'，大小: {len(file_content)/1024:.2f}KB，类型: {file_extension}"
                        
                        # 尝试解码为文本作为回退
                        try:
                            text_content = file_content.decode('utf-8', errors='replace')[:2000]
                            messages[1]["content"][0]["text"] += f"\n文件内容预览:\n{text_content}\n..."
                        except:
                            pass
                except Exception as e:
                    error_msg = f"处理文件时发生错误: {str(e)}"
                    error_logs.append(error_msg)
                    logger.error(error_msg)
                    # 失败时添加基本文件信息
                    messages[1]["content"][0]["text"] += f"\n\n收到文件 '{file_name}'，但处理失败: {str(e)}"
            
            # 调用大模型
            # 对于包含文件的请求，考虑使用更适合多模态内容的模型
            model_to_use = "qwen3-max"
            if file_content and file_name and file_name.split('.')[-1].lower() in ['jpg', 'jpeg', 'png']:
                model_to_use = "qwen3-vl-plus"  # 对于图片文件，使用视觉模型
                
            logger.info(f"准备调用模型: {model_to_use}")
            
            # 简化消息结构，使用最基本的格式
            # 完全避免复杂的多模态结构，只使用简单的文本消息
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
                # 直接设置API密钥（如果未设置）
                if hasattr(dashscope, 'api_key'):
                    api_key = os.environ.get('DASHSCOPE_API_KEY')
                    if api_key:
                        dashscope.api_key = api_key
                        logger.info("已直接设置dashscope API密钥")
                
                # 添加调试信息，检查dashscope配置
                logger.info(f"Dashscope配置检查 - API密钥已设置: {hasattr(dashscope, 'api_key') and bool(dashscope.api_key)}")
                
                # 尝试使用不同的调用方式
                # 一些版本的dashscope可能需要不同的参数或格式
                logger.info("尝试使用基本消息格式调用模型")
                logger.info(f"模型: {model_to_use}, 消息数量: {len(basic_messages)}")
                
                try:
                    # 使用Generation.call - 纯文本接口
                    # 注意：不传递任何URL相关参数，让库使用默认配置
                    response = Generation.call(
                        model=model_to_use,
                        messages=basic_messages,
                        temperature=0.01,  # 低温度以确保确定性输出
                        seed=12345
                    )
                except Exception as call_error:
                    logger.error(f"第一次调用失败: {str(call_error)}")
                    # 如果主要调用失败，记录错误并使用模拟数据
                    logger.error(f"模型调用失败: {str(call_error)}")
                    raise call_error  # 重新抛出原始错误
                
                # 检查响应状态
                if response.status_code != 200:
                    error_logs.append(f"API调用失败: {response.code} - {response.message}")
                    logger.error(f"模型调用失败: {response.code} - {response.message}")
                    # 回退到模拟数据
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
                        
                        # 提取JSON数据
                        extracted_data = extract_json_from_text(text_output)
                        
                        # 验证和转换数据格式
                        equity_data = validate_and_convert_equity_data(extracted_data, error_logs)
                        
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
        
        # 如果不使用真实API或API调用失败，使用模拟数据生成
        if not use_real_api:
            logger.info("使用模拟数据生成股权结构")
            equity_data = generate_mock_equity_data(prompt, file_name, error_logs)
        
        # 确保数据完整性
        equity_data = ensure_data_completeness(equity_data)
        
        # 生成分析报告
        report = generate_analysis_report(equity_data)
        equity_data['report'] = report
        
        logger.info(f"股权结构分析完成，识别到 {len(equity_data['top_level_entities'])} 个顶级实体和 {len(equity_data['subsidiaries'])} 个子公司")
        
    except Exception as e:
        error_msg = f"分析过程中发生错误: {str(e)}"
        logger.error(error_msg)
        error_logs.append(error_msg)
        
        # 即使出错也生成基本报告
        if 'equity_data' in locals():
            report = generate_analysis_report(equity_data)
            equity_data['report'] = report
    
    # 确保equity_data存在并包含report字段
    if 'equity_data' not in locals():
        equity_data = {}
    if 'report' not in equity_data:
        equity_data['report'] = "未能生成分析报告"
    
    return equity_data, error_logs

def validate_and_convert_equity_data(data: Dict[str, Any], error_logs: List[str]) -> Dict[str, Any]:
    """
    验证并转换股权数据格式
    
    Args:
        data: 从大模型提取的数据
        error_logs: 错误日志列表
    
    Returns:
        验证后的股权数据
    """
    validated_data = {
        "core_company": data.get("core_company", ""),
        "actual_controller": data.get("actual_controller", ""),
        "top_level_entities": [],
        "all_entities": [],
        "subsidiaries": [],
        "entity_relationships": [],
        "control_relationships": []  # 添加控制关系列表
    }
    
    # 验证和转换顶级实体
    if "top_level_entities" in data:
        for idx, entity in enumerate(data["top_level_entities"]):
            try:
                # 提取持股比例
                percentage = entity.get("percentage", 0)
                if isinstance(percentage, str):
                    # 尝试从字符串中提取数字
                    match = re.search(r'\d+(?:\.\d+)?', percentage)
                    if match:
                        percentage = float(match.group())
                    else:
                        percentage = 0
                
                # 验证数据
                if not entity.get("name"):
                    error_logs.append(f"顶级实体 #{idx+1} 缺少名称")
                    continue
                
                if percentage < 0 or percentage > 100:
                    error_logs.append(f"顶级实体 {entity.get('name')} 的持股比例 {percentage} 超出范围")
                    percentage = max(0, min(100, percentage))
                
                # 创建实体对象
                validated_entity = {
                    "name": entity.get("name").strip(),
                    "percentage": float(percentage),
                    "entity_type": entity.get("entity_type", "未知")
                }
                
                validated_data["top_level_entities"].append(validated_entity)
                validated_data["all_entities"].append(validated_entity)
                
            except Exception as e:
                error_logs.append(f"处理顶级实体 #{idx+1} 时出错: {str(e)}")
    
    # 验证和转换子公司
    if "subsidiaries" in data:
        for idx, sub in enumerate(data["subsidiaries"]):
            try:
                # 提取持股比例
                percentage = sub.get("percentage", 0)
                if isinstance(percentage, str):
                    # 尝试从字符串中提取数字
                    match = re.search(r'\d+(?:\.\d+)?', percentage)
                    if match:
                        percentage = float(match.group())
                    else:
                        percentage = 0
                
                # 验证数据
                if not sub.get("name"):
                    error_logs.append(f"子公司 #{idx+1} 缺少名称")
                    continue
                
                if percentage < 0 or percentage > 100:
                    error_logs.append(f"子公司 {sub.get('name')} 的持股比例 {percentage} 超出范围")
                    percentage = max(0, min(100, percentage))
                
                # 创建子公司对象
                validated_sub = {
                    "name": sub.get("name").strip(),
                    "parent_entity": sub.get("parent_entity", validated_data["core_company"]),
                    "percentage": float(percentage)
                }
                
                validated_data["subsidiaries"].append(validated_sub)
                
            except Exception as e:
                error_logs.append(f"处理子公司 #{idx+1} 时出错: {str(e)}")
    
    # 验证和转换实体关系
    if "entity_relationships" in data:
        # 创建子公司名称集合，用于快速检查
        subsidiary_names = set()
        if data.get("subsidiaries"):
            for sub in data["subsidiaries"]:
                if sub.get("name"):
                    subsidiary_names.add(sub.get("name").strip())
        
        for idx, rel in enumerate(data["entity_relationships"]):
            try:
                if not rel.get("from") or not rel.get("to"):
                    error_logs.append(f"实体关系 #{idx+1} 缺少必要的实体信息")
                    continue
                
                from_entity = rel.get("from").strip()
                to_entity = rel.get("to").strip()
                rel_type = rel.get("relationship_type", "关联")
                
                # 避免重复添加控股关系：如果是核心公司对子公司的控股关系，且该子公司已在subsidiaries中，则跳过
                if (from_entity == validated_data["core_company"] and 
                    to_entity in subsidiary_names and 
                    ("控股" in rel_type or "持有" in rel_type or "100%" in rel.get("description", ""))):
                    logger.info(f"跳过重复的控股关系: {from_entity} -> {to_entity}")
                    continue
                
                validated_rel = {
                    "from": from_entity,
                    "to": to_entity,
                    "relationship_type": rel_type,
                    "description": rel.get("description", "")
                }
                
                validated_data["entity_relationships"].append(validated_rel)
                
            except Exception as e:
                error_logs.append(f"处理实体关系 #{idx+1} 时出错: {str(e)}")
    
    # 自动添加实控人到控制关系
    if validated_data["actual_controller"] and validated_data["core_company"]:
        # 检查是否已经存在相同的控制关系
        exists = False
        for rel in validated_data.get("control_relationships", []):
            if (rel.get("parent") == validated_data["actual_controller"] and 
                rel.get("child") == validated_data["core_company"]):
                exists = True
                break
        
        # 如果不存在，则添加新的控制关系
        if not exists:
            control_rel = {
                "parent": validated_data["actual_controller"],
                "child": validated_data["core_company"],
                "relationship_type": "实际控制",
                "description": f"{validated_data['actual_controller']}是{validated_data['core_company']}的实际控制人"
            }
            validated_data["control_relationships"].append(control_rel)
    
    return validated_data

def generate_mock_equity_data(prompt: str, file_name: Optional[str], error_logs: List[str]) -> Dict[str, Any]:
    """
    生成模拟的股权数据，优先从测试结果目录加载真实测试数据
    
    Args:
        prompt: 用户提示词
        file_name: 文件名
        error_logs: 错误日志列表
    
    Returns:
        模拟的股权数据
    """
    error_logs.append("使用测试数据，实际部署时请配置有效的API密钥")
    
    # 尝试从test_results目录加载真实测试数据
    test_results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'test_results')
    
    # 测试数据文件列表
    test_files = [
        os.path.join(test_results_dir, 'result_1_福建南方路面机械股份有限公司-对外投资-20250930110317.json'),
        os.path.join(test_results_dir, 'result_2_福建南方路面机械股份有限公司-股东信息最新公示-20250930090121.json')
    ]
    
    # 根据文件名选择合适的测试数据
    selected_file = None
    if file_name:
        # 如果文件名包含特定关键词，选择对应的测试数据
        if any(keyword in file_name for keyword in ['投资', '对外']):
            selected_file = test_files[0]  # 对外投资数据
        elif any(keyword in file_name for keyword in ['股东', '股权']):
            selected_file = test_files[1]  # 股东信息数据
    
    # 如果没有根据文件名选择，尝试随机选择一个测试文件
    if not selected_file and test_files:
        selected_file = test_files[0]  # 默认选择第一个
    
    # 尝试加载测试数据文件
    if selected_file and os.path.exists(selected_file):
        try:
            logger.info(f"加载测试数据文件: {selected_file}")
            with open(selected_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            
            # 提取股权数据部分
            if 'equity_data' in test_data:
                equity_data = test_data['equity_data']
                logger.info(f"成功加载测试数据，包含 {len(equity_data.get('top_level_entities', []))} 个顶级实体")
                # 确保返回的数据结构完整
                return ensure_data_completeness(equity_data)
        except Exception as e:
            error_msg = f"加载测试数据失败: {str(e)}"
            error_logs.append(error_msg)
            logger.error(error_msg)
    else:
        logger.warning(f"测试数据文件不存在: {selected_file}")
    
    # 如果加载测试数据失败，使用硬编码的模拟数据作为回退
    logger.info("使用硬编码模拟数据作为回退")
    mock_data = {
        "core_company": "示例科技有限公司",
        "actual_controller": "张三",
        "top_level_entities": [
            {"name": "张三", "percentage": 45.0, "entity_type": "自然人"},
            {"name": "李四", "percentage": 25.0, "entity_type": "自然人"},
            {"name": "投资机构A", "percentage": 20.0, "entity_type": "法人"},
            {"name": "投资机构B", "percentage": 10.0, "entity_type": "法人"}
        ],
        "all_entities": [
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
        ]
    }
    
    # 如果提示词中提到特定内容，调整模拟数据
    if "控股" in prompt or "控制" in prompt:
        mock_data["actual_controller"] = "主要控股方"
    
    if "虚拟关系" in prompt:
        mock_data["entity_relationships"].append(
            {"from": "投资机构A", "to": "投资机构B", "relationship_type": "虚拟关系", "description": "战略合作"}
        )
    
    return mock_data

def ensure_data_completeness(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    确保股权数据的完整性
    
    Args:
        data: 股权数据
    
    Returns:
        完整的股权数据
    """
    # 确保所有必要的键存在
    required_keys = [
        "core_company", "actual_controller", "top_level_entities", 
        "all_entities", "subsidiaries", "entity_relationships", "control_relationships"
    ]
    
    for key in required_keys:
        if key not in data:
            data[key] = [] if key.endswith('ies') or key.endswith('s') else ""    
    
    # 自动创建个人股东与核心公司的股权关系
    if data["core_company"] and isinstance(data["top_level_entities"], list) and isinstance(data["entity_relationships"], list):
        # 获取现有关系中已存在的(股东->核心公司)对
        existing_relationships = set()
        for rel in data["entity_relationships"]:
            rel_from = rel.get("from", "")
            rel_to = rel.get("to", "")
            if rel_to == data["core_company"]:
                existing_relationships.add(rel_from)
        
        # 为顶级个人股东创建股权关系
        for entity in data["top_level_entities"]:
            entity_name = entity.get("name", "")
            entity_type = entity.get("entity_type", "")
            percentage = entity.get("percentage", 0)
            
            # 只处理有名称的股东，且不存在已有关系
            if entity_name and entity_name not in existing_relationships and percentage > 0:
                equity_rel = {
                    "from": entity_name,
                    "to": data["core_company"],
                    "relationship_type": "持股",
                    "description": f"持有{data['core_company']}{percentage}%的股权"
                }
                data["entity_relationships"].append(equity_rel)
    
    # 确保all_entities包含所有top_level_entities
    if not data["all_entities"] and data["top_level_entities"]:
        data["all_entities"] = data["top_level_entities"].copy()
    
    # 自动添加实控人到控制关系（如果不存在）
    if data["actual_controller"] and data["core_company"] and isinstance(data["control_relationships"], list):
        # 检查是否已经存在相同的控制关系（同时考虑parent/child和from/to两种格式）
        exists = False
        for rel in data["control_relationships"]:
            # 检查两种格式的关系是否已经存在
            if ((rel.get("parent") == data["actual_controller"] and 
                 rel.get("child") == data["core_company"]) or 
                (rel.get("from") == data["actual_controller"] and 
                 rel.get("to") == data["core_company"])):
                exists = True
                break
        
        # 如果不存在，则添加新的控制关系
        if not exists:
            control_rel = {
                "parent": data["actual_controller"],
                "child": data["core_company"],
                "relationship_type": "实际控制",
                "description": f"{data['actual_controller']}是{data['core_company']}的实际控制人"
            }
            data["control_relationships"].append(control_rel)
    
    # 如果没有核心公司名称，使用默认值
    if not data["core_company"]:
        data["core_company"] = "未命名公司"
    if not data["actual_controller"] and data["top_level_entities"]:
        # 找出持股比例最高的实体
        max_entity = max(data["top_level_entities"], key=lambda x: x.get("percentage", 0), default=None)
        if max_entity:
            data["actual_controller"] = max_entity.get("name", "")
    
    # 避免重复的控股关系：检查control_relationships中是否存在与subsidiaries重复的控股关系
    if "control_relationships" in data and "subsidiaries" in data and isinstance(data["control_relationships"], list):
        # 创建子公司名称集合，用于快速检查
        subsidiary_names = set()
        for sub in data["subsidiaries"]:
            if sub.get("name"):
                subsidiary_names.add(sub.get("name").strip())
        
        # 过滤掉重复的控股关系
        filtered_relationships = []
        for rel in data["control_relationships"]:
            # 获取关系的来源和目标（兼容parent/child和from/to两种格式）
            rel_parent = rel.get("parent", rel.get("from", ""))
            rel_child = rel.get("child", rel.get("to", ""))
            
            # 如果是核心公司对子公司的控股关系，且该子公司已在subsidiaries中，则跳过
            if (rel_parent == data["core_company"] and 
                rel_child in subsidiary_names and 
                ("控股" in rel.get("relationship_type", "") or "持有" in rel.get("relationship_type", "") or 
                 "100%" in rel.get("description", ""))):
                logger.info(f"过滤掉重复的控股关系: {rel_parent} -> {rel_child}")
                continue
            
            filtered_relationships.append(rel)
        
        # 更新控制关系列表
        data["control_relationships"] = filtered_relationships
    
    return data

# 辅助函数：生成完整的股权结构分析报告
def generate_analysis_report(result: Dict[str, Any], content_to_analyze: Optional[str] = None) -> str:
    """
    生成包含核心公司、实际控制人、股东、子公司、关联关系及总结的完整报告
    
    Args:
        result: 分析结果数据
        content_to_analyze: 用于分析的原始内容
        
    Returns:
        格式化的分析报告文本
    """
    report_sections = []
    
    # 一、基本信息
    core_company = result.get('core_company', '未命名公司')
    report_sections.append(f"一、基本信息")
    report_sections.append(f"核心公司：{core_company}")
    
    # 获取实际控制人信息
    controller_info = identify_actual_controller(result)
    controller_name = controller_info.get('name', '未明确')
    controller_reason = controller_info.get('reason', '')
    report_sections.append(f"实际控制人：{controller_name}")
    if controller_reason:
        report_sections.append(f"确认依据：{controller_reason}")
    report_sections.append("")
    
    # 二、股东结构概览
    shareholders = result.get('shareholders', result.get('top_level_entities', []))
    report_sections.append(f"二、股东结构概览")
    report_sections.append(f"股东总数：{len(shareholders)}名")
    
    # 计算自然人股东和法人股东数量
    natural_persons = [s for s in shareholders if s.get('type') == 'person' or '自然人' in str(s.get('description', ''))]
    legal_persons = [s for s in shareholders if s not in natural_persons]
    report_sections.append(f"其中：自然人股东{len(natural_persons)}名，法人股东{len(legal_persons)}名")
    report_sections.append("")
    
    # 三、主要股东及其持股比例
    report_sections.append(f"三、主要股东及其持股比例")
    if shareholders:
        # 按持股比例降序排序
        sorted_shareholders = sorted(shareholders, key=lambda x: x.get('percentage', 0), reverse=True)
        
        # 显示主要股东（显示前5名）
        for i, shareholder in enumerate(sorted_shareholders[:5]):
            name = shareholder.get('name', '未知')
            percentage = shareholder.get('percentage', 0)
            entity_type = "自然人" if shareholder in natural_persons else "法人"
            report_sections.append(f"{i+1}. {name}（{entity_type}）：{percentage}%")
        
        # 如果有更多股东，显示汇总信息
        if len(sorted_shareholders) > 5:
            other_percentage = sum(s.get('percentage', 0) for s in sorted_shareholders[5:])
            report_sections.append(f"6. 其他股东（共{len(sorted_shareholders) - 5}名）：合计{other_percentage:.2f}%")
    else:
        report_sections.append("未获取到股东信息")
    report_sections.append("")
    
    # 四、子公司关系
    subsidiaries = result.get('subsidiaries', [])
    report_sections.append(f"四、子公司关系")
    if subsidiaries:
        report_sections.append(f"子公司总数：{len(subsidiaries)}家")
        
        # 显示主要子公司（前5家）
        for i, subsidiary in enumerate(subsidiaries[:5]):
            name = subsidiary.get('name', '未知')
            percentage = subsidiary.get('percentage', 0)
            report_sections.append(f"{i+1}. {name}：持股{percentage}%")
        
        # 如果有更多子公司，显示汇总信息
        if len(subsidiaries) > 5:
            report_sections.append(f"... 等{len(subsidiaries) - 5}家子公司")
    else:
        report_sections.append("未获取到子公司信息")
    report_sections.append("")
    
    # 五、控制关系分析
    control_relationships = result.get('control_relationships', [])
    report_sections.append(f"五、控制关系分析")
    if control_relationships:
        report_sections.append(f"控制关系数量：{len(control_relationships)}条")
        
        # 显示关键控制关系
        for rel in control_relationships[:5]:
            parent = rel.get('parent', rel.get('from', '未知'))
            child = rel.get('child', rel.get('to', '未知'))
            desc = rel.get('description', '控制关系')
            report_sections.append(f"- {parent} → {child}：{desc}")
    else:
        report_sections.append("未获取到明确的控制关系信息")
    report_sections.append("")
    
    # 六、股权结构总结
    report_sections.append(f"六、股权结构总结")
    summary = generate_summary(result)
    report_sections.append(summary)
    
    return "\n".join(report_sections)

# 辅助函数：识别实际控制人
def identify_actual_controller(result: Dict[str, Any]) -> Dict[str, str]:
    """
    基于持股比例识别实际控制人
    
    Args:
        result: 分析结果数据
        
    Returns:
        包含实际控制人名称和确认依据的字典
    """
    shareholders = result.get('shareholders', result.get('top_level_entities', []))
    core_company = result.get('core_company', '目标公司')
    
    # 如果结果中已经有实际控制人信息，直接返回
    if 'actual_controller' in result and result['actual_controller']:
        return {
            "name": result['actual_controller'],
            "reason": f"根据分析结果直接确认{result['actual_controller']}为实际控制人"
        }
    
    if not shareholders:
        return {"name": "未明确", "reason": "无股东信息可用于判断实际控制人"}
    
    # 按持股比例降序排序
    sorted_shareholders = sorted(shareholders, key=lambda x: x.get('percentage', 0), reverse=True)
    top_shareholder = sorted_shareholders[0]
    top_percentage = top_shareholder.get('percentage', 0)
    
    # 判断控制类型
    if top_percentage > 50:
        return {
            "name": top_shareholder.get('name', '未知'),
            "reason": f"直接持有公司{top_percentage}%的股份，持股比例超过50%，对公司拥有绝对控股权"
        }
    elif len(sorted_shareholders) >= 2 and top_percentage > sorted_shareholders[1].get('percentage', 0) * 2:
        second_percentage = sorted_shareholders[1].get('percentage', 0)
        return {
            "name": top_shareholder.get('name', '未知'),
            "reason": f"持有{top_percentage}%的股份，是第二大股东持股比例（{second_percentage}%）的两倍以上，相对控股地位明显"
        }
    elif len(sorted_shareholders) >= 3 and top_percentage > sum(s.get('percentage', 0) for s in sorted_shareholders[1:3]):
        second_third_percentage = sum(s.get('percentage', 0) for s in sorted_shareholders[1:3])
        return {
            "name": top_shareholder.get('name', '未知'),
            "reason": f"持有{top_percentage}%的股份，超过第二、三大股东持股比例之和（{second_third_percentage}%），相对控股"
        }
    else:
        # 检查是否有明确的控制关系
        control_relationships = result.get('control_relationships', [])
        for rel in control_relationships:
            if rel.get('child') == core_company or rel.get('to') == core_company:
                controller = rel.get('parent', rel.get('from', '未知'))
                return {
                    "name": controller,
                    "reason": f"通过控制关系确认{controller}对{core_company}具有控制权"
                }
        
        return {
            "name": top_shareholder.get('name', '未知'),
            "reason": f"持有{top_percentage}%的股份，为第一大股东，但持股比例不高，可能存在共同控制或无实际控制人情况"
        }

# 辅助函数：生成股权结构总结
def generate_summary(result: Dict[str, Any]) -> str:
    """
    生成股权结构总结
    
    Args:
        result: 分析结果数据
        
    Returns:
        股权结构总结文本
    """
    core_company = result.get('core_company', '目标公司')
    shareholders = result.get('shareholders', result.get('top_level_entities', []))
    subsidiaries = result.get('subsidiaries', [])
    
    if not shareholders:
        return f"{core_company}股权结构信息不足，无法提供有效分析。"
    
    # 计算前三大股东持股比例
    sorted_shareholders = sorted(shareholders, key=lambda x: x.get('percentage', 0), reverse=True)
    top_3_percentage = sum(s.get('percentage', 0) for s in sorted_shareholders[:3])
    
    # 判断股权集中度
    if top_3_percentage > 70:
        concentration = "股权高度集中"
    elif top_3_percentage > 50:
        concentration = "股权相对集中"
    else:
        concentration = "股权较为分散"
    
    # 获取实际控制人信息
    controller_info = identify_actual_controller(result)
    controller_name = controller_info.get('name', '未知')
    
    # 构建总结
    summary = f"{core_company}{concentration}，{controller_name}"
    
    if top_3_percentage > 50:
        summary += f"处于相对控股地位，前三大股东合计持股约{top_3_percentage:.2f}%，控制权较为稳定"
    else:
        summary += f"为主要股东，前三大股东合计持股约{top_3_percentage:.2f}%，可能存在股权制衡关系"
    
    if subsidiaries:
        summary += f"。公司拥有{len(subsidiaries)}家子公司，形成一定规模的企业集团结构"
    
    summary += "。建议关注公司章程中关于重大事项表决机制的规定，以及是否存在一致行动协议等特殊安排，这些因素可能对公司实际控制权产生重要影响。"
    
    return summary

if __name__ == "__main__":
    # 测试代码
    test_prompt = "请分析这家公司的股权结构，特别关注控股关系和虚拟关系"
    result, errors = analyze_equity_with_ai(test_prompt)
    print("分析结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if errors:
        print("\n错误日志:")
        for error in errors:
            print(f"- {error}")