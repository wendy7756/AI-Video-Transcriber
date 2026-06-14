#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Video Trans 客户端打包"
echo "    项目: $ROOT"

if [ ! -d venv ]; then
  echo "❌ 请先运行: ./scripts/install_local.sh"
  exit 1
fi

if ! command -v ffmpeg >/dev/null; then
  echo "⚠️  未检测到 ffmpeg，转录可能失败。安装: brew install ffmpeg"
fi

cd desktop
npm install

# 写入项目根路径，供 .app 运行时定位 Python 后端
echo "$ROOT" > src-tauri/project_root.txt

set +e
npm run tauri build
BUILD_RC=$?
set -e

BUNDLE="$ROOT/desktop/src-tauri/target/release/bundle"
OUT="$ROOT/dist/client"
mkdir -p "$OUT"

APP_SRC="$BUNDLE/macos/Video Trans.app"
DMG_SRC=$(ls "$BUNDLE/dmg/"*.dmg 2>/dev/null | head -1)
DMG_NAME="Video Trans_0.1.0_aarch64.dmg"

if [ ! -d "$APP_SRC" ]; then
  echo "❌ 未找到 .app，打包失败 (exit $BUILD_RC)"
  exit 1
fi

rm -rf "$OUT/Video Trans.app"
cp -R "$APP_SRC" "$OUT/"
echo "✅ .app -> $OUT/Video Trans.app"

if [ -n "$DMG_SRC" ] && [ -f "$DMG_SRC" ]; then
  cp "$DMG_SRC" "$OUT/"
  echo "✅ dmg  -> $OUT/$(basename "$DMG_SRC")"
else
  echo "⚠️  Tauri dmg 打包未成功，使用 hdiutil 生成..."
  rm -f "$OUT/$DMG_NAME"
  hdiutil create -volname "Video Trans" -srcfolder "$OUT/Video Trans.app" -ov -format UDZO "$OUT/$DMG_NAME"
  echo "✅ dmg  -> $OUT/$DMG_NAME"
fi

echo ""
echo "产物目录: $OUT"
ls -lh "$OUT"
