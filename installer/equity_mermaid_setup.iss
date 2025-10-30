; Inno Setup 脚本
; 股权结构可视化工具安装程序配置
; 版本: 1.0
; 创建日期: 2025-10-24

#define MyAppName "股权结构可视化工具"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Company Name"
#define MyAppURL "https://your-website.com"
#define MyAppExeName "equity_mermaid_tool.exe"
#define MyAppDescription "股权结构图生成与分析工具"

[Setup]
; 应用程序基本信息
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 安装路径
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 输出设置
OutputDir=..\installer_output
OutputBaseFilename=EquityMermaidTool_Setup_v{#MyAppVersion}
; SetupIconFile=..\src\assets\icons\clarity_picture-solid.svg  ; SVG not supported, need .ico file
Compression=lzma2/max
SolidCompression=yes

; 系统要求
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; 权限
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; 界面设置
WizardStyle=modern
DisableWelcomePage=no
LicenseFile=..\README.md
InfoBeforeFile=installer_info.txt

; 卸载设置
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; 语言
ShowLanguageDialog=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"  ; Chinese language pack not installed by default

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch shortcut"; GroupDescription: "Additional icons:"; OnlyBelowVersion: 6.1; Flags: unchecked

[Files]
; Main program and all dependencies
Source: "..\dist\equity_mermaid_tool_fixed\equity_mermaid_tool.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\equity_mermaid_tool_fixed\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Optional files (commented out - these will be created at runtime)
; Source: "..\dist\equity_mermaid_tool_fixed\config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
; Source: "..\dist\equity_mermaid_tool_fixed\README.md"; DestDir: "{app}"; Flags: ignoreversion
; Source: "..\user_data\*"; DestDir: "{userappdata}\{#MyAppName}\user_data"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; 桌面快捷方式
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; 快速启动栏（Windows 7 及以下）
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; 安装完成后可选运行
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时删除运行时生成的文件
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\user_data\autosave"
Type: files; Name: "{app}\*.log"

[Code]
// 检查 .NET Framework 或其他依赖（可选）
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  
  // 这里可以添加依赖检查
  // 例如检查是否安装了必要的 VC++ 运行库等
  
  // 显示欢迎信息
  // MsgBox('欢迎安装股权结构可视化工具！', mbInformation, MB_OK);
end;

// 安装前检查
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  CheckExe: String;
begin
  Result := '';
  
  // 检查程序是否正在运行
  CheckExe := ExpandConstant('{app}\{#MyAppExeName}');
  if FileExists(CheckExe) then
  begin
    if CheckForMutexes('{#MyAppName}') then
    begin
      Result := '程序正在运行，请先关闭程序再继续安装。';
    end;
  end;
end;

// 卸载前检查
function InitializeUninstall(): Boolean;
begin
  Result := True;
  
  // 可以添加卸载前的确认对话框
  if MsgBox('Uninstall {#MyAppName}?', mbConfirmation, MB_YESNO) = IDYES then
    Result := True
  else
    Result := False;
end;
