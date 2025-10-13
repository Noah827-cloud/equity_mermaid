#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP环境UVX启动脚本

这个脚本专为在Builder with MCP环境中启动mcp-feedback-enhanced服务而设计，
使用uvx的绝对路径，避免'spawn uvx ENOENT'错误。
"""

import os
import subprocess
import sys

def get_mcp_uvx_path() -> str:
    """
    获取MCP环境中uvx的绝对路径
    
    Returns:
        str: uvx的绝对路径
    """
    # 获取用户主目录
    user_home = os.path.expanduser('~')
    
    # 优先检查Trae AI环境中的uvx路径（根据用户环境信息）
    trae_uvx_path = os.path.join(user_home, '.trae-cn', 'tools', 'uv', 'latest', 'uvx.exe')
    if os.path.exists(trae_uvx_path):
        print(f"MCP环境 - 找到Trae AI环境中的uvx: {trae_uvx_path}")
        return trae_uvx_path
    
    # 检查PATH环境变量中的uvx
    path_env = os.environ.get('PATH', '')
    for path_dir in path_env.split(os.pathsep):
        if path_dir:
            potential_uvx = os.path.join(path_dir, 'uvx.exe' if sys.platform == 'win32' else 'uvx')
            if os.path.exists(potential_uvx):
                print(f"MCP环境 - 在PATH中找到uvx: {potential_uvx}")
                return potential_uvx
    
    # 如果都没找到，尝试从环境变量UVX_PATH获取
    uvx_path_from_env = os.environ.get('UVX_PATH', '')
    if uvx_path_from_env and os.path.exists(uvx_path_from_env):
        print(f"MCP环境 - 从环境变量获取uvx路径: {uvx_path_from_env}")
        return uvx_path_from_env
    
    # 如果所有尝试都失败，返回默认的uvx命令
    print("MCP环境 - 未找到uvx可执行文件，将使用默认'uvx'")
    return 'uvx'

def start_mcp_feedback():
    """
    启动mcp-feedback-enhanced服务
    """
    # 获取uvx的绝对路径
    uvx_path = get_mcp_uvx_path()
    
    # 设置工作目录为用户主目录（根据用户环境信息）
    user_home = os.path.expanduser('~')
    
    # 创建环境变量字典，包含所有必要的环境变量
    env = os.environ.copy()
    
    # 确保Trae AI环境路径在PATH中
    trae_uv_path = os.path.join(user_home, '.trae-cn', 'tools', 'uv', 'latest')
    if os.path.exists(trae_uv_path) and trae_uv_path not in env.get('PATH', ''):
        env['PATH'] = trae_uv_path + os.pathsep + env.get('PATH', '')
    
    # 构建命令
    cmd = [uvx_path, 'mcp-feedback-enhanced@latest']
    
    print(f"MCP环境 - 准备启动服务")
    print(f"- UVX路径: {uvx_path}")
    print(f"- 命令: {cmd}")
    print(f"- 工作目录: {user_home}")
    
    try:
        # 执行命令，不捕获输出以便直接显示到控制台
        process = subprocess.run(
            cmd,
            cwd=user_home,
            env=env,
            check=True
        )
        return process.returncode
    except subprocess.CalledProcessError as e:
        print(f"MCP环境 - 启动失败，返回码: {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"MCP环境 - 启动异常: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = start_mcp_feedback()
    sys.exit(exit_code)