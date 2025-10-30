#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动同步 src/utils 模块到 equity_mermaid.spec 文件
防止打包时遗漏新增的工具模块
"""

import os
import sys
import re


def get_utils_modules():
    """获取 src/utils 目录下所有的 Python 模块"""
    utils_dir = "src/utils"
    if not os.path.exists(utils_dir):
        print(f"❌ 错误: {utils_dir} 目录不存在")
        return []
    
    modules = []
    for file in sorted(os.listdir(utils_dir)):
        if file.endswith('.py') and file != '__init__.py':
            modules.append(file)
    
    return modules


def check_spec_file():
    """检查 equity_mermaid.spec 文件中的工具模块配置"""
    spec_file = "equity_mermaid.spec"
    if not os.path.exists(spec_file):
        print(f"❌ 错误: {spec_file} 文件不存在")
        return False
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        spec_content = f.read()
    
    # 获取所有实际存在的工具模块
    actual_modules = get_utils_modules()
    
    # 检查 project_datas 部分
    print("=" * 70)
    print("检查 equity_mermaid.spec 文件中的工具模块配置")
    print("=" * 70)
    print()
    
    print(f"📁 在 src/utils 目录中发现 {len(actual_modules)} 个模块：")
    for module in actual_modules:
        print(f"  - {module}")
    print()
    
    # 检查 project_datas 中缺失的模块
    missing_in_datas = []
    for module in actual_modules:
        pattern = f"\\('src/utils/{module}', 'src/utils'\\)"
        if not re.search(pattern, spec_content):
            missing_in_datas.append(module)
    
    # 检查 hiddenimports 中缺失的模块
    missing_in_imports = []
    for module in actual_modules:
        module_name = module.replace('.py', '')
        pattern = f"'src\\.utils\\.{module_name}'"
        if not re.search(pattern, spec_content):
            missing_in_imports.append(module)
    
    # 报告结果
    if not missing_in_datas and not missing_in_imports:
        print("✅ 所有工具模块都已在 spec 文件中正确配置！")
        return True
    
    all_good = True
    
    if missing_in_datas:
        print("⚠️  警告: 以下模块未在 project_datas 中声明：")
        print()
        print("请在 equity_mermaid.spec 的 project_datas 部分添加：")
        print("-" * 70)
        for module in missing_in_datas:
            module_name = module.replace('.py', '')
            print(f"    ('src/utils/{module}', 'src/utils'),  # 添加{module_name}工具")
        print("-" * 70)
        print()
        all_good = False
    
    if missing_in_imports:
        print("⚠️  警告: 以下模块未在 hiddenimports 中声明：")
        print()
        print("请在 equity_mermaid.spec 的 hiddenimports 部分添加：")
        print("-" * 70)
        for module in missing_in_imports:
            module_name = module.replace('.py', '')
            print(f"    'src.utils.{module_name}',")
        print("-" * 70)
        print()
        all_good = False
    
    return all_good


def auto_update_spec():
    """自动更新 equity_mermaid.spec 文件（如果用户确认）"""
    spec_file = "equity_mermaid.spec"
    
    if not os.path.exists(spec_file):
        print(f"❌ 错误: {spec_file} 文件不存在")
        return False
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        spec_content = f.read()
    
    actual_modules = get_utils_modules()
    
    # 收集需要添加的内容
    missing_in_datas = []
    missing_in_imports = []
    
    for module in actual_modules:
        # 检查 project_datas
        pattern = f"\\('src/utils/{module}', 'src/utils'\\)"
        if not re.search(pattern, spec_content):
            missing_in_datas.append(module)
        
        # 检查 hiddenimports
        module_name = module.replace('.py', '')
        pattern = f"'src\\.utils\\.{module_name}'"
        if not re.search(pattern, spec_content):
            missing_in_imports.append(module)
    
    if not missing_in_datas and not missing_in_imports:
        print("✅ 所有模块已配置，无需更新。")
        return True
    
    print()
    print("🔧 准备自动更新 equity_mermaid.spec 文件...")
    print()
    
    # 询问用户确认
    response = input("是否继续？(y/n): ").strip().lower()
    if response != 'y':
        print("❌ 用户取消操作")
        return False
    
    modified = False
    
    # 更新 project_datas
    if missing_in_datas:
        # 查找插入位置（在最后一个 src/utils 条目之后）
        last_utils_match = None
        for match in re.finditer(r"    \('src/utils/[^']+', 'src/utils'\),.*\n", spec_content):
            last_utils_match = match
        
        if last_utils_match:
            insert_pos = last_utils_match.end()
            new_lines = []
            for module in missing_in_datas:
                module_name = module.replace('.py', '')
                new_lines.append(f"    ('src/utils/{module}', 'src/utils'),  # 添加{module_name}工具\n")
            
            spec_content = spec_content[:insert_pos] + ''.join(new_lines) + spec_content[insert_pos:]
            modified = True
            print(f"✅ 已在 project_datas 中添加 {len(missing_in_datas)} 个模块")
    
    # 更新 hiddenimports
    if missing_in_imports:
        # 查找插入位置（在最后一个 src.utils 条目之后）
        last_import_match = None
        for match in re.finditer(r"    'src\.utils\.[^']+',\n", spec_content):
            last_import_match = match
        
        if last_import_match:
            insert_pos = last_import_match.end()
            new_lines = []
            for module in missing_in_imports:
                module_name = module.replace('.py', '')
                new_lines.append(f"    'src.utils.{module_name}',\n")
            
            spec_content = spec_content[:insert_pos] + ''.join(new_lines) + spec_content[insert_pos:]
            modified = True
            print(f"✅ 已在 hiddenimports 中添加 {len(missing_in_imports)} 个模块")
    
    if modified:
        # 备份原文件
        backup_file = spec_file + '.bak'
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(open(spec_file, 'r', encoding='utf-8').read())
        print(f"📝 已备份原文件到: {backup_file}")
        
        # 写入更新后的内容
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        print(f"✅ 已更新 {spec_file}")
        return True
    
    return False


def main():
    """主函数"""
    print()
    print("=" * 70)
    print("工具模块同步脚本")
    print("=" * 70)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        # 自动更新模式
        success = auto_update_spec()
        sys.exit(0 if success else 1)
    else:
        # 检查模式
        success = check_spec_file()
        
        if not success:
            print()
            print("💡 提示:")
            print("   1. 手动按照上述提示更新 equity_mermaid.spec")
            print("   2. 或运行 'python scripts/sync_utils_to_spec.py --auto' 自动更新")
            print()
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

