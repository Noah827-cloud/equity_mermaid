#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare bootloader executable and runtime payload between builds.

If differences are detected, emit warnings so publishers know to
ship a full package instead of an incremental patch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Tuple


def iter_file_chunks(path: Path, chunk_size: int = 65536):
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            yield chunk


def file_signature(path: Path) -> Dict[str, object]:
    """
    Calculate file signature using size and SHA256 hash.
    
    Note: mtime is intentionally excluded as it can change due to:
    - File copy operations
    - Version control systems (git checkout)
    - Build tools
    This would cause false positives in drift detection.
    """
    sha256 = hashlib.sha256()
    for piece in iter_file_chunks(path):
        sha256.update(piece)
    stat = path.stat()
    return {
        "size": stat.st_size,
        "sha256": sha256.hexdigest(),
    }


def collect_runtime(dist_root: Path, runtime_dir_name: str) -> Dict[str, Dict[str, object]]:
    runtime_root = dist_root / runtime_dir_name
    payload: Dict[str, Dict[str, object]] = {}

    if not runtime_root.exists():
        return payload

    for path in runtime_root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(dist_root).as_posix()
            payload[rel] = file_signature(path)
    return payload


def diff_snapshots(prev: Dict[str, object], curr: Dict[str, object]) -> Tuple[bool, str]:
    """Return (has_changes, summary_message)."""
    messages = []
    changed = False

    prev_boot = prev.get("bootloader") if prev else None
    curr_boot = curr.get("bootloader")

    if prev_boot != curr_boot:
        changed = True
        messages.append(" - Bootloader executable differs (size/hash mismatch).")

    prev_runtime = prev.get("runtime") if prev else {}
    curr_runtime = curr.get("runtime", {})

    prev_keys = set(prev_runtime or {})
    curr_keys = set(curr_runtime or {})

    added = sorted(curr_keys - prev_keys)
    removed = sorted(prev_keys - curr_keys)
    common = prev_keys & curr_keys

    changed_files = [
        rel for rel in sorted(common)
        if prev_runtime[rel] != curr_runtime[rel]
    ]

    if added:
        changed = True
        messages.append(" - New runtime files: {}".format(", ".join(added[:5]) + (" ..." if len(added) > 5 else "")))
    if removed:
        changed = True
        messages.append(" - Removed runtime files: {}".format(", ".join(removed[:5]) + (" ..." if len(removed) > 5 else "")))
    if changed_files:
        changed = True
        messages.append(" - Updated runtime files: {}".format(", ".join(changed_files[:5]) + (" ..." if len(changed_files) > 5 else "")))

    summary = "\n".join(messages) if messages else ""
    return changed, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for runtime/bootloader drift.")
    parser.add_argument("--dist", required=True, help="Distribution root folder.")
    parser.add_argument("--exe", required=True, help="Bootloader executable filename.")
    parser.add_argument("--runtime-dir", default="runtime", help="Relative runtime directory name.")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot JSON file.")
    parser.add_argument("--flag", help="Optional flag file written when drift detected.")
    args = parser.parse_args()

    dist_root = Path(args.dist).resolve()
    snapshot_path = Path(args.snapshot).resolve()
    flag_path = Path(args.flag).resolve() if args.flag else None

    bootloader_path = dist_root / args.exe
    if not bootloader_path.exists():
        print(f"[WARN] Bootloader executable not found: {bootloader_path}")
        return 0

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    if flag_path:
        flag_path.parent.mkdir(parents=True, exist_ok=True)

    current_snapshot = {
        "bootloader": file_signature(bootloader_path),
        "runtime": collect_runtime(dist_root, args.runtime_dir),
    }

    if snapshot_path.exists():
        try:
            prev_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except Exception:
            prev_snapshot = None
    else:
        prev_snapshot = None

    if prev_snapshot is None:
        print("[INFO] No previous snapshot found; creating baseline.")
        has_changes = False
        summary = ""
        if flag_path and flag_path.exists():
            try:
                flag_path.unlink()
            except OSError:
                pass
    else:
        has_changes, summary = diff_snapshots(prev_snapshot or {}, current_snapshot)

        if has_changes:
            print("=" * 70)
            print("[WARN] Runtime or bootloader changed since last snapshot.")
            if summary:
                print(summary)
            print("       Please ship a FULL installer instead of an incremental patch.")
            print("=" * 70)
            if flag_path:
                flag_path.write_text("runtime_changed", encoding="utf-8")
        else:
            print("[OK] Runtime/bootloader unchanged since last snapshot.")
            if flag_path and flag_path.exists():
                try:
                    flag_path.unlink()
                except OSError:
                    pass

    snapshot_path.write_text(json.dumps(current_snapshot, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[INFO] Snapshot updated: {snapshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
