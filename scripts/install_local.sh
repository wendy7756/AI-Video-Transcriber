#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Video Trans 本地环境安装"
echo "    目录: $ROOT"

if ! command -v python3 >/dev/null; then
  echo "❌ 需要 python3"
  exit 1
fi

if ! command -v ffmpeg >/dev/null; then
  echo "⚠️  未检测到 ffmpeg，请安装: brew install ffmpeg"
fi

if [ ! -d venv ]; then
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "✅ 本地 Python 环境就绪"
echo "   启动桌面版: cd desktop && npm install && npm run tauri dev"
echo "   或仅后端:   ./scripts/run_local.sh"
