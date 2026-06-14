# Video Trans Desktop

Tauri 本地壳：启动 Python FastAPI sidecar，内嵌 WebView 加载 `http://127.0.0.1:8765`。

## 前置

```bash
# 在项目根目录
./scripts/install_local.sh
```

需要：Python 3.8+、FFmpeg、Rust、Node.js。

## 开发运行

```bash
cd desktop
npm install
npm run tauri dev
```

## 打包

```bash
cd desktop
npm run tauri build
```

产物位于 `desktop/src-tauri/target/release/bundle/`。

## 仅后端（无 Tauri）

```bash
./scripts/run_local.sh
# 浏览器打开 http://127.0.0.1:8765
```

桌面模式默认：
- `WHISPER_ENGINE=auto`（Apple Silicon 自动选 mlx-whisper，否则 faster-whisper）
- `WHISPER_SPEED_PRESET=balanced`
- `WHISPER_DEVICE=auto`（faster-whisper 有 CUDA 时用 GPU）
- API Key 可在 UI 的 AI Settings 配置，无需环境变量
