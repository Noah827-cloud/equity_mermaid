from typing import Tuple

from src.utils.translation_usage import (
    get_cached,
    set_cached,
    check_and_consume,
    refund,
)
from src.utils.alicloud_translator import translate_with_alicloud


class QuotaExceededError(Exception):
    pass


def _translate_single_chunk(text: str, src: str, tgt: str) -> Tuple[bool, str, str]:
    return translate_with_alicloud(text, src, tgt)


def translate_text(text: str, src: str, tgt: str, scene: str = "general") -> str:
    safe_text = text or ""
    if not safe_text:
        return safe_text

    cached = get_cached(safe_text, src, tgt)
    if cached is not None:
        return cached

    char_count = len(safe_text)
    allowed, info = check_and_consume(char_count)
    if not allowed:
        raise QuotaExceededError(
            f"monthly quota exceeded: used={info.get('used')}, limit={info.get('limit')}"
        )

    max_len = 5000
    chunks = [safe_text[i : i + max_len] for i in range(0, len(safe_text), max_len)]
    results = []
    try:
        for chunk in chunks:
            ok, translated, err = _translate_single_chunk(chunk, src, tgt)
            if not ok or not translated:
                raise RuntimeError(err or "translate failed")
            results.append(translated)
        final_text = "".join(results)
        set_cached(safe_text, src, tgt, final_text)
        return final_text
    except Exception:
        refund(char_count)
        raise
