@echo off
chcp 65001 >nul 2>&1
title AI Video Transcriber

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    echo Starting AI Video Transcriber...
    echo.
    "%VENV_PYTHON%" "%SCRIPT_DIR%start.py" %*
) else (
    echo [Error] Virtual environment not found.
    echo Please run install.bat or install.ps1 first.
    echo.
    pause
)
