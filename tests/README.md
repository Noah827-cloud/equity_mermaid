# 测试文件夹说明

本文件夹用于存放股权结构图生成功能的测试脚本和测试数据。所有测试相关的内容都将自动归纳到此处，方便管理和维护。

## 文件夹结构

- `test_new_data.py`: 使用最新JSON数据测试Mermaid图表生成功能
- `test_mermaid_generation.py`: 基本的Mermaid图表生成测试
- `test_bracket_issue.py`: 测试括号转义问题
- `test_translation.py`: 翻译功能测试
- `test_updated_translation.py`: 更新后的翻译功能测试
- `simple_translation_test.py`: 简单翻译测试
- `*.json`: 测试结果和数据文件
- `*.txt`: Mermaid图表输出文件

## 如何运行测试

1. 确保已安装所有依赖（参考项目根目录的requirements.txt）
2. 在项目根目录下运行：

```bash
# 运行特定测试
python tests/test_new_data.py

# 或运行所有测试（如果有测试框架）
pytest tests/
```

## 测试结果

测试生成的Mermaid图表代码将保存在对应的输出文件中（如`test_mermaid_output_new.txt`）。

## 注意事项

- 新增测试应遵循现有测试的命名规范和结构
- 测试数据应与测试脚本一起保存在此文件夹中
- 确保测试脚本能够正确引用项目的源代码模块