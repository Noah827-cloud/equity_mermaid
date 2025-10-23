#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复protobuf和PyArrow DLL加载问题的脚本
"""

import os
import sys
import shutil
import stat

def fix_protobuf_issue():
    """修复protobuf和PyArrow DLL加载问题"""
    print("=" * 60)
    print("修复protobuf和PyArrow DLL加载问题")
    print("=" * 60)
    
    # 检查是否存在打包后的exe文件
    exe_path = "dist/equity_mermaid_tool_fixed/equity_mermaid_tool.exe"
    if not os.path.exists(exe_path):
        print("❌ 未找到打包后的exe文件，请先运行打包脚本")
        return False
    
    print("✅ 找到打包后的exe文件")
    
    # 检查Anaconda环境中的protobuf和PyArrow DLL文件
    anaconda_lib_bin = r'C:\Users\z001syzk\AppData\Local\anaconda3\Library\bin'
    required_dlls = [
        'libprotobuf.dll',
        'abseil_dll.dll',
        'arrow.dll',
        'arrow_flight.dll',
        'arrow_dataset.dll',
        'arrow_acero.dll',
        'arrow_substrait.dll',
        'parquet.dll'
    ]
    
    missing_dlls = []
    for dll in required_dlls:
        dll_path = os.path.join(anaconda_lib_bin, dll)
        if os.path.exists(dll_path):
            print(f"✅ 找到 {dll}")
        else:
            print(f"❌ 未找到 {dll}")
            missing_dlls.append(dll)
    
    if missing_dlls:
        print(f"\n⚠️ 缺少以下DLL文件: {', '.join(missing_dlls)}")
        print("请确保protobuf已正确安装")
        return False
    
    # 复制DLL文件到打包目录
    dist_dir = "dist/equity_mermaid_tool_fixed"
    internal_dir = os.path.join(dist_dir, "_internal")

    if not os.path.isdir(internal_dir):
        print("❌ 未找到 _internal 目录，无法复制DLL文件")
        return False

    target_dir = internal_dir
    print(f"\n📁 复制DLL文件到: {target_dir}")
    
    for dll in required_dlls:
        src_path = os.path.join(anaconda_lib_bin, dll)
        dst_path = os.path.join(target_dir, dll)
        legacy_path = os.path.join(dist_dir, dll)

        if os.path.exists(legacy_path) and os.path.abspath(legacy_path) != os.path.abspath(dst_path):
            try:
                os.replace(legacy_path, dst_path)
                print(f"🧹 已移动根目录中的旧版 {dll} 至 _internal")
            except PermissionError:
                try:
                    os.chmod(legacy_path, stat.S_IWRITE)
                    os.replace(legacy_path, dst_path)
                    print(f"🧹 已移动根目录中的旧版 {dll} 至 _internal")
                except Exception as move_err:
                    print(f"⚠️ 无法移动根目录中的 {dll}: {move_err}")
            except Exception as move_err:
                print(f"⚠️ 无法移动根目录中的 {dll}: {move_err}")
        
        need_copy = True
        if os.path.exists(dst_path):
            try:
                if os.path.getsize(dst_path) == os.path.getsize(src_path):
                    need_copy = False
                    print(f"ℹ️ {dll} 已存在且大小一致，跳过复制")
            except OSError:
                pass

        if need_copy:
            try:
                shutil.copy2(src_path, dst_path)
                print(f"✅ 已复制 {dll}")
            except Exception as e:
                print(f"❌ 复制 {dll} 失败: {e}")
                return False
    
    print("\n🎉 protobuf和PyArrow DLL文件修复完成！")
    print("\n现在可以尝试运行exe文件:")
    print(f"   {exe_path}")
    
    return True

if __name__ == "__main__":
    success = fix_protobuf_issue()
    if not success:
        sys.exit(1)
