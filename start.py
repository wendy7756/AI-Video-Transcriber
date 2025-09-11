#!/usr/bin/env python3
"""
AI影片轉錄器啟動腳本
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """
    檢查依賴是否安裝。

    Returns:
        bool: 如果所有依賴都已安裝則返回True，否則返回False。
    """
    import sys
    required_packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "yt-dlp": "yt_dlp",
        "faster-whisper": "faster_whisper",
        "openai": "openai"
    }

    missing_packages = []
    for display_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(display_name)

    if missing_packages:
        print("❌ 缺少以下依賴包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n請運行以下命令安裝依賴:")
        print("source venv/bin/activate && pip install -r requirements.txt")
        return False

    print("✅ 所有依賴已安裝")
    return True

def check_ffmpeg():
    """
    檢查FFmpeg是否安裝。

    Returns:
        bool: 如果FFmpeg已安裝則返回True，否則返回False。
    """
    try:
        subprocess.run(["ffmpeg", "-version"],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      check=True)
        print("✅ FFmpeg已安裝")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 未找到FFmpeg")
        print("請安裝FFmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt install ffmpeg")
        print("  Windows: 從官網下載 https://ffmpeg.org/download.html")
        return False

def setup_environment():
    """
    設置環境變數。

    配置OpenAI API相關的環境變數。
    """
    # 設置OpenAI配置
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  警告: 未設置OPENAI_API_KEY環境變數")
        print("請設置環境變數: export OPENAI_API_KEY=your_api_key_here")
        return False
        print("✅ 已設置OpenAI API Key")

    if not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = "https://oneapi.basevec.com/v1"
        print("✅ 已設置OpenAI Base URL")

    # 設置其他預設配置
    if not os.getenv("WHISPER_MODEL_SIZE"):
        os.environ["WHISPER_MODEL_SIZE"] = "base"
    
    print(f"📊 Whisper 模型大小: {os.getenv('WHISPER_MODEL_SIZE')}")

    print("🔑 OpenAI API已配置，摘要功能可用")

def main():
    """
    主函數。

    執行啟動檢查並啟動FastAPI伺服器。
    """
    # 檢查是否使用生產模式（禁用熱重載）
    production_mode = "--prod" in sys.argv or os.getenv("PRODUCTION_MODE") == "true"

    print("🚀 AI影片轉錄器啟動檢查")
    if production_mode:
        print("🔒 生產模式 - 熱重載已禁用")
    else:
        print("🔧 開發模式 - 熱重載已啟用")
    print("=" * 50)

    # 檢查依賴
    if not check_dependencies():
        sys.exit(1)

    # 檢查FFmpeg
    if not check_ffmpeg():
        print("⚠️  FFmpeg未安裝，可能影響某些影片格式的處理")

    # 設置環境
    setup_environment()

    print("\n🎉 啟動檢查完成!")
    print("=" * 50)

    # 啟動伺服器
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8893))

    print(f"\n🌐 啟動伺服器...")
    print(f"   地址: http://localhost:{port}")
    print(f"   按 Ctrl+C 停止服務")
    print("=" * 50)

    try:
        # 切換到backend目錄並啟動服務
        backend_dir = Path(__file__).parent / "backend"
        os.chdir(backend_dir)

        cmd = [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", host,
            "--port", str(port)
        ]

        # 只在開發模式下啟用熱重載
        if not production_mode:
            cmd.append("--reload")

        subprocess.run(cmd)

    except KeyboardInterrupt:
        print("\n\n👋 服務已停止")
    except Exception as e:
        print(f"\n❌ 啟動失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
