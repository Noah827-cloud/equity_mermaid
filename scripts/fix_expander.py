# 临时修复脚本 - 简化版本
try:
    # 读取文件内容
    with open('c:/Users/z001syzk/Downloads/equity_mermaid/src/main/manual_equity_editor.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找问题代码块的位置
    start_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if '# 创建自定义HTML的展开面板' in line:
            start_idx = i
        elif '</script>' in line and start_idx != -1:
            end_idx = i + 1  # 包含script标签行
            break
    
    if start_idx == -1 or end_idx == -1:
        print('未找到需要修复的代码块')
        exit(1)
    
    # 创建新的代码块内容
    new_lines = []
    # 添加start_idx之前的行
    new_lines.extend(lines[:start_idx+1])
    # 添加修复后的代码
    new_lines.extend([
        '    # 修复语法错误: 使用变量存储HTML\n',
        "    expander_html = '''\n",
        '    <div class="custom-expander" style="margin-top: 1rem; border: 1px solid #e2e8f0; border-radius: 0.25rem; overflow: hidden;">\n',
        '        <div class="expander-header" style="background-color: #2b6cb0; color: white; padding: 0.5rem 1rem; cursor: pointer; display: flex; align-items: center;">\n',
        "        ''' + info_icon_html + ''' 使用说明\n",
        '        <span class="expander-icon" style="margin-left: auto;">&#9660;</span>\n',
        '        </div>\n',
        '        <div class="expander-content" style="padding: 1rem; background-color: white; border-top: 1px solid #e2e8f0; display: none;">\n',
        '            <h3>手动编辑模式操作步骤</h3>\n',
        '            <ol>\n',
        '                <li><strong>设置核心公司</strong>: 输入公司名称</li>\n',
        '                <li><strong>添加股权关系</strong>:\n',
        '                    <ul>\n',
        '                        <li>添加股东及持股比例</li>\n',
        '                        <li>添加子公司及持股比例</li>\n',
        '                        <li>设置实际控制关系</li>\n',
        '                    </ul>\n',
        '                </li>\n',
        '            </ol>\n',
        '        </div>\n',
        '    </div>\n',
        "    '''\n",
        '    st.markdown(expander_html, unsafe_allow_html=True)\n'
    ])
    # 添加end_idx之后的行
    new_lines.extend(lines[end_idx:])
    
    # 写回文件
    with open('c:/Users/z001syzk/Downloads/equity_mermaid/src/main/manual_equity_editor.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print('修复成功！')
except Exception as e:
    print(f'修复失败: {e}')