# Git中文乱码问题解决方案

## 问题描述
在Windows系统上使用Git时，中文提交信息显示为乱码，如：
```
feat: ååæµè¯•æä»lå¤¹å¹ä¼˜åŒ–HTMLå›¾è¡¨æ˜¾ç¤º
```

## 解决方案

### 1. 设置Git全局编码配置
```bash
git config --global core.quotepath false
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
```

### 2. 设置PowerShell编码
```bash
chcp 65001
```

### 3. 修复已存在的乱码提交
```bash
# 修改最新提交信息
git commit --amend -m "新的提交信息"

# 强制推送到远程仓库
git push origin master --force
```

### 4. 预防措施
- 使用英文提交信息避免编码问题
- 或者在提交前确保终端编码设置正确
- 使用Git GUI工具（如GitKraken、SourceTree）可以避免编码问题

## 当前状态
- ✅ Git编码配置已设置
- ✅ PowerShell编码已设置为UTF-8
- ✅ 最新提交信息已修复为英文
- ⏳ 等待网络恢复后推送修复后的提交

## 下次推送命令
```bash
git push origin master --force
```
