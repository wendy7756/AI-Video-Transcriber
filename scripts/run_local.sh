#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d venv ]; then
  echo "请先运行: ./scripts/install_local.sh"
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate
exec python start.py --desktop --prod
