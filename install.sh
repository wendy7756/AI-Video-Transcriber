#!/bin/bash

# AI影片轉錄器安裝腳本

echo "🚀 AI影片轉錄器安裝腳本"
echo "=========================="

# 檢查Python版本
echo "檢查Python環境..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
if [[ -z "$python_version" ]]; then
    echo "❌ 未找到Python3，請先安裝Python 3.8或更高版本"
    exit 1
fi
echo "✅ Python版本: $python_version"

# 檢查pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ 未找到pip3，請先安裝pip"
    exit 1
fi
echo "✅ pip已安裝"

# 安裝Python依賴
echo ""
echo "安裝Python依賴..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Python依賴安裝完成"
else
    echo "❌ Python依賴安裝失敗"
    exit 1
fi

# 檢查FFmpeg
echo ""
echo "檢查FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg已安裝"
else
    echo "⚠️  FFmpeg未安裝，正在嘗試安裝..."

    # 檢測作業系統
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y ffmpeg
        elif command -v yum &> /dev/null; then
            sudo yum install -y ffmpeg
        else
            echo "❌ 無法自動安裝FFmpeg，請手動安裝"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "❌ 請先安裝Homebrew，然後運行: brew install ffmpeg"
        fi
    else
        echo "❌ 不支援的作業系統，請手動安裝FFmpeg"
    fi
fi

# 創建必要的目錄
echo ""
echo "創建必要的目錄..."
mkdir -p temp static
echo "✅ 目錄創建完成"

# 設置權限
chmod +x start.py

echo ""
echo "🎉 安裝完成!"
echo ""
echo "使用方法:"
echo "  1. (可選) 配置OpenAI API金鑰以啟用智慧摘要功能"
echo "     export OPENAI_API_KEY=your_api_key_here"
echo ""
echo "  2. 啟動服務:"
echo "     python3 start.py"
echo ""
echo "  3. 打開瀏覽器訪問: http://localhost:8000"
echo ""
echo "支援的影片平台:"
echo "  - YouTube"
echo "  - Bilibili"
echo "  - 其他yt-dlp支援的平台"
