#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UVX执行辅助模块

这个模块提供了一个统一的接口来执行uvx命令，优先使用.env文件中配置的绝对路径，
避免在不同环境下可能出现的'spawn uvx ENOENT'错误。
"""

import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple, Union

def get_uvx_path() -> str:
    """
    获取uvx的执行路径
    
    优先从环境变量UVX_PATH获取绝对路径，然后检查常见的uvx安装位置
    
    Returns:
        str: uvx的执行路径
    """
    # 优先从环境变量获取配置的绝对路径
    uvx_path = os.environ.get('UVX_PATH', '').strip()
    
    # 检查路径是否有效
    if uvx_path and os.path.exists(uvx_path):
        return uvx_path
    
    # 如果是Windows系统，尝试添加.exe扩展名
    if sys.platform == 'win32' and not uvx_path.endswith('.exe'):
        uvex_path_exe = uvx_path + '.exe'
        if os.path.exists(uvex_path_exe):
            return uvex_path_exe
    
    # 检查Trae AI环境中的uvx路径
    user_home = os.path.expanduser('~')
    trae_uvx_paths = [
        os.path.join(user_home, '.trae-cn', 'tools', 'uv', 'latest', 'uvx.exe'),
        os.path.join(user_home, '.trae-cn', 'tools', 'uv', 'latest', 'uvx'),
    ]
    for path in trae_uvx_paths:
        if os.path.exists(path):
            print(f"找到Trae AI环境中的uvx: {path}")
            return path
    
    # 检查虚拟环境中的uvx路径
    venv_uvx_paths = [
        os.path.join(os.path.dirname(sys.executable), 'Scripts', 'uvx.exe'),
        os.path.join(os.path.dirname(sys.executable), 'Scripts', 'uvx'),
        os.path.join(os.path.dirname(sys.executable), 'uvx.exe'),
        os.path.join(os.path.dirname(sys.executable), 'uvx'),
    ]
    for path in venv_uvx_paths:
        if os.path.exists(path):
            print(f"找到虚拟环境中的uvx: {path}")
            return path
    
    # 检查PATH环境变量中的uvx
    path_env = os.environ.get('PATH', '')
    for path_dir in path_env.split(os.pathsep):
        if path_dir:
            potential_uvx = os.path.join(path_dir, 'uvx.exe' if sys.platform == 'win32' else 'uvx')
            if os.path.exists(potential_uvx):
                print(f"在PATH中找到uvx: {potential_uvx}")
                return potential_uvx
    
    # 如果都没找到，返回'uvx'命令名，让系统在PATH中查找
    print("未找到uvx可执行文件，将使用系统PATH查找")
    return 'uvx'

def run_uvx_command(args: Union[str, List[str]], 
                    capture_output: bool = True,
                    text: bool = True,
                    shell: bool = False,
                    env: Optional[Dict[str, str]] = None,
                    cwd: Optional[str] = None,
                    timeout: Optional[int] = None,
                    **kwargs) -> subprocess.CompletedProcess:
    """
    执行uvx命令，优先使用配置的绝对路径
    
    Args:
        args: 命令参数，可以是字符串或列表
        capture_output: 是否捕获输出，默认为True
        text: 是否以文本模式处理输出，默认为True
        shell: 是否在shell中执行，默认为False
        env: 环境变量字典，如果为None则使用当前环境
        cwd: 工作目录，如果为None则使用当前工作目录
        timeout: 超时时间（秒）
        **kwargs: 传递给subprocess.run的其他参数
    
    Returns:
        subprocess.CompletedProcess: 命令执行结果
    
    Raises:
        subprocess.SubprocessError: 命令执行失败时抛出
    """
    # 获取uvx路径
    uvx_path = get_uvx_path()
    
    # 构建命令
    if isinstance(args, str):
        # 如果args是字符串，需要在shell模式下执行
        cmd = f"{uvx_path} {args}"
        shell = True
    else:
        # 如果args是列表，将uvx路径作为第一个元素
        cmd = [uvx_path] + args
    
    # 确保环境变量包含Python Scripts目录
    if env is None:
        env = os.environ.copy()
    
    # 获取Python可执行文件所在目录（Scripts目录）
    scripts_dir = os.path.dirname(sys.executable)
    if scripts_dir not in env.get('PATH', ''):
        # 将Scripts目录添加到PATH环境变量的最前面
        env['PATH'] = scripts_dir + os.pathsep + env.get('PATH', '')
    
    # 添加Trae AI环境路径到PATH
    user_home = os.path.expanduser('~')
    trae_uv_path = os.path.join(user_home, '.trae-cn', 'tools', 'uv', 'latest')
    if os.path.exists(trae_uv_path) and trae_uv_path not in env.get('PATH', ''):
        env['PATH'] = trae_uv_path + os.pathsep + env.get('PATH', '')
    
    # 使用指定的工作目录或默认目录
    working_dir = cwd if cwd is not None else os.getcwd()
    
    # 执行命令
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=text,
            shell=shell,
            env=env,
            cwd=working_dir,
            timeout=timeout,
            **kwargs
        )
        return result
    except Exception as e:
        # 添加更多调试信息
        error_msg = f"执行uvx命令失败: {str(e)}"
        error_msg += f"\n- UVX路径: {uvx_path}"
        error_msg += f"\n- 命令: {cmd}"
        error_msg += f"\n- Python路径: {sys.executable}"
        error_msg += f"\n- Scripts目录: {scripts_dir}"
        error_msg += f"\n- 执行工作目录: {working_dir}"
        error_msg += f"\n- 当前工作目录: {os.getcwd()}"
        error_msg += f"\n- PATH包含Trae UV: {trae_uv_path in env.get('PATH', '')}"
        
        # 尝试使用更详细的异常信息
        if hasattr(e, 'errno'):
            error_msg += f"\n- 错误码: {e.errno}"
        
        # 包装并重新抛出异常
        if isinstance(e, subprocess.SubprocessError):
            raise subprocess.SubprocessError(error_msg) from e
        else:
            raise subprocess.SubprocessError(error_msg) from e

def is_uvx_available() -> Tuple[bool, str]:
    """
    检查uvx是否可用
    
    Returns:
        Tuple[bool, str]: (是否可用, 版本信息或错误信息)
    """
    try:
        result = run_uvx_command(['--version'])
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, f"命令执行失败，返回码: {result.returncode}, 错误: {result.stderr.strip()}"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    # 测试uvx是否可用
    available, info = is_uvx_available()
    print(f"UVX可用状态: {'✓ 可用' if available else '✗ 不可用'}")
    print(f"详细信息: {info}")
    
    # 打印UVX路径信息
    print(f"使用的UVX路径: {get_uvx_path()}")
    
    # 测试在不同工作目录下执行uvx
    print("\n测试在用户主目录下执行uvx:")
    user_home = os.path.expanduser('~')
    try:
        result = run_uvx_command(['--version'], cwd=user_home)
        print(f"在用户主目录下执行成功: {result.stdout.strip()}")
    except Exception as e:
        print(f"在用户主目录下执行失败: {str(e)}")