import os
import json
import time
import uuid
import hmac
import hashlib
import urllib.parse
import requests
import base64
from cryptography.fernet import Fernet

# 检查是否在Streamlit Cloud环境中
IS_STREAMLIT_CLOUD = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'

def load_key(key_file='config.key'):
    """加载加密密钥"""
    try:
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        return None
    except Exception as e:
        print(f"加载密钥失败: {e}")
        return None

def decrypt_config_data(encrypted_data, key):
    """解密配置数据"""
    try:
        fernet = Fernet(key)
        # 确保encrypted_data是bytes类型
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        return fernet.decrypt(encrypted_data).decode()
    except Exception as e:
        print(f"解密数据失败: {e}")
        return None

def get_access_key():
    """
    从配置文件或环境变量获取阿里云访问密钥
    支持加密和未加密的配置文件
    """
    # 1. 优先从环境变量获取（Streamlit Cloud推荐方式）
    access_key_id = os.environ.get('ALICLOUD_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('ALICLOUD_ACCESS_KEY_SECRET')
    
    if access_key_id and access_key_secret:
        return access_key_id, access_key_secret
    
    # 2. 在Streamlit Cloud环境中，如果没有环境变量，则跳过配置文件读取
    if IS_STREAMLIT_CLOUD:
        print("Streamlit Cloud环境：未设置环境变量，跳过配置文件读取")
        return None, None
    
    # 3. 在本地环境中尝试从配置文件获取
    try:
        # 从配置文件读取
        if not os.path.exists('config.json'):
            print("配置文件不存在")
            return None, None
            
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查是否包含阿里云翻译配置
        if 'alicloud_translator' not in config:
            print("配置中未包含alicloud_translator部分")
            return None, None
        
        translator_config = config['alicloud_translator']
        
        # 检查是否为加密配置
        if translator_config.get('__encrypted__', False) or config.get('__encrypted__', False):
            print("检测到加密配置，尝试解密...")
            # 尝试加载密钥
            key = load_key()
            if not key:
                print("无法加载密钥文件，跳过加密配置读取")
                return None, None
                
            # 解密access_key_id
            encrypted_id = translator_config.get('access_key_id')
            access_key_id = decrypt_config_data(encrypted_id, key) if encrypted_id else None
            
            # 解密access_key_secret
            encrypted_secret = translator_config.get('access_key_secret')
            access_key_secret = decrypt_config_data(encrypted_secret, key) if encrypted_secret else None
            
            if access_key_id and access_key_secret:
                print("配置解密成功")
                return access_key_id, access_key_secret
        
        # 处理未加密的配置
        else:
            access_key_id = translator_config.get('access_key_id')
            access_key_secret = translator_config.get('access_key_secret')
            if access_key_id and access_key_secret:
                return access_key_id, access_key_secret
                
        print("配置中未找到有效的AccessKey信息")
    except json.JSONDecodeError:
        print("解析配置文件失败")
    except Exception as e:
        print(f"读取配置文件失败: {e}")
    
    return None, None

def translate_with_alicloud(source_text, source_language, target_language):
    """
    使用阿里云翻译服务进行文本翻译
    
    参数:
    - source_text: 待翻译的文本
    - source_language: 源语言代码 (如 'zh', 'en')
    - target_language: 目标语言代码 (如 'en', 'zh')
    
    返回:
    - (success, translated_text, error_message): 三元组，包含是否成功、翻译结果或错误信息
    """
    try:
        access_key_id, access_key_secret = get_access_key()
        
        if not access_key_id or not access_key_secret:
            return False, None, "未找到有效的阿里云AccessKey"
        
        # 构建请求参数
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        nonce = str(uuid.uuid4()).replace('-', '')
        
        # 添加FormatType参数，这是必需的
        params = {
            'Action': 'TranslateGeneral',
            'Format': 'JSON',
            'FormatType': 'text',  # 添加必需的FormatType参数
            'SourceLanguage': source_language,
            'TargetLanguage': target_language,
            'SourceText': source_text,
            'Scene': 'general',
            'AccessKeyId': access_key_id,
            'Timestamp': timestamp,
            'SignatureVersion': '1.0',
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureNonce': nonce,
            'Version': '2018-10-12'
        }
        
        # 按参数名排序
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        
        # 构建签名字符串
        canonicalized_query_string = '&'.join([
            f"{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(v)}"
            for k, v in sorted_params
        ])
        
        # 构建用于签名的字符串
        string_to_sign = f"GET&%2F&{urllib.parse.quote_plus(canonicalized_query_string)}"
        
        # 生成签名 - 使用正确的base64编码
        access_key_secret_with_amp = f"{access_key_secret}&"
        signature_bytes = hmac.new(
            access_key_secret_with_amp.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        signature = base64.b64encode(signature_bytes).decode('utf-8')
        
        # 构建最终URL
        url = f"https://mt.cn-hangzhou.aliyuncs.com/?{canonicalized_query_string}&Signature={urllib.parse.quote_plus(signature)}"
        
        # 发送请求
        response = requests.get(url, timeout=10)
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            if 'Data' in result and 'Translated' in result['Data']:
                return True, result['Data']['Translated'], None
            else:
                return False, None, f"翻译结果解析失败: {result}"
        else:
            return False, None, f"翻译失败: HTTP状态码 {response.status_code}, 响应: {response.text}"
    
    except Exception as e:
        return False, None, f"翻译过程中发生错误: {str(e)}"