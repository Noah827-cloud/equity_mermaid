#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件加密工具
用于加密和解密配置文件中的敏感信息
"""

import json
import base64
from cryptography.fernet import Fernet
import os
import argparse


def generate_key():
    """生成加密密钥"""
    return Fernet.generate_key()


def save_key(key, key_file='config.key'):
    """保存密钥到文件"""
    with open(key_file, 'wb') as f:
        f.write(key)
    print(f"密钥已保存到 {key_file}")
    print("警告：请妥善保管此密钥文件，不要提交到版本控制系统！")


def load_key(key_file='config.key'):
    """从文件加载密钥"""
    with open(key_file, 'rb') as f:
        return f.read()


def encrypt_config(config_file, key, output_file=None):
    """加密配置文件"""
    # 读取配置文件
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 使用Fernet加密
    fernet = Fernet(key)
    
    # 加密敏感字段 - 这里以alicloud_translator为例，可根据需要扩展
    if 'alicloud_translator' in config:
        translator_config = config['alicloud_translator']
        # 加密access_key_id和access_key_secret
        if 'access_key_id' in translator_config:
            translator_config['access_key_id'] = fernet.encrypt(
                translator_config['access_key_id'].encode()
            ).decode()
        if 'access_key_secret' in translator_config:
            translator_config['access_key_secret'] = fernet.encrypt(
                translator_config['access_key_secret'].encode()
            ).decode()
    
    # 标记文件已加密
    config['__encrypted__'] = True
    
    # 保存加密后的配置
    output = output_file or f"{config_file}.encrypted"
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"配置文件已加密并保存到 {output}")


def decrypt_config(config_file, key, output_file=None):
    """解密配置文件"""
    # 读取加密的配置文件
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 检查是否已加密
    if not config.get('__encrypted__', False):
        print("警告：配置文件似乎未加密")
        return
    
    # 使用Fernet解密
    fernet = Fernet(key)
    
    # 解密敏感字段
    if 'alicloud_translator' in config:
        translator_config = config['alicloud_translator']
        # 解密access_key_id和access_key_secret
        if 'access_key_id' in translator_config:
            translator_config['access_key_id'] = fernet.decrypt(
                translator_config['access_key_id'].encode()
            ).decode()
        if 'access_key_secret' in translator_config:
            translator_config['access_key_secret'] = fernet.decrypt(
                translator_config['access_key_secret'].encode()
            ).decode()
    
    # 移除加密标记
    config.pop('__encrypted__', None)
    
    # 保存解密后的配置
    output = output_file or f"{config_file.replace('.encrypted', '')}"
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"配置文件已解密并保存到 {output}")


def main():
    parser = argparse.ArgumentParser(description='配置文件加密工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 生成密钥命令
    parser_gen = subparsers.add_parser('generate', help='生成新的加密密钥')
    parser_gen.add_argument('--output', '-o', default='config.key', help='密钥输出文件')
    
    # 加密配置命令
    parser_enc = subparsers.add_parser('encrypt', help='加密配置文件')
    parser_enc.add_argument('--config', '-c', default='config.json', help='配置文件路径')
    parser_enc.add_argument('--key', '-k', default='config.key', help='密钥文件路径')
    parser_enc.add_argument('--output', '-o', help='加密后配置输出路径')
    
    # 解密配置命令
    parser_dec = subparsers.add_parser('decrypt', help='解密配置文件')
    parser_dec.add_argument('--config', '-c', default='config.json.encrypted', help='加密配置文件路径')
    parser_dec.add_argument('--key', '-k', default='config.key', help='密钥文件路径')
    parser_dec.add_argument('--output', '-o', help='解密后配置输出路径')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        key = generate_key()
        save_key(key, args.output)
    
    elif args.command == 'encrypt':
        if not os.path.exists(args.key):
            print(f"错误：密钥文件 {args.key} 不存在")
            print("请先运行 'python config_encryptor.py generate' 生成密钥")
            return
        
        if not os.path.exists(args.config):
            print(f"错误：配置文件 {args.config} 不存在")
            return
        
        key = load_key(args.key)
        encrypt_config(args.config, key, args.output)
    
    elif args.command == 'decrypt':
        if not os.path.exists(args.key):
            print(f"错误：密钥文件 {args.key} 不存在")
            return
        
        if not os.path.exists(args.config):
            print(f"错误：配置文件 {args.config} 不存在")
            return
        
        key = load_key(args.key)
        decrypt_config(args.config, key, args.output)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()