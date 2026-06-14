#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/dist/client/Video Trans.app"

echo "==> Video Trans 客户端启动检查"
echo "    项目: $ROOT"

if [ ! -d "$ROOT/venv" ]; then
  echo "❌ 未找到 venv，请先运行: ./scripts/install_local.sh"
  exit 1
fi

if [ ! -f "$ROOT/start.py" ]; then
  echo "❌ 缺少 start.py"
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "⚠️  未检测到 ffmpeg，视频下载/转码可能失败。安装: brew install ffmpeg"
fi

if [ ! -d "$APP" ]; then
  echo "❌ 未找到客户端: $APP"
  echo "   请先运行: ./scripts/build_client.sh"
  exit 1
fi

export VIDEO_TRANS_ROOT="$ROOT"
open "$APP"
echo "✅ 已启动 Video Trans.app（自动检测/拉起后端，8765 占用时会尝试 8766–8799）"
