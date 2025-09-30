# Streamlit Community Cloud部署指南

## 前置条件

1. 拥有GitHub账号
2. 应用代码已经在本地完成开发和测试
3. 已更新`requirements.txt`，仅包含必要的生产依赖
4. 已添加环境变量支持和错误处理机制

## 步骤1：将代码提交到GitHub

### 初始化Git仓库（如果尚未初始化）

```bash
# 进入项目目录
cd c:\Users\z001syzk\Downloads\equity_mermaid

# 初始化Git仓库
git init

# 确保.gitignore文件已正确配置
git add .gitignore

# 提交.gitignore
git commit -m "Add .gitignore"
```

### 添加并提交所有代码

```bash
# 添加所有文件
git add .

# 提交更改
git commit -m "准备部署到Streamlit Cloud"
```

### 创建GitHub仓库并推送到远程

1. 在GitHub上创建一个新的仓库（https://github.com/new）
2. 按照GitHub的指引将本地代码推送到远程仓库：

```bash
# 添加远程仓库
git remote add origin https://github.com/你的用户名/equity_mermaid.git

# 推送代码到远程仓库
git push -u origin master
```

## 步骤2：部署到Streamlit Community Cloud

1. 访问 [Streamlit Community Cloud](https://share.streamlit.io/)
2. 使用你的GitHub账号登录
3. 点击右上角的 "New app" 按钮

### 配置应用部署参数

- **Repository**: 选择你的GitHub仓库（例如：`你的用户名/equity_mermaid`）
- **Branch**: 选择 `master` 或 `main` 分支
- **Main file path**: 输入 `manual_equity_editor.py`

### 设置环境变量（可选）

如果你的应用需要API密钥或其他敏感信息，可以在部署后进行配置：

1. 部署完成后，点击应用右上角的三个点图标
2. 选择 "Settings"
3. 在 "Secrets" 部分添加环境变量：
   - 变量名：`ALICLOUD_ACCESS_KEY_ID`
   - 变量值：你的阿里云Access Key ID
   - 变量名：`ALICLOUD_ACCESS_KEY_SECRET`
   - 变量值：你的阿里云Access Key Secret

## 步骤3：验证部署

部署完成后，Streamlit Community Cloud会提供一个URL（通常格式为：`https://你的用户名-equity_mermaid-streamlit-app-name.streamlit.app`）。

1. 访问提供的URL
2. 验证应用是否正常运行
3. 测试主要功能是否正常工作

## 常见问题排查

### 应用无法启动

1. 检查应用的日志（在Streamlit Cloud的应用页面点击 "Manage app" > "Logs"）
2. 确认`requirements.txt`中的所有依赖都已正确安装
3. 检查代码中是否有硬编码的本地路径

### 功能缺失或错误

1. 检查是否缺少必要的环境变量
2. 确认所有依赖版本兼容
3. 查看应用日志中的错误信息

### 性能问题

1. 优化代码，减少不必要的计算
2. 考虑缓存频繁使用的数据
3. 确保API调用设置了合理的超时时间

## 维护与更新

更新应用只需将新代码推送到GitHub仓库：

```bash
# 提交本地更改
git commit -am "更新应用功能"

# 推送到远程仓库
git push
```

Streamlit Cloud会自动检测更改并重新部署应用。