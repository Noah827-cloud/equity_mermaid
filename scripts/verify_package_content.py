#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的打包产物体检脚本，可用于经典包或增量包目录。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


def list_directory(path: Path) -> Iterable[str]:
    try:
        return sorted(os.listdir(path))
    except FileNotFoundError:
        return []


def check_dist_directory(dist_path: Path, exe_name: str) -> bool:
    print("=" * 70)
    print("打包产物体检")
    print("=" * 70)
    print()

    if not dist_path.exists():
        print(f"[ERROR] 找不到输出目录: {dist_path}")
        return False

    print(f"检查目录: {dist_path}")
    print()

    all_good = True

    # 1. 主程序
    print("① 主程序文件")
    print("-" * 50)
    exe_path = dist_path / exe_name
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"[OK] {exe_name} 存在，体积 {size_mb:.2f} MB")
    else:
        print(f"[WARN] {exe_name} 缺失")
        all_good = False
    print()

    # 2. 顶层目录
    print("② 顶层目录")
    print("-" * 50)
    subdirs = [item for item in list_directory(dist_path) if (dist_path / item).is_dir()]
    if subdirs:
        print(f"发现 {len(subdirs)} 个子目录：")
        for subdir in subdirs:
            print(f"  - {subdir}")
    else:
        print("未发现子目录（单文件模式?）")
    print()

    # 3. _internal（经典包）
    print("③ _internal 目录")
    print("-" * 50)
    internal_path = dist_path / "_internal"
    if internal_path.exists():
        file_count = 0
        dll_count = 0
        pyd_count = 0
        for root, _, files in os.walk(internal_path):
            for file in files:
                file_count += 1
                if file.lower().endswith(".dll"):
                    dll_count += 1
                elif file.lower().endswith(".pyd"):
                    pyd_count += 1
        print(f"[INFO] _internal 总文件数: {file_count} (DLL {dll_count}, PYD {pyd_count})")
    else:
        print("[INFO] 未发现 _internal (增量包正常现象)")
    print()

    # 4. 资源检查
    print("④ 关键资源文件")
    print("-" * 50)
    candidate_paths = [
        Path("app/src/assets/icons"),
        Path("src/assets/icons"),
        Path("_internal/src/assets/icons"),
        Path("assets/icons"),
    ]
    svg_found = False
    for rel_path in candidate_paths:
        full_path = dist_path / rel_path
        if full_path.exists():
            svg_files = [f for f in list_directory(full_path) if f.lower().endswith(".svg")]
            if svg_files:
                print(f"[OK] 在 {rel_path.as_posix()} 找到 {len(svg_files)} 个 SVG 资源")
                preview = svg_files[:3]
                for item in preview:
                    print(f"     - {item}")
                if len(svg_files) > 3:
                    print(f"     ... 其余 {len(svg_files) - 3} 项略")
                svg_found = True
                break
    if not svg_found:
        print("[WARN] 未找到 SVG 资源，请确认图标是否被正确打包")
        all_good = False
    print()

    # 5. 配置文件
    print("⑤ 配置文件")
    print("-" * 50)
    config_locations = [dist_path, dist_path / "app"]
    for cfg in ("config.json", "config.key", "README.md"):
        found = False
        for location in config_locations:
            if (location / cfg).exists():
                print(f"[OK] {cfg} 已包含 ({location.relative_to(dist_path) if location != dist_path else '.'})")
                found = True
                break
        if not found:
            print(f"[WARN] {cfg} 缺失")
            all_good = False
    print()

    # 6. Python 动态内容
    print("⑥ Python 相关文件")
    print("-" * 50)
    pyz_files = []
    pkg_files = []
    for root, _, files in os.walk(dist_path):
        for file in files:
            rel = Path(root, file).relative_to(dist_path).as_posix()
            if file.lower().endswith(".pyz"):
                pyz_files.append(rel)
            elif file.lower().endswith(".pkg"):
                pkg_files.append(rel)
    if pyz_files:
        print(f"[INFO] 发现 {len(pyz_files)} 个 PYZ 包：")
        for pyz in pyz_files:
            print(f"     - {pyz}")
    if pkg_files:
        print(f"[INFO] 发现 {len(pkg_files)} 个 PKG 包：")
        for pkg in pkg_files:
            print(f"     - {pkg}")
    if not pyz_files and not pkg_files:
        print("[INFO] 未发现 .pyz/.pkg，可能已启用 noarchive 模式")
    print()

    print("=" * 70)
    if all_good:
        print("[OK] 体检通过，可进入后续测试。")
    else:
        print("[WARN] 体检发现问题，请先修复后再发版。")
    print("=" * 70)
    print()

    return all_good


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 PyInstaller 输出目录内容。")
    parser.add_argument("dist_path", nargs="?", default="dist/equity_mermaid_tool_fixed", help="待检查的目录路径")
    parser.add_argument("--exe", default="equity_mermaid_tool.exe", help="主程序文件名")
    args = parser.parse_args()

    success = check_dist_directory(Path(args.dist_path), args.exe)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
