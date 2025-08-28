#!/usr/bin/env python3
"""
AI视频转录器启动脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """检查依赖是否安装"""
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
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装依赖:")
        print("source venv/bin/activate && pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖已安装")
    return True

def check_ffmpeg():
    """检查FFmpeg是否安装"""
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        print("✅ FFmpeg已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 未找到FFmpeg")
        print("请安装FFmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt install ffmpeg")
        print("  Windows: 从官网下载 https://ffmpeg.org/download.html")
        return False

def setup_environment():
    """设置环境变量"""
    # 设置OpenAI配置
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "sk-IOYS1zAFnSxg3tYCK7PhHUFoh98yf2WlIp0979vw911Oisen"
        print("✅ 已设置OpenAI API Key")
    
    if not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = "https://oneapi.basevec.com/v1"
        print("✅ 已设置OpenAI Base URL")
    
    # 设置其他默认配置
    if not os.getenv("WHISPER_MODEL_SIZE"):
        os.environ["WHISPER_MODEL_SIZE"] = "base"
    
    print("🔑 OpenAI API已配置，摘要功能可用")

def main():
    """主函数"""
    print("🚀 AI视频转录器启动检查")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查FFmpeg
    if not check_ffmpeg():
        print("⚠️  FFmpeg未安装，可能影响某些视频格式的处理")
    
    # 设置环境
    setup_environment()
    
    print("\n🎉 启动检查完成!")
    print("=" * 50)
    
    # 启动服务器
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    print(f"\n🌐 启动服务器...")
    print(f"   地址: http://localhost:{port}")
    print(f"   按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        # 切换到backend目录并启动服务
        backend_dir = Path(__file__).parent / "backend"
        os.chdir(backend_dir)
        
        cmd = [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", host,
            "--port", str(port),
            "--reload"
        ]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
