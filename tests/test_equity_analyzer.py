#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构分析功能测试脚本

该脚本用于测试ai_equity_analyzer.py模块能否通过Excel文件正常调用qwen3-max模型
并返回正确的股权结构信息。
"""

import os
import json
import logging
import time
from typing import Dict, List, Tuple

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("equity_analyzer_test")

# 导入ai_equity_analyzer模块
try:
    from src.utils.ai_equity_analyzer import analyze_equity_with_ai
    logger.info("成功导入ai_equity_analyzer模块")
except ImportError as e:
    logger.error(f"导入模块失败: {str(e)}")
    raise

def read_file_content(file_path: str) -> bytes:
    """读取文件内容为字节"""
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件失败 {file_path}: {str(e)}")
        raise

def test_single_file(file_path: str, prompt: str, api_key: str = None) -> Tuple[Dict, List[str]]:
    """测试单个文件的股权分析"""
    logger.info(f"开始测试文件: {os.path.basename(file_path)}")
    
    # 读取文件内容
    file_content = read_file_content(file_path)
    file_name = os.path.basename(file_path)
    
    # 记录开始时间
    start_time = time.time()
    
    # 调用分析函数
    logger.info(f"调用analyze_equity_with_ai，使用qwen3-max模型分析文件: {file_name}")
    if api_key:
        logger.info("使用实际API密钥进行调用")
    else:
        logger.warning("未提供API密钥，将使用模拟数据")
    
    equity_data, error_logs = analyze_equity_with_ai(
        prompt=prompt,
        file_content=file_content,
        file_name=file_name,
        api_key=api_key
    )
    
    # 计算耗时
    elapsed_time = time.time() - start_time
    logger.info(f"分析完成，耗时: {elapsed_time:.2f} 秒")
    
    # 输出错误日志
    if error_logs:
        logger.warning(f"发现 {len(error_logs)} 个错误/警告:")
        for error in error_logs:
            logger.warning(f"  - {error}")
    else:
        logger.info("没有错误日志")
    
    # 验证返回数据结构
    validate_data_structure(equity_data)
    
    # 输出结果摘要
    output_results_summary(equity_data)
    
    return equity_data, error_logs

def validate_data_structure(equity_data: Dict) -> bool:
    """验证返回数据结构是否正确"""
    required_keys = [
        "core_company", "actual_controller", "top_level_entities", 
        "all_entities", "subsidiaries", "entity_relationships"
    ]
    
    for key in required_keys:
        if key not in equity_data:
            logger.error(f"返回数据缺少必要字段: {key}")
            return False
    
    logger.info("数据结构验证通过")
    return True

def output_results_summary(equity_data: Dict) -> None:
    """输出结果摘要"""
    logger.info("===== 分析结果摘要 =====")
    logger.info(f"核心公司: {equity_data['core_company']}")
    logger.info(f"实际控制人: {equity_data['actual_controller']}")
    logger.info(f"顶级实体数量: {len(equity_data['top_level_entities'])}")
    logger.info(f"子公司数量: {len(equity_data['subsidiaries'])}")
    logger.info(f"实体关系数量: {len(equity_data['entity_relationships'])}")
    
    if equity_data['top_level_entities']:
        logger.info("主要股东:")
        for i, entity in enumerate(equity_data['top_level_entities'][:3]):  # 只显示前3个
            logger.info(f"  {i+1}. {entity['name']}: {entity['percentage']}% ({entity['entity_type']})")
    
    logger.info("=====================")

def load_api_key_from_env() -> str:
    """
    从环境变量加载API密钥
    
    支持从多个可能的环境变量名称中获取API密钥
    """
    # 尝试从多个可能的环境变量名称中获取API密钥
    possible_env_vars = [
        "DASHSCOPE_API_KEY",  # 主环境变量名
        "QIANFAN_API_KEY",    # 可能的备用环境变量名
        "ALI_API_KEY",        # 可能的备用环境变量名
        "DASHSCOPE_KEY"       # 可能的备用环境变量名
    ]
    
    for env_var in possible_env_vars:
        api_key = os.environ.get(env_var)
        if api_key:
            logger.info(f"从环境变量 {env_var} 成功加载API密钥")
            return api_key
    
    logger.warning("未找到API密钥环境变量")
    return ""

def prompt_user_for_api_key() -> str:
    """
    提示用户输入API密钥
    """
    try:
        print("\n请输入DashScope API密钥（输入时不会显示）:")
        # 在Windows中可以使用getpass模块获取密码
        import getpass
        api_key = getpass.getpass()
        if api_key:
            logger.info("成功获取用户输入的API密钥")
            return api_key
    except Exception as e:
        logger.error(f"获取用户输入失败: {str(e)}")
    
    return ""

def main():
    """主函数"""
    # 测试文件路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_files = [
        os.path.join(base_dir, "tests", "福建南方路面机械股份有限公司-对外投资-20250930110317.xlsx"),
        os.path.join(base_dir, "tests", "福建南方路面机械股份有限公司-股东信息最新公示-20250930090121.xlsx")
    ]
    
    # 验证测试文件存在
    for file_path in test_files:
        if not os.path.exists(file_path):
            logger.error(f"测试文件不存在: {file_path}")
            return
    
    # 分析提示词
    prompt = "请分析这家公司的股权结构，重点关注股东信息、持股比例、子公司关系以及实际控制人。请严格按照要求的JSON格式输出结果。"
    
    # 1. 首先尝试从环境变量获取API密钥
    api_key = load_api_key_from_env()
    
    # 2. 如果环境变量中没有找到，询问用户是否要输入
    if not api_key:
        try:
            response = input("环境变量中未找到API密钥，是否要手动输入？(y/n): ")
            if response.lower() == 'y':
                api_key = prompt_user_for_api_key()
        except Exception as e:
            logger.error(f"用户输入交互失败: {str(e)}")
    
    # 3. 显示API密钥使用状态
    if api_key:
        logger.info("将使用实际API密钥进行测试，将调用真实的qwen3-max模型")
        # 显示API密钥的部分信息用于调试，但不显示完整密钥
        masked_key = api_key[:3] + "***" + api_key[-3:] if len(api_key) > 6 else "***"
        logger.info(f"使用的API密钥（部分显示）: {masked_key}")
    else:
        logger.warning("未设置API密钥，将使用模拟数据进行测试")
        print("\n注意：未提供API密钥，将使用模拟数据。要使用真实API，请设置环境变量DASHSCOPE_API_KEY或在提示时输入。\n")
    
    # 创建结果目录
    results_dir = os.path.join(base_dir, "test_results")
    os.makedirs(results_dir, exist_ok=True)
    
    # 依次测试每个文件
    for i, file_path in enumerate(test_files):
        logger.info(f"\n\n========== 开始测试第 {i+1} 个文件 ==========")
        try:
            equity_data, error_logs = test_single_file(file_path, prompt, api_key)
            
            # 保存结果到文件
            result_file = os.path.join(
                results_dir, 
                f"result_{i+1}_{os.path.splitext(os.path.basename(file_path))[0]}.json"
            )
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "file_name": os.path.basename(file_path),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "equity_data": equity_data,
                    "error_logs": error_logs,
                    "used_real_api": bool(api_key)  # 标记是否使用了真实API
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"结果已保存至: {result_file}")
            
        except Exception as e:
            logger.error(f"测试文件 {file_path} 失败: {str(e)}")
        
        logger.info(f"========== 第 {i+1} 个文件测试结束 ==========\n")
        
        # 如果测试多个文件，中间暂停一下
        if i < len(test_files) - 1:
            time.sleep(2)
    
    logger.info("所有测试完成!")

if __name__ == "__main__":
    main()