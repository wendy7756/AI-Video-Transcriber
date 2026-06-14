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

def setup_environment(desktop: bool = False):
    """设置环境变量"""
    # Desktop / GUI 启动时 PATH 可能被裁剪，补全 Homebrew 常见路径
    extra_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
    current_path = os.environ.get("PATH", "")
    for p in extra_paths:
        if p not in current_path.split(os.pathsep):
            current_path = f"{p}{os.pathsep}{current_path}"
    os.environ["PATH"] = current_path

    if desktop:
        os.environ.setdefault("WHISPER_ENGINE", "auto")
        os.environ.setdefault("WHISPER_SPEED_PRESET", "fast")
        os.environ.setdefault("WHISPER_DEVICE", "auto")
        os.environ.setdefault("WHISPER_PRELOAD", "true")
        os.environ.setdefault("HOST", "127.0.0.1")
        if not os.getenv("OPENAI_API_KEY"):
            print("ℹ️  未设置 OPENAI_API_KEY，可在 UI 的 AI Settings 中配置")
        else:
            print("✅ 已设置 OpenAI API Key")
        return True

    # 设置OpenAI配置
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  警告: 未设置OPENAI_API_KEY环境变量")
        print("请设置环境变量: export OPENAI_API_KEY=your_api_key_here")
        return False
    
    print("✅ 已设置OpenAI API Key")
    
    if not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = "https://oneapi.basevec.com/v1"
        print("✅ 已设置OpenAI Base URL")
    
    # 设置其他默认配置
    if not os.getenv("WHISPER_MODEL_SIZE"):
        os.environ["WHISPER_MODEL_SIZE"] = "base"
    
    print("🔑 OpenAI API已配置，摘要功能可用")
    return True

def main():
    """主函数"""
    desktop_mode = "--desktop" in sys.argv
    # 检查是否使用生产模式（禁用热重载）
    production_mode = "--prod" in sys.argv or desktop_mode or os.getenv("PRODUCTION_MODE") == "true"
    
    print("🚀 Video Trans 启动检查")
    if desktop_mode:
        print("🖥  桌面模式")
    if production_mode:
        print("🔒 生产模式 - 热重载已禁用")
    else:
        print("🔧 开发模式 - 热重载已启用")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查FFmpeg
    if not check_ffmpeg():
        print("⚠️  FFmpeg未安装，可能影响某些视频格式的处理")
    
    # 设置环境
    setup_environment(desktop=desktop_mode)
    
    print("\n🎉 启动检查完成!")
    print("=" * 50)
    
    # 启动服务器
    host = os.getenv("HOST", "127.0.0.1" if desktop_mode else "0.0.0.0")
    port = int(os.getenv("PORT", "8765" if desktop_mode else "8000"))
    
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
            "--port", str(port)
        ]
        
        # 只在开发模式下启用热重载
        if not production_mode:
            cmd.append("--reload")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
