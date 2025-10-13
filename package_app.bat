@echo off

:: Equity Relationship Diagram Tool - Packaging Script
:: This script packages the application using PyInstaller with --noconfirm flag

echo Starting packaging process...
echo. 

:: Use Python from virtual environment if available
echo Checking for virtual environment...
if exist ".venv" (
    echo Virtual environment found, using Python from .venv
    set "PYTHON_PATH=.venv\Scripts\python"
) else (
    echo No virtual environment found, using system Python
    set "PYTHON_PATH=python"
)

:: Check if Python is available
%PYTHON_PATH% --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please ensure Python is installed and added to PATH.
    pause
    exit /b 1
)

:: Check if PyInstaller is installed
%PYTHON_PATH% -m pip show pyinstaller > nul 2>&1
if %errorlevel% neq 0 (
    echo Error: PyInstaller not found. Attempting to install...
    %PYTHON_PATH% -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Failed to install PyInstaller. Please install manually.
        pause
        exit /b 1
    )
)

:: Execute packaging command with --noconfirm flag
echo Packaging application with PyInstaller...
echo Command: %PYTHON_PATH% -m PyInstaller equity_mermaid.spec --noconfirm
echo. 
%PYTHON_PATH% -m PyInstaller equity_mermaid.spec --noconfirm

:: Check packaging result
if %errorlevel% neq 0 (
    echo. 
    echo Error: Packaging failed! Please check error messages.
    pause
    exit /b 1
)

echo. 
echo Packaging completed successfully!
echo Executable location: dist\equity_mermaid_tool.exe
echo Complete distribution directory: dist\equity_mermaid_tool_fixed\
echo. 
echo Note: Packaging process automatically used --noconfirm flag to avoid overwrite prompts.
pause