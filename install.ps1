#Requires -Version 5.1
<#
.SYNOPSIS
    AI视频转录器 Windows 自动安装脚本
.DESCRIPTION
    检查 Python 环境、创建虚拟环境、安装依赖、安装 FFmpeg、初始化配置文件。
.NOTES
    用法: .\install.ps1  或通过 install.bat 双击运行
#>

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "===========================" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "===========================" -ForegroundColor Cyan
}

function Write-OK {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[!!] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[X]  $Message" -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# Step 1: 检查 Python
# ---------------------------------------------------------------------------

function Find-Python {
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $output = & $cmd --version 2>&1
            if ($output -match "Python\s+(\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -ge 3 -and $minor -ge 8) {
                    return @{ Cmd = $cmd; Version = "$major.$minor" }
                }
            }
        } catch {
            continue
        }
    }
    return $null
}

Write-Host ""
Write-Host "  AI Video Transcriber - Windows Installer" -ForegroundColor Magenta
Write-Host ""

Write-Step "Step 1/6: Python"

$py = Find-Python
if (-not $py) {
    Write-Fail "Python 3.8+ not found"
    Write-Host ""
    Write-Host "  Please install Python 3.8 or later:" -ForegroundColor White
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "  (Make sure to check 'Add Python to PATH' during installation)" -ForegroundColor White
    Write-Host ""
    exit 1
}

$PythonCmd = $py.Cmd
Write-OK "Python $($py.Version) ($PythonCmd)"

# ---------------------------------------------------------------------------
# Step 2: 虚拟环境
# ---------------------------------------------------------------------------

Write-Step "Step 2/6: Virtual Environment"

$VenvDir = Join-Path $ScriptDir "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

if (Test-Path $VenvPython) {
    Write-OK "venv/ already exists, reusing"
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor White
    & $PythonCmd -m venv $VenvDir
    if (-not (Test-Path $VenvPython)) {
        Write-Fail "Failed to create virtual environment"
        exit 1
    }
    Write-OK "venv/ created"
}

# ---------------------------------------------------------------------------
# Step 3: 安装 Python 依赖
# ---------------------------------------------------------------------------

Write-Step "Step 3/6: Python Dependencies"

Write-Host "Upgrading pip..." -ForegroundColor White
& $VenvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null
Write-OK "pip upgraded"

Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor White
& $VenvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Failed to install Python dependencies"
    exit 1
}
Write-OK "All Python dependencies installed"

# ---------------------------------------------------------------------------
# Step 4: FFmpeg
# ---------------------------------------------------------------------------

Write-Step "Step 4/6: FFmpeg"

$ffmpegInstalled = $false
try {
    $null = & ffmpeg -version 2>&1
    $ffmpegInstalled = $true
} catch {
    $ffmpegInstalled = $false
}

if ($ffmpegInstalled) {
    Write-OK "FFmpeg already installed"
} else {
    Write-Host "FFmpeg not found, attempting to install..." -ForegroundColor White

    $installed = $false

    # Try winget
    if (-not $installed) {
        try {
            $null = Get-Command winget -ErrorAction Stop
            Write-Host "  Trying winget..." -ForegroundColor White
            & winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $installed = $true
                Write-OK "FFmpeg installed via winget"
            }
        } catch { }
    }

    # Try chocolatey
    if (-not $installed) {
        try {
            $null = Get-Command choco -ErrorAction Stop
            Write-Host "  Trying chocolatey..." -ForegroundColor White
            & choco install ffmpeg -y 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $installed = $true
                Write-OK "FFmpeg installed via chocolatey"
            }
        } catch { }
    }

    # Try scoop
    if (-not $installed) {
        try {
            $null = Get-Command scoop -ErrorAction Stop
            Write-Host "  Trying scoop..." -ForegroundColor White
            & scoop install ffmpeg 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $installed = $true
                Write-OK "FFmpeg installed via scoop"
            }
        } catch { }
    }

    if (-not $installed) {
        Write-Warn "Could not install FFmpeg automatically"
        Write-Host ""
        Write-Host "  Please install FFmpeg manually:" -ForegroundColor White
        Write-Host "    Option 1: winget install Gyan.FFmpeg" -ForegroundColor White
        Write-Host "    Option 2: choco install ffmpeg" -ForegroundColor White
        Write-Host "    Option 3: Download from https://ffmpeg.org/download.html" -ForegroundColor White
        Write-Host "              and add it to your system PATH" -ForegroundColor White
        Write-Host ""
    }
}

# ---------------------------------------------------------------------------
# Step 5: 创建目录
# ---------------------------------------------------------------------------

Write-Step "Step 5/6: Directories"

foreach ($dir in @("temp", "static")) {
    $path = Join-Path $ScriptDir $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-OK "Created $dir/"
    } else {
        Write-OK "$dir/ already exists"
    }
}

# ---------------------------------------------------------------------------
# Step 6: .env 配置
# ---------------------------------------------------------------------------

Write-Step "Step 6/6: Configuration"

$envFile = Join-Path $ScriptDir ".env"
$envExample = Join-Path $ScriptDir ".env.example"

if (Test-Path $envFile) {
    Write-OK ".env already exists, skipping"
} elseif (Test-Path $envExample) {
    Copy-Item $envExample $envFile
    Write-OK ".env created from .env.example"
    Write-Warn "Please edit .env and set your OPENAI_API_KEY"
} else {
    Write-Warn ".env.example not found, skipping .env creation"
}

# ---------------------------------------------------------------------------
# 完成
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "===========================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "===========================" -ForegroundColor Green
Write-Host ""
Write-Host "  Usage:" -ForegroundColor White
Write-Host ""
Write-Host "    1. (Optional) Edit .env to set OPENAI_API_KEY" -ForegroundColor White
Write-Host ""
Write-Host "    2. Start the server (choose one):" -ForegroundColor White
Write-Host "       Double-click start.bat" -ForegroundColor Yellow
Write-Host "       or run: .\venv\Scripts\python.exe start.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "    3. Open browser:" -ForegroundColor White
Write-Host "       http://localhost:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Supported platforms: YouTube, Bilibili, and more (via yt-dlp)" -ForegroundColor White
Write-Host ""
