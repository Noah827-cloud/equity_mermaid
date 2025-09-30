#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复到V2版本脚本

此脚本用于将mermaid_function.py恢复到V2版本，即当前已保存的mermaid_function_v2.py的内容

使用方法: python restore_v2.py
"""

import os
import shutil
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('restore_v2')

# 定义文件路径
V2_VERSION_FILE = 'mermaid_function_v2.py'
TARGET_FILE = 'mermaid_function.py'


def restore_to_v2():
    """
    将mermaid_function.py恢复到V2版本
    """
    try:
        # 检查V2版本文件是否存在
        if not os.path.exists(V2_VERSION_FILE):
            error_message = f"错误: V2版本文件 {V2_VERSION_FILE} 不存在"
            logger.error(error_message)
            print(error_message)
            return False
        
        # 检查目标文件是否存在
        if os.path.exists(TARGET_FILE):
            # 创建一个备份，以防需要恢复
            backup_file = f"{TARGET_FILE}.bak"
            shutil.copy2(TARGET_FILE, backup_file)
            logger.info(f"已备份当前文件到 {backup_file}")
            print(f"已备份当前文件到 {backup_file}")
        
        # 复制V2版本到目标文件
        shutil.copy2(V2_VERSION_FILE, TARGET_FILE)
        
        logger.info(f"成功恢复到V2版本: {TARGET_FILE} 已更新")
        print(f"成功恢复到V2版本！")
        print(f"{TARGET_FILE} 已更新为V2版本")
        
        return True
    
    except Exception as e:
        error_message = f"恢复过程中发生错误: {str(e)}"
        logger.error(error_message, exc_info=True)
        print(error_message)
        return False


if __name__ == "__main__":
    print("开始恢复到V2版本...")
    success = restore_to_v2()
    
    if success:
        print("\n恢复完成！")
    else:
        print("\n恢复失败，请检查错误信息")