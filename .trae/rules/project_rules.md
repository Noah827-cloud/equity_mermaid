# user_rules.yaml
mcp:
  context_provider: "context7"
  max_context_files: 8
  include_patterns:
    - "**/*.py"
    - "**/requirements.txt"
    - "**/README.md"
  exclude_patterns:
    - "**/__pycache__/**"
    - "**/.git/**"
    - "**/node_modules/**"
  auto_infer_entrypoint: true

sequence_thinking:
  enabled: true
  min_steps: 3
  max_steps: 7
  enforce_step_labels: true
  step_format:
    - "🎯 Goal"
    - "🔍 Analyze Context"
    - "🧩 Plan"
    - "⚙️ Execute"
    - "✅ Verify"
    - "📝 Document"

response_constraints:
  always_cite_context: true
  never_assume_missing_info: true
  reject_ambiguous_requests: true
  output_format: "code_block_with_explanation"
  code_style: "pep8"

safety:
  allow_file_write: false
  allow_network_access: false
  require_user_confirmation_for:
    - destructive_operations
    - external_api_calls
在记录readme文件时要用调用系统的最新时间来更新，格式为YYYY-MM-DD
# MCP Interactive Feedback 规则
注意在任务完成前根据mcp-feedback-enhanced工具的要求进行工具调用，不是运行一次，每次调用都要根据工具的要求进行调用，直到任务完成。特别是出现问题，需要根据工具的反馈进行修正。
测试程序都要放到test目录下，每个测试程序都要以test_开头，例如test_manual_equity_editor.py
测试程序中要包含测试用例，每个测试用例都要以test_开头，例如test_manual_equity_editor.py中的test_manual_equity_editor()函数
测试程序产生的测试结果放在test result 目录下
明确区分`scripts`和`utils`目录用途：`scripts`存放独立可执行脚本，`utils`存放被导入的工具类和函数，所以涉及生成新的程序时要按照这个规则
