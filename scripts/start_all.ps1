# 股权结构图生成工具 - PowerShell 启动脚本
# 支持中文显示

# 设置控制台编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "                    股权结构图生成工具 - 启动脚本" -ForegroundColor Yellow
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 启动主界面(推荐) (端口: 8504)" -ForegroundColor Green
Write-Host "2. 启动图像识别模式 (端口: 8501)" -ForegroundColor Green
Write-Host "3. 启动手动编辑模式 (端口: 8502)" -ForegroundColor Green
Write-Host "4. 退出" -ForegroundColor Red
Write-Host ""

$choice = Read-Host "请选择功能 (1-4)"

$pythonPath = "C:\Users\z001syzk\AppData\Local\Programs\Python\Python313\python.exe"

switch ($choice) {
    "1" {
        Write-Host "正在启动主界面(推荐)..." -ForegroundColor Yellow
        & $pythonPath -m streamlit run main_page.py --server.port=8504
    }
    "2" {
        Write-Host "正在启动图像识别模式..." -ForegroundColor Yellow
        & $pythonPath -m streamlit run pages\1_图像识别模式.py --server.port=8501
    }
    "3" {
        Write-Host "正在启动手动编辑模式..." -ForegroundColor Yellow
        & $pythonPath -m streamlit run pages\2_手动编辑模式.py --server.port=8502
    }
    "4" {
        Write-Host "退出程序..." -ForegroundColor Red
        exit
    }
    default {
        Write-Host "无效的选择，请重新运行脚本。" -ForegroundColor Red
        Read-Host "按任意键继续"
        exit
    }
}

Read-Host "按任意键继续"
