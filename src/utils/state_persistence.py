from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import streamlit as st

# 仅保存这些键，避免把不可序列化对象写入
SERIALIZABLE_KEYS = [
    "equity_data",
    "current_step",
    "hidden_entities",
    "merged_entities",
    "mermaid_code",
    "json_data",
    "extracted_data",
    "translate_to_english",
    "use_real_api",
    "workspace_name",
]

AUTOSAVE_DIR = Path("user_data") / "autosave"
AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_sanitize(x) for x in obj]
    # 回退为字符串，避免类型不兼容
    return str(obj)


def make_snapshot() -> Dict[str, Any]:
    snap: Dict[str, Any] = {
        "schema_version": 1,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    for k in SERIALIZABLE_KEYS:
        if k in st.session_state:
            snap[k] = _sanitize(st.session_state[k])
    return snap


def apply_snapshot(snap: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(snap, dict):
        return False, "快照格式无效（非JSON对象）"
    # 未来可根据 schema_version 做迁移
    for k, v in snap.items():
        if k in ("schema_version", "saved_at"):
            continue
        st.session_state[k] = v
    return True, "已恢复编辑进度"


def autosave(snapshot: Dict[str, Any], workspace: str) -> Path:
    fname = AUTOSAVE_DIR / f"{workspace}.autosave.json"
    fname.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return fname


def find_autosave(workspace: str) -> Path | None:
    fname = AUTOSAVE_DIR / f"{workspace}.autosave.json"
    return fname if fname.exists() else None
