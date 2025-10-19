import os
import json
import hashlib
from datetime import datetime
from typing import Optional, Tuple, Dict

import portalocker  # type: ignore[reportMissingImports]


USER_DATA_DIR = os.path.join(os.getcwd(), 'user_data')
CACHE_PATH = os.path.join(USER_DATA_DIR, 'translation_cache.json')
USAGE_PATH = os.path.join(USER_DATA_DIR, 'translation_usage.json')


def _ensure_dirs() -> None:
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR, exist_ok=True)


def normalize_lang(code: str) -> str:
    if not code:
        return ''
    return code.strip().lower().replace('_', '-')


def build_cache_key(text: str, src: str, tgt: str) -> str:
    normalized = f"{normalize_lang(src)}::{normalize_lang(tgt)}::{text.strip()}"
    return hashlib.sha1(normalized.encode('utf-8')).hexdigest()


def _locked_load(path: str) -> dict:
    _ensure_dirs()
    if not os.path.exists(path):
        return {}
    try:
        with portalocker.Lock(path, timeout=5, flags=portalocker.LOCK_SH) as fh:
            try:
                fh.seek(0)
                return json.load(fh)
            except json.JSONDecodeError:
                return {}
    except (LOCK_EXCEPTION, OSError):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}


def _locked_save(path: str, data: dict) -> None:
    _ensure_dirs()
    with portalocker.Lock(path, timeout=5, flags=portalocker.LOCK_EX, mode='a+') as fh:
        fh.seek(0)
        fh.truncate()
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def get_cached(text: str, src: str, tgt: str) -> Optional[str]:
    key = build_cache_key(text, src, tgt)
    cache = _locked_load(CACHE_PATH)
    item = cache.get(key)
    if not item:
        return None
    # 更新命中次数但不强制写盘以减少IO；在写入时会覆盖
    try:
        item['hits'] = int(item.get('hits', 0)) + 1
        cache[key] = item
        _locked_save(CACHE_PATH, cache)
    except Exception:
        pass
    return item.get('translated')


def set_cached(text: str, src: str, tgt: str, translated: str) -> None:
    key = build_cache_key(text, src, tgt)
    cache = _locked_load(CACHE_PATH)
    cache[key] = {
        'src': normalize_lang(src),
        'tgt': normalize_lang(tgt),
        'text_len': len(text),
        'translated': translated,
        'ts': datetime.utcnow().isoformat() + 'Z',
        'hits': int(cache.get(key, {}).get('hits', 0)),
    }
    _locked_save(CACHE_PATH, cache)


def get_month_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.utcnow()
    return d.strftime('%Y-%m')


def ensure_month_record(limit_default: int = 50000) -> Dict:
    usage = _locked_load(USAGE_PATH)
    month = get_month_key()
    if usage.get('month') != month:
        usage = {
            'month': month,
            'used': 0,
            'limit': int(limit_default),
            'history': [],
        }
        _locked_save(USAGE_PATH, usage)
    return usage


def get_monthly_usage() -> Dict:
    usage = ensure_month_record()
    return {'month': usage.get('month'), 'used': int(usage.get('used', 0)), 'limit': int(usage.get('limit', 0))}


def check_and_consume(chars: int) -> Tuple[bool, Dict]:
    if chars < 0:
        chars = 0
    usage = ensure_month_record()
    remaining = int(usage['limit']) - int(usage['used'])
    if remaining < chars:
        return False, {'used': int(usage['used']), 'limit': int(usage['limit']), 'remaining': remaining}
    usage['used'] = int(usage['used']) + int(chars)
    _locked_save(USAGE_PATH, usage)
    return True, {'used': int(usage['used']), 'limit': int(usage['limit']), 'remaining': int(usage['limit']) - int(usage['used'])}


def refund(chars: int) -> None:
    if chars <= 0:
        return
    usage = ensure_month_record()
    usage['used'] = max(0, int(usage['used']) - int(chars))
    _locked_save(USAGE_PATH, usage)


def set_month_limit(new_limit: int, actor: str = 'admin', reason: str = '') -> Dict:
    usage = ensure_month_record()
    old = int(usage['limit'])
    usage['limit'] = max(0, int(new_limit))
    usage.setdefault('history', []).append({
        'ts': datetime.utcnow().isoformat() + 'Z',
        'actor': actor,
        'delta': int(usage['limit']) - old,
        'reason': reason or 'manual adjust',
    })
    _locked_save(USAGE_PATH, usage)
    return {'old': old, 'new': int(usage['limit'])}


def get_admin_password() -> str:
    # 环境变量优先
    env_pwd = os.environ.get('TRANSLATION_ADMIN_PASSWORD')
    if env_pwd:
        return env_pwd
    # config.json 次之
    try:
        app_config_path = os.path.join(os.getcwd(), 'config.json')
        if os.path.exists(app_config_path):
            with open(app_config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                pwd = cfg.get('translation_admin_password')
                if isinstance(pwd, str) and pwd:
                    return pwd
    except Exception:
        pass
    # 默认密码
    return 'Noah2025@Ali'


LOCK_EXCEPTION = getattr(portalocker, "LockException", Exception)
