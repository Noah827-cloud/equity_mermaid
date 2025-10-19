from __future__ import annotations
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
AUTOSAVE_RETENTION = 10


def sanitize_workspace_name(workspace: str | None) -> str:
    if not workspace:
        return "workspace"
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", str(workspace)).strip()
    sanitized = sanitized.rstrip(" .")
    return sanitized or "workspace"


def _canonical_snapshot(snapshot: Dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True)


def _snapshot_hash_from_dict(snapshot: Dict[str, Any]) -> str:
    return hashlib.sha1(_canonical_snapshot(snapshot).encode("utf-8")).hexdigest()


def _snapshot_hash_from_path(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    try:
        return _snapshot_hash_from_dict(data)
    except Exception:
        return None


def _autosave_directory(workspace: str) -> Path:
    sanitized = sanitize_workspace_name(workspace)
    directory = AUTOSAVE_DIR / sanitized
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _sorted_autosave_files(directory: Path) -> List[Path]:
    files = list(directory.glob("*.json"))
    return sorted(files)


def _latest_autosave_file(directory: Path) -> Path | None:
    files = _sorted_autosave_files(directory)
    return files[-1] if files else None


def _ensure_snapshot_timestamp(snapshot: Dict[str, Any]) -> None:
    if "saved_at" not in snapshot:
        snapshot["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def autosave(snapshot: Dict[str, Any], workspace: str, keep_last: int = AUTOSAVE_RETENTION) -> Tuple[Path, bool]:
    _ensure_snapshot_timestamp(snapshot)
    directory = _autosave_directory(workspace)
    latest = _latest_autosave_file(directory)
    new_hash = _snapshot_hash_from_dict(snapshot)
    if latest:
        latest_hash = _snapshot_hash_from_path(latest)
        if latest_hash and latest_hash == new_hash:
            return latest, False
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    prefix = directory.name or sanitize_workspace_name(workspace) or "workspace"
    candidate = directory / f"{prefix}-{timestamp}.json"
    suffix = 1
    while candidate.exists():
        suffix += 1
        candidate = directory / f"{prefix}-{timestamp}-{suffix}.json"
    candidate.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _prune_autosaves(directory, keep_last)
    _update_latest_pointer(directory, candidate)
    return candidate, True


def find_autosave(workspace: str) -> Path | None:
    history = list_autosaves(workspace, limit=1)
    return history[0]["path"] if history else None


def list_autosaves(workspace: str, limit: int | None = None) -> List[Dict[str, Any]]:
    sanitized = sanitize_workspace_name(workspace)
    directory = AUTOSAVE_DIR / sanitized
    entries: List[Dict[str, Any]] = []
    if directory.exists():
        files = list(reversed(_sorted_autosave_files(directory)))
        for path in files:
            entries.append(_build_autosave_metadata(path))
            if limit and len(entries) >= limit:
                return entries[:limit]
    legacy = AUTOSAVE_DIR / f"{sanitized}.autosave.json"
    if legacy.exists():
        entries.append(_build_autosave_metadata(legacy))
    return entries[:limit] if limit else entries


def _prune_autosaves(directory: Path, keep_last: int) -> None:
    if keep_last <= 0:
        return
    files = _sorted_autosave_files(directory)
    if len(files) <= keep_last:
        return
    for path in files[:-keep_last]:
        try:
            path.unlink()
        except Exception:
            pass


def _update_latest_pointer(directory: Path, latest: Path) -> None:
    pointer = directory / "latest.json"
    try:
        pointer.write_text(
            json.dumps({"latest": latest.name}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _build_autosave_metadata(path: Path) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "path": path,
        "filename": path.name,
        "saved_at": None,
        "size": None,
        "created_ts": None,
    }
    try:
        stat = path.stat()
        metadata["size"] = stat.st_size
        metadata["created_ts"] = stat.st_mtime
    except OSError:
        pass
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            metadata["saved_at"] = data.get("saved_at")
    except Exception:
        pass
    return metadata
