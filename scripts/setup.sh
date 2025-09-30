#!/bin/bash

# 股权结构可视化工具 - Streamlit Cloud部署脚本

# 输出部署信息
echo "开始部署股权结构可视化工具..."

# 检查Python版本
echo "Python版本信息:"
python --version

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装项目依赖..."
pip install -r requirements.txt

# 验证安装
echo "验证依赖安装..."
pip list

# 设置环境变量（可选，实际部署时应在Streamlit Cloud Secrets中配置）
# 注意：不要在脚本中硬编码敏感信息

# 显示完成消息
echo "部署准备完成！"
echo "Streamlit应用将自动启动"