import os
import sys
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

# 检查是否在PyInstaller打包环境中
IS_PYINSTALLER = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# 尝试将标准输出/错误设置为utf-8，避免Windows控制台编码问题
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# 安全日志输出，避免因非ASCII字符导致的编码错误
def _safe_log(message):
    try:
        print(message)
    except Exception:
        try:
            # 尽量以UTF-8输出，不行则忽略无法编码的字符
            text = str(message)
            sys.stdout.write(text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore') + "\n")
        except Exception:
            pass

# 获取应用根目录
def get_app_root():
    """获取应用根目录，兼容开发环境和PyInstaller打包环境"""
    if IS_PYINSTALLER:
        # PyInstaller打包环境
        return sys._MEIPASS
    else:
        # 开发环境
        return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def load_key():
    """Locate and return the Fernet key used for encrypted configuration."""
    try:
        if IS_STREAMLIT_CLOUD:
            _safe_log("Streamlit Cloud runtime detected; skipping local key loading.")
            return None

        app_root = get_app_root()
        candidate_paths = [
            os.path.join(app_root, "config.key"),
            os.path.join(app_root, "src", "config", "config.key"),
            os.path.join(app_root, "app", "config.key"),
            os.path.join(app_root, "app", "src", "config", "config.key"),
            os.path.join(os.getcwd(), "config.key"),
            os.path.join(os.getcwd(), "src", "config", "config.key"),
            os.path.join(os.getcwd(), "app", "config.key"),
            os.path.join(os.getcwd(), "app", "src", "config", "config.key"),
        ]
        key_file = next((path for path in candidate_paths if os.path.exists(path)), None)
        if not key_file:
            _safe_log("config.key not found in candidate paths: " + ", ".join(candidate_paths))
            return None

        with open(key_file, "rb") as f:
            return f.read()
    except Exception as e:
        _safe_log(f"Failed to load config.key: {e}")
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
        _safe_log(f"解密数据失败: {e}")
        return None

def get_access_key():
    """Resolve Alibaba Cloud translator AccessKey from env vars or config files."""
    access_key_id = os.environ.get("ALICLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALICLOUD_ACCESS_KEY_SECRET")

    if access_key_id and access_key_secret:
        return access_key_id, access_key_secret

    if IS_STREAMLIT_CLOUD:
        _safe_log("Streamlit Cloud detected; please configure AccessKey via environment variables.")
        return None, None

    try:
        app_root = get_app_root()
        config_candidates = [
            os.path.join(app_root, "config.json"),
            os.path.join(app_root, "app", "config.json"),
            os.path.join(app_root, "src", "config", "config.json"),
            os.path.join(app_root, "app", "src", "config", "config.json"),
            os.path.join(os.getcwd(), "config.json"),
            os.path.join(os.getcwd(), "app", "config.json"),
            os.path.join(os.getcwd(), "src", "config", "config.json"),
            os.path.join(os.getcwd(), "app", "src", "config", "config.json"),
        ]
        config_path = next((path for path in config_candidates if os.path.exists(path)), None)

        if not config_path:
            _safe_log("config.json not found in candidate paths: " + ", ".join(config_candidates))
            return None, None

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        translator_config = config.get("alicloud_translator")
        if not translator_config:
            _safe_log("Missing alicloud_translator section in config.json")
            return None, None

        encrypted_config = translator_config.get("__encrypted__", False) or config.get("__encrypted__", False)

        if encrypted_config:
            key = load_key()
            if not key:
                _safe_log("Encrypted config detected but config.key not found.")
                return None, None

            encrypted_id = translator_config.get("access_key_id")
            encrypted_secret = translator_config.get("access_key_secret")
            access_key_id = decrypt_config_data(encrypted_id, key) if encrypted_id else None
            access_key_secret = decrypt_config_data(encrypted_secret, key) if encrypted_secret else None
        else:
            access_key_id = translator_config.get("access_key_id")
            access_key_secret = translator_config.get("access_key_secret")

        if access_key_id and access_key_secret:
            return access_key_id, access_key_secret

        _safe_log("config.json does not contain usable AccessKey values")
    except json.JSONDecodeError:
        _safe_log("Failed to parse config.json")
    except Exception as exc:
        _safe_log(f"Unexpected error while resolving AccessKey: {exc}")

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
        
        # 构建签名字符串 - 确保参数值已正确编码（阿里云API要求的精确编码方式）
        canonicalized_query_string = '&'.join([
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
            for k, v in sorted_params
        ])
        
        # 构建用于签名的字符串 - 严格按照阿里云文档要求
        string_to_sign = f"GET&{urllib.parse.quote('/', safe='')}&{urllib.parse.quote(canonicalized_query_string, safe='')}"
        
        # 生成签名 - 确保正确处理密钥和编码
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

