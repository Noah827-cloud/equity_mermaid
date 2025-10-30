# PyInstaller 打包模式对比

## 📦 您的问题

> 打包好的 exe 有 400M，还有 _internal 的 400M，运行的时候需不需要 _internal 文件夹？

## ✅ 答案：**必须需要！**

您当前使用的是 **onedir 模式**，exe 和 _internal 必须一起使用。

---

## 两种打包模式对比

### 模式 1：onedir（目录模式）- **当前使用**

#### 特点
```
dist/equity_mermaid_tool_fixed/
├── equity_mermaid_tool.exe    ← 441 MB (启动器 + 部分代码)
└── _internal/                  ← 13,987 个文件
    ├── *.dll (236 个)
    ├── *.pyd (580 个)
    ├── base_library.zip
    └── src/assets/icons/
```

#### 优点 ✅
- **启动快** - 直接从文件系统加载，无需解压
- **占用空间小** - 不需要额外的临时文件空间
- **调试方便** - 可以直接查看和替换资源文件
- **更新方便** - 可以单独替换某些 DLL 或资源文件

#### 缺点 ❌
- **文件多** - 必须保持目录结构，不能只复制 exe
- **不够简洁** - 用户看到一堆文件可能感到困惑

#### 分发方式
```bash
# 方式 1：打包成 ZIP
压缩整个 equity_mermaid_tool_fixed 文件夹

# 方式 2：制作安装包
使用 Inno Setup 或 NSIS 制作安装程序

# 用户使用
解压后，双击 equity_mermaid_tool.exe 即可
（不能把 exe 单独复制出来使用！）
```

---

### 模式 2：onefile（单文件模式）

#### 特点
```
dist/
└── equity_mermaid_tool_onefile.exe  ← 单个文件，约 600+ MB
```

#### 优点 ✅
- **真正的单文件** - 只有一个 exe，方便分发
- **简洁** - 用户只需复制一个文件即可

#### 缺点 ❌
- **启动慢** - 每次运行需要解压到临时目录（约 3-10 秒）
- **占用空间大** - 运行时会在临时目录解压（额外占用 500+ MB）
- **文件大** - exe 文件本身更大（因为包含所有内容）
- **防病毒软件误报** - 更容易被杀毒软件拦截

#### 临时文件位置
运行时会解压到：
```
C:\Users\<用户名>\AppData\Local\Temp\_MEIxxxxxx\
```
退出程序后自动清理。

---

## 🔄 如何切换到单文件模式

### 1. 使用新的配置文件

我已经为您创建了 `equity_mermaid_onefile.spec`，使用方法：

```bash
# 打包成单文件
python -m PyInstaller equity_mermaid_onefile.spec --noconfirm

# 输出位置
dist/equity_mermaid_tool_onefile.exe
```

### 2. 关键区别

#### onedir 配置（当前）
```python
exe = EXE(pyz, a.scripts, ...)

# 重点：有 COLLECT 步骤
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, ...)
```

#### onefile 配置（单文件）
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,    # ← 打包到 exe 中
    a.zipfiles,    # ← 打包到 exe 中
    a.datas,       # ← 打包到 exe 中
    ...
)
# 重点：没有 COLLECT 步骤
```

---

## 📊 性能对比

| 特性 | onedir (当前) | onefile (单文件) |
|------|--------------|-----------------|
| **文件数量** | 1 exe + 13,987 文件 | 1 exe |
| **总大小** | ~880 MB | ~650 MB (但运行时解压) |
| **启动速度** | ⚡ 快速 (1-2秒) | 🐌 较慢 (5-10秒) |
| **磁盘占用** | ~880 MB | exe 650 MB + 临时 500 MB |
| **分发方便** | 需要打包整个文件夹 | ✅ 只需一个文件 |
| **资源更新** | ✅ 可单独替换 | ❌ 必须重新打包 |
| **防病毒友好** | ✅ 较少误报 | ⚠️ 容易误报 |

---

## 💡 推荐方案

### 方案 A：继续使用 onedir（推荐）

**适合场景**：
- 企业内部部署
- 需要频繁更新资源文件
- 希望启动速度快

**分发方式**：
```bash
# 1. 压缩整个文件夹
7z a equity_mermaid_v1.0.7z equity_mermaid_tool_fixed/

# 2. 或制作安装包
# 使用 Inno Setup 或 NSIS
```

### 方案 B：制作安装程序（最佳用户体验）

使用 **Inno Setup** 制作安装包：

```iss
[Setup]
AppName=股权结构可视化工具
AppVersion=1.0
DefaultDirName={pf}\EquityMermaidTool
OutputDir=installer
OutputBaseFilename=EquityMermaidTool_Setup

[Files]
Source: "dist\equity_mermaid_tool_fixed\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{commondesktop}\股权结构工具"; Filename: "{app}\equity_mermaid_tool.exe"
```

优点：
- ✅ 自动安装到合适位置
- ✅ 创建桌面快捷方式
- ✅ 支持卸载
- ✅ 专业的用户体验

### 方案 C：切换到 onefile

**适合场景**：
- 临时使用、演示
- 不介意启动速度
- 希望分发简单

**使用方法**：
```bash
python -m PyInstaller equity_mermaid_onefile.spec --noconfirm
```

---

## ⚠️ 重要提醒

### 当前模式（onedir）下：

1. **必须保持目录结构**
   ```
   ✅ 正确：
   equity_mermaid_tool_fixed/
   ├── equity_mermaid_tool.exe
   └── _internal/
   
   ❌ 错误：
   只复制 equity_mermaid_tool.exe
   ```

2. **分发时的完整清单**
   ```
   需要发给用户的内容：
   - 整个 equity_mermaid_tool_fixed 文件夹
   或
   - 压缩包（用户解压后保持结构）
   ```

3. **用户使用说明**
   ```
   1. 解压到任意目录（如 D:\软件\EquityTool\）
   2. 进入 equity_mermaid_tool_fixed 文件夹
   3. 双击 equity_mermaid_tool.exe 运行
   4. 不要移动 exe 文件到其他位置！
   ```

---

## 🛠️ 快速测试

### 测试当前 onedir 包

```bash
# 1. 进入打包目录
cd dist/equity_mermaid_tool_fixed

# 2. 运行
equity_mermaid_tool.exe

# 3. 测试移动 exe（应该失败）
copy equity_mermaid_tool.exe ..\..\
cd ..\..
equity_mermaid_tool.exe  # ← 会报错找不到依赖
```

### 测试 onefile 包

```bash
# 1. 打包
python -m PyInstaller equity_mermaid_onefile.spec --noconfirm

# 2. 运行（首次启动会慢一些）
dist\equity_mermaid_tool_onefile.exe

# 3. 可以移动到任何位置运行
copy dist\equity_mermaid_tool_onefile.exe D:\test.exe
D:\test.exe  # ← 正常运行
```

---

## 📝 总结

### 您的问题答案

**Q: 运行时需要 _internal 文件夹吗？**  
**A: 是的，必须需要！** exe 和 _internal 是一个整体。

### 如果想要单文件

使用我创建的 `equity_mermaid_onefile.spec`：
```bash
python -m PyInstaller equity_mermaid_onefile.spec --noconfirm
```

### 推荐配置

| 用途 | 推荐模式 | 原因 |
|------|---------|------|
| 企业内部 | onedir | 快速、稳定 |
| 外部分发 | onedir + 安装包 | 专业体验 |
| 临时演示 | onefile | 方便携带 |
| 开发测试 | onedir | 调试方便 |

---

**维护记录**：
- 2025-10-24: 创建打包模式对比文档
- 2025-10-24: 新增 onefile 配置文件

