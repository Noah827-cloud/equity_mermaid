# 🔐 安全配置指南

## ⚠️ 重要安全提醒

**永远不要将明文凭证文件提交到版本控制系统！**

## 📁 配置文件说明

### ✅ 安全的配置文件
- `config.json` - **加密的配置文件**（包含 `"__encrypted__": true`）
- `src/config/config.json.template` - 配置模板文件
- `src/config/config.key` - 加密密钥文件
- `src/config/mcp_config.json` - MCP配置（仅包含路径信息）

### ❌ 禁止的文件
- `config.decrypted.json` - **明文凭证文件**（已删除）
- `config.decrypted.py` - **明文凭证文件**
- `*.decrypted.*` - 任何解密后的配置文件

## 🔒 加密配置系统

项目使用 `src/utils/config_encryptor.py` 进行配置加密：

### 加密流程
1. 使用 `config.json.template` 创建明文配置
2. 运行加密工具将敏感信息加密
3. 生成 `config.json`（加密版本）
4. **删除明文配置文件**

### 使用示例
```bash
# 加密配置文件
python src/utils/config_encryptor.py encrypt config.template.json

# 解密配置文件（仅用于调试）
python src/utils/config_encryptor.py decrypt config.json
```

## 🛡️ 安全最佳实践

### 1. 密钥管理
- ✅ `config.key` 文件已添加到 `.gitignore`
- ✅ 密钥文件不要提交到版本控制
- ✅ 定期轮换密钥

### 2. 环境变量
- 考虑使用环境变量替代配置文件
- 在部署时动态注入敏感信息

### 3. 访问控制
- 限制对配置文件的访问权限
- 使用最小权限原则

## 🚨 应急响应

如果发现凭证泄露：

1. **立即轮换密钥**
   - 登录阿里云控制台
   - 生成新的 AccessKey
   - 更新配置文件

2. **清理泄露痕迹**
   - 删除所有明文配置文件
   - 检查版本历史
   - 强制推送清理提交

3. **通知相关人员**
   - 告知团队成员
   - 检查是否有异常使用

## 📋 检查清单

- [ ] 没有明文凭证文件
- [ ] `.gitignore` 包含所有敏感文件模式
- [ ] 加密配置系统正常工作
- [ ] 密钥文件安全存储
- [ ] 定期轮换凭证

## 🔗 相关文件

- `src/utils/config_encryptor.py` - 加密工具
- `src/config/config.json.template` - 配置模板
- `.gitignore` - 忽略规则
- `README.md` - 项目文档
