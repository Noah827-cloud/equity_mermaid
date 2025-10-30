# 安装包制作指南

## 📦 如何制作安装包

### 准备工作

#### 1. 安装 Inno Setup

**下载地址**: https://jrsoftware.org/isdl.php

**安装步骤**:
1. 下载 **Inno Setup 6** (推荐最新版本)
2. 运行安装程序
3. 使用默认安装路径: `C:\Program Files (x86)\Inno Setup 6\`
4. 安装完成

#### 2. 确保已完成打包

确保您已经运行了 `build_exe.bat` 并成功生成了：
```
dist/equity_mermaid_tool_fixed/
├── equity_mermaid_tool.exe
└── _internal/
```

---

## 🚀 快速开始

### 方法 1：使用自动化脚本（推荐）

```batch
# 进入 installer 目录
cd installer

# 运行自动构建脚本
build_installer.bat
```

脚本会自动：
- ✅ 检查 Inno Setup 是否安装
- ✅ 检查打包文件是否完整
- ✅ 编译生成安装包
- ✅ 显示输出位置和大小

### 方法 2：手动编译

1. 打开 Inno Setup
2. 点击 `File` → `Open`
3. 选择 `installer/equity_mermaid_setup.iss`
4. 点击 `Build` → `Compile` 或按 `Ctrl+F9`
5. 等待编译完成

---

## 📁 文件结构

```
项目根目录/
├── dist/
│   └── equity_mermaid_tool_fixed/    ← 打包输出（必需）
│       ├── equity_mermaid_tool.exe
│       └── _internal/
│
├── installer/                         ← 安装包配置
│   ├── equity_mermaid_setup.iss      ← Inno Setup 脚本
│   ├── installer_info.txt            ← 安装前说明
│   ├── build_installer.bat           ← 自动构建脚本
│   └── INSTALLER_GUIDE.md            ← 本文档
│
└── installer_output/                  ← 安装包输出（自动创建）
    └── EquityMermaidTool_Setup_v1.0.0.exe
```

---

## ⚙️ 配置说明

### 基本信息配置

编辑 `equity_mermaid_setup.iss` 文件顶部：

```pascal
#define MyAppName "股权结构可视化工具"
#define MyAppVersion "1.0.0"                    ← 修改版本号
#define MyAppPublisher "Your Company Name"      ← 修改公司名称
#define MyAppURL "https://your-website.com"     ← 修改网址
```

### 安装路径

默认安装到 `C:\Program Files\股权结构可视化工具\`

要修改：
```pascal
DefaultDirName={autopf}\{#MyAppName}
```

可选值：
- `{autopf}` = Program Files (64位系统自动判断)
- `{pf}` = Program Files
- `{pf32}` = Program Files (x86)
- `{userdocs}` = 用户文档目录
- `{localappdata}` = 本地应用数据目录

### 快捷方式配置

```pascal
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(&D)"; 
    GroupDescription: "附加图标:"; 
    Flags: unchecked    ← checked=默认勾选, unchecked=默认不勾选
```

### 文件包含配置

```pascal
[Files]
; 主程序
Source: "..\dist\equity_mermaid_tool_fixed\equity_mermaid_tool.exe"; 
    DestDir: "{app}"; 
    Flags: ignoreversion

; _internal 目录（包含所有依赖）
Source: "..\dist\equity_mermaid_tool_fixed\_internal\*"; 
    DestDir: "{app}\_internal"; 
    Flags: ignoreversion recursesubdirs createallsubdirs
```

---

## 🎨 自定义安装包

### 1. 更改应用图标

```pascal
SetupIconFile=..\src\assets\icons\your_icon.ico
```

**注意**: 需要 `.ico` 格式，您可以使用在线工具将 SVG 转换为 ICO：
- https://convertio.co/zh/svg-ico/
- https://www.aconvert.com/cn/icon/svg-to-ico/

### 2. 添加许可协议

创建 `LICENSE.txt` 文件，然后：
```pascal
LicenseFile=..\LICENSE.txt
```

### 3. 添加自述文件

```pascal
InfoAfterFile=..\RELEASE_NOTES.txt
```

### 4. 更改安装界面语言

```pascal
[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
```

### 5. 自定义安装提示

编辑 `[Messages]` 部分：
```pascal
[Messages]
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=这将在您的计算机上安装 [name/ver]。
```

---

## 🧪 测试安装包

### 测试清单

#### ✅ 安装测试
- [ ] 双击安装包能正常启动
- [ ] 安装界面显示正常（中文、图标等）
- [ ] 可以选择安装路径
- [ ] 安装进度显示正常
- [ ] 安装完成后文件完整

#### ✅ 运行测试
- [ ] 桌面快捷方式（如果创建）能正常启动
- [ ] 开始菜单快捷方式能正常启动
- [ ] 直接运行 exe 能正常启动
- [ ] 程序功能正常（图像识别、手动编辑等）
- [ ] 配置文件能正常保存

#### ✅ 卸载测试
- [ ] 控制面板能找到程序
- [ ] 卸载程序能正常启动
- [ ] 卸载完成后文件被删除
- [ ] 开始菜单项被删除
- [ ] 桌面快捷方式被删除（如果创建）

### 推荐测试环境

1. **本机测试**
   - 快速验证基本功能
   
2. **虚拟机测试**（强烈推荐）
   - 使用 VMware 或 VirtualBox
   - 创建纯净的 Windows 10/11 虚拟机
   - 测试完整的安装-使用-卸载流程
   
3. **不同系统测试**
   - Windows 10 (64-bit)
   - Windows 11 (64-bit)
   - 不同语言环境

---

## 📊 安装包信息

### 生成的安装包特性

| 特性 | 说明 |
|------|------|
| **文件名** | `EquityMermaidTool_Setup_v1.0.0.exe` |
| **大小** | 约 400-500 MB（压缩后） |
| **压缩** | LZMA2 最大压缩 |
| **界面** | 现代化 Windows 风格 |
| **语言** | 简体中文 |
| **系统要求** | Windows 10 x64 或更高 |
| **权限** | 需要管理员权限 |

### 安装包包含内容

```
安装后的目录结构:
C:\Program Files\股权结构可视化工具\
├── equity_mermaid_tool.exe      ← 主程序
├── _internal\                    ← 所有依赖
│   ├── *.dll (236个)
│   ├── *.pyd (580个)
│   └── src\assets\icons\         ← SVG 图标
├── config.json                   ← 配置文件
└── README.md                     ← 说明文档
```

---

## 🔧 常见问题

### Q1: 编译失败，提示找不到文件

**原因**: 源文件路径不正确

**解决**:
1. 确保已运行 `build_exe.bat` 完成打包
2. 检查 `dist/equity_mermaid_tool_fixed/` 目录存在
3. 检查 `.iss` 文件中的路径是否正确

### Q2: 安装包太大

**原因**: 包含了完整的 Python 环境和所有依赖

**说明**: 这是正常的
- onedir 模式: ~880 MB
- 压缩后安装包: ~400-500 MB
- 这是因为包含了完整的 Streamlit、Pandas、PyArrow 等库

**优化建议**:
- 考虑使用 onefile 模式（单文件）
- 或使用在线安装包（分阶段下载）

### Q3: 安装后程序无法运行

**检查项**:
1. 确认 `_internal` 目录被正确复制
2. 检查防病毒软件是否拦截
3. 以管理员权限运行
4. 检查系统是否满足要求（Win10 x64+）

### Q4: 想修改安装位置的默认值

编辑 `.iss` 文件：
```pascal
; 默认安装到 Program Files
DefaultDirName={autopf}\{#MyAppName}

; 改为用户文档目录
DefaultDirName={userdocs}\{#MyAppName}

; 改为自定义路径
DefaultDirName=C:\MyApps\{#MyAppName}
```

### Q5: 想让用户可以不用管理员权限安装

```pascal
; 将此行改为 lowest
PrivilegesRequired=lowest

; 并修改默认安装路径到用户目录
DefaultDirName={localappdata}\{#MyAppName}
```

---

## 📤 分发安装包

### 方法 1: 直接分发 .exe 文件

```
将 installer_output/EquityMermaidTool_Setup_v1.0.0.exe 发送给用户
用户双击即可安装
```

### 方法 2: 打包成 ZIP（带说明）

```
创建 ZIP 包含:
├── EquityMermaidTool_Setup_v1.0.0.exe
├── 安装说明.txt
└── 系统要求.txt
```

### 方法 3: 制作网络安装包

可以上传到网站/网盘，提供下载链接：
- 百度网盘
- 阿里云盘
- 腾讯微云
- 或公司内部服务器

### 用户安装步骤

给用户的说明：
```
1. 下载 EquityMermaidTool_Setup_v1.0.0.exe
2. 双击运行安装程序
3. 如果出现 Windows 安全提示，点击"运行"
4. 按照安装向导完成安装
5. 安装完成后，从桌面或开始菜单启动程序
```

---

## 🎯 版本更新

### 更新版本号

1. 修改 `.iss` 文件：
```pascal
#define MyAppVersion "1.0.1"  ← 改为新版本
```

2. 重新编译安装包

### 支持升级安装

Inno Setup 会自动检测并覆盖旧版本，用户数据会保留。

---

## 💡 高级功能

### 1. 添加自定义安装步骤

```pascal
[Run]
; 安装后自动创建用户数据目录
Filename: "{cmd}"; Parameters: "/c mkdir ""{userappdata}\{#MyAppName}\user_data"""; Flags: runhidden

; 安装完成后打开网站
Filename: "https://your-website.com"; Flags: shellexec postinstall skipifsilent; Description: "访问官网"
```

### 2. 检测已安装版本

```pascal
[Code]
function InitializeSetup(): Boolean;
var
  OldVersion: String;
begin
  Result := True;
  
  // 读取已安装版本
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1', 
     'DisplayVersion', OldVersion) then
  begin
    if MsgBox('检测到已安装版本 ' + OldVersion + '，是否覆盖安装？', 
       mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;
```

### 3. 添加多语言支持

```pascal
[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
chinesesimplified.LaunchProgram=启动程序
english.LaunchProgram=Launch Program
japanese.LaunchProgram=プログラムを起動
```

---

## 📝 总结

✅ **现在您可以**:
1. 运行 `installer/build_installer.bat` 自动制作安装包
2. 得到专业的 Windows 安装程序
3. 用户体验类似专业软件（自动安装、卸载等）
4. 不需要向用户解释如何使用 onedir 包

✅ **优势**:
- 专业的安装界面
- 自动处理文件结构
- 支持完整卸载
- 创建快捷方式
- 注册到系统

---

**维护记录**:
- 2025-10-24: 创建安装包制作指南
- 2025-10-24: 添加 Inno Setup 配置文件
- 2025-10-24: 创建自动构建脚本

