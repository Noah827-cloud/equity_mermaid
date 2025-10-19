# PowerShell 脚本：清除所有 Python 文件的 BOM 字符
# 使用方法：在项目根目录运行 powershell -ExecutionPolicy Bypass -File scripts\remove_bom.ps1

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "                    清除 BOM 字符工具" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$rootPath = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $rootPath

Write-Host "工作目录: $rootPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "正在扫描所有 Python 文件..." -ForegroundColor Green
Write-Host ""

$excludePaths = @('build', 'dist', '__pycache__', '.venv', 'venv', 'node_modules', '.git')
$foundCount = 0
$fixedCount = 0

Get-ChildItem -Path . -Include *.py -Recurse -File | Where-Object {
    $exclude = $false
    foreach ($excludePath in $excludePaths) {
        if ($_.FullName -match "\\$excludePath\\") {
            $exclude = $true
            break
        }
    }
    -not $exclude
} | ForEach-Object {
    $foundCount++
    $relativePath = $_.FullName.Replace($rootPath, "").TrimStart('\')
    
    $content = [System.IO.File]::ReadAllBytes($_.FullName)
    
    if ($content.Length -gt 2 -and $content[0] -eq 0xEF -and $content[1] -eq 0xBB -and $content[2] -eq 0xBF) {
        Write-Host "[发现 BOM] $relativePath" -ForegroundColor Red
        
        $newContent = $content[3..($content.Length-1)]
        [System.IO.File]::WriteAllBytes($_.FullName, $newContent)
        
        Write-Host "  ✓ 已修复 (删除了 3 字节)" -ForegroundColor Green
        $fixedCount++
    }
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "扫描完成！" -ForegroundColor Green
Write-Host "  - 扫描文件数: $foundCount" -ForegroundColor Yellow
Write-Host "  - 修复文件数: $fixedCount" -ForegroundColor Yellow

if ($fixedCount -eq 0) {
    Write-Host "  ✓ 所有文件都没有 BOM 问题！" -ForegroundColor Green
} else {
    Write-Host "  ✓ 已清理所有 BOM 字符！" -ForegroundColor Green
}
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# 等待用户按键
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

