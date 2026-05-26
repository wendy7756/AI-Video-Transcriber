<div align="center">

# AI Video Transcriber

English | [中文](README_ZH.md)

An AI-powered tool to transcribe and summarize videos and podcasts — paste a URL from YouTube, TikTok, Bilibili, Apple Podcasts, SoundCloud, and 30+ platforms, **or upload a local file** (audio, video, or plain text).

![Interface](en_video.png)

</div>

## ✨ Features

- 🎥 **Multi-Platform Support**: Works with YouTube, TikTok, Bilibili, Apple Podcasts, SoundCloud, and 30+ more
- 📁 **Local File Upload**: Drag-and-drop or pick a file — supported formats include `.txt` (treated as transcript text), `.mp3`, `.mp4`, `.m4a`, `.wav`, `.webm`, `.mkv`, `.ogg`, `.flac`. Media is normalized with FFmpeg for Whisper; the same optimize → translate → summarize pipeline runs as for URLs
- ⚡ **Subtitle-First Architecture**: For platforms with native subtitles (e.g. YouTube), transcripts are extracted instantly — no audio download needed. Whisper is only used as a fallback, making the whole pipeline dramatically faster.
- 🗣️ **Intelligent Transcription**: High-accuracy speech-to-text using Faster-Whisper when subtitles aren't available
- 🤖 **AI Text Optimization**: Automatic typo correction, sentence completion, and intelligent paragraphing
- 🌍 **Multi-Language Summaries**: Generate intelligent summaries in multiple languages
- 🔧 **Bring Your Own Model**: Configure any OpenAI-compatible API endpoint (OpenAI, OpenRouter, local LLM, etc.) directly in the UI — enter your API Base URL and API Key, then click **Fetch** to auto-discover all available models and select the one you want
- ⚙️ **Conditional Translation**: Auto-translates the transcript when the summary language differs from the source language
- 📱 **Mobile-Friendly**: Perfect support for mobile devices

[![Star History Chart](https://api.star-history.com/svg?repos=wendy7756/AI-Video-Transcriber&type=Date)](https://star-history.com/#wendy7756/AI-Video-Transcriber&Date)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg (required for yt-dlp audio extraction and for normalizing uploaded media)
- An API key from any OpenAI-compatible provider (OpenAI, OpenRouter, etc.) — configured directly in the UI, no server-side env var needed

### Installation

#### Method 1: Automatic Installation

```bash
# Clone the repository
git clone https://github.com/wendy7756/AI-Video-Transcriber.git
cd AI-Video-Transcriber

# Run installation script
chmod +x install.sh
./install.sh
```

#### Method 2: Docker

```bash
# Clone the repository
git clone https://github.com/wendy7756/AI-Video-Transcriber.git
cd AI-Video-Transcriber

# Using Docker Compose (easiest)
cp .env.example .env
# Edit .env file if you want server-side defaults (optional)
docker-compose up -d

# Or using Docker directly
docker build -t ai-video-transcriber .
docker run -p 8000:8000 --env-file .env ai-video-transcriber
```

The image uses **Python 3.12** (Debian Bookworm), upgrades `pip`/`setuptools`/`wheel`, then installs from `requirements.txt` — same version constraints as a fresh local venv on a current Python.

#### Method 3: Manual Installation

1. **Install Python Dependencies**
```bash
# macOS (PEP 668) strongly recommends using a virtualenv
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2. **Install FFmpeg**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg
```

3. **Configure Environment Variables** *(optional)*
```bash
# If you prefer server-side defaults, set these — otherwise configure via the UI
export OPENAI_API_KEY="your_api_key_here"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"  # any OpenAI-compatible endpoint
```

### Start the Service

```bash
python3 start.py
```

After the service starts, open your browser and visit `http://localhost:8000`

#### Production Mode (Recommended for long videos)

To avoid SSE disconnections during long processing, start in production mode (hot-reload disabled):

```bash
python3 start.py --prod
```

This keeps the SSE connection stable throughout long tasks (30–60+ min).

#### Run with explicit env (example)

```bash
source venv/bin/activate
export OPENAI_API_KEY=your_api_key_here         # optional: server-side default
# export OPENAI_BASE_URL=https://openrouter.ai/api/v1  # optional: server-side default
python3 start.py --prod
```

## 📖 Usage Guide

1. **Choose input — URL or file**
   - **Video / podcast URL**: Paste a link from YouTube, Bilibili, or any other supported platform into the input field
   - **Local file**: Drag a file onto the dashed upload area (or click to browse). Same **Transcribe** button starts the job; uploads use the same API route as URLs (`POST /api/process-video` with multipart `file`), which helps when a reverse proxy only allows that path
2. **Select Summary Language**: Choose the output language from the dropdown next to the input area
3. **(Optional) Configure AI Model**: Click **AI Settings** to expand the panel
   - Enter your **API Base URL** (e.g. `https://openrouter.ai/api/v1`) and **API Key**
   - Click **Fetch** to auto-load all models from that provider
   - Select the model you want — or leave blank to use the server default
4. **Start Processing**: Click the **Transcribe** button. For **URL** jobs, the progress bar shows which mode is active:
   - **⚡ Subtitle** (green) — native subtitles found, transcript extracted in seconds
   - **🎙 Whisper** (amber) — no subtitles available, downloading audio for transcription
   For **local uploads**, media is normalized with FFmpeg then transcribed with Whisper; plain **`.txt`** files skip download/Whisper and go straight into the text pipeline (optimize → summary, and translation when languages differ).
5. **View Results**: Review the optimized transcript and AI summary
   - If transcript language ≠ selected summary language, a **Translation** tab appears automatically
6. **Download Files**: Save Markdown-formatted files (Transcript / Translation / Summary)

## 🛠️ Technical Architecture

### Backend Stack
- **FastAPI**: Modern Python web framework
- **yt-dlp**: Video downloading and processing
- **FFmpeg**: Audio extraction and local upload normalization (mono 16 kHz for Whisper)
- **Faster-Whisper**: Efficient speech transcription
- **OpenAI API**: Intelligent text summarization

### Frontend Stack
- **HTML5 + CSS3**: Responsive interface design
- **JavaScript (ES6+)**: Modern frontend interactions
- **Marked.js**: Markdown rendering
- **Font Awesome**: Icon library

### Project Structure
```
AI-Video-Transcriber/
├── backend/                 # Backend code
│   ├── main.py             # FastAPI main application
│   ├── video_processor.py  # Video processing module
│   ├── transcriber.py      # Transcription module
│   ├── summarizer.py       # Summary module
│   ├── translator.py       # Translation module
│   └── llm_sanitize.py     # Post-process LLM outputs (strip boilerplate)
├── static/                 # Frontend files
│   ├── index.html          # Main page
│   └── app.js              # Frontend logic
├── temp/                   # Temporary files directory
├── Dockerfile              # Docker image configuration
├── docker-compose.yml      # Docker Compose configuration
├── .dockerignore           # Docker ignore rules
├── .env.example            # Environment variables template
├── requirements.txt        # Python dependencies
├── start.py               # Startup script
└── README.md              # Project documentation
```

## ⚙️ Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | API key (server-side default) | - | No — can be set in UI instead |
| `HOST` | Server address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `WHISPER_MODEL_SIZE` | Whisper model size | `base` | No |
| `UPLOAD_MAX_MB` | Maximum upload size for local files (MB) | `200` | No |
| `YT_DLP_COOKIES_FILE` | Path to a Netscape-format `cookies.txt` for yt-dlp | - | No — needed to bypass YouTube bot-check |
| `YT_DLP_COOKIES_BROWSER` | Read cookies from a local browser profile (e.g. `chrome`, `firefox`, `chrome:Default`) | - | No — alternative to `YT_DLP_COOKIES_FILE` |
| `YT_DLP_SOCKET_TIMEOUT` | yt-dlp socket timeout in seconds | `60` | No |
| `YT_DLP_RETRIES` | yt-dlp retries for transient errors | `10` | No |
| `YT_DLP_FRAGMENT_RETRIES` | yt-dlp retries per HLS/DASH fragment | `10` | No |
| `YT_DLP_REMOTE_COMPONENTS` | Comma-separated remote-component sources for yt-dlp's EJS JS-challenge solver (needed for YouTube's `n` parameter; requires a JS runtime like `deno` or `node`) | `ejs:github` | No |

An optional dedicated endpoint `POST /api/process-upload` exists with the same behavior as sending `file` to `/api/process-video`.

### Whisper Model Size Options

| Model | Parameters | English-only | Multilingual | Speed | Memory Usage |
|-------|------------|--------------|--------------|-------|--------------|
| tiny | 39 M | ✓ | ✓ | Fast | Low |
| base | 74 M | ✓ | ✓ | Medium | Low |
| small | 244 M | ✓ | ✓ | Medium | Medium |
| medium | 769 M | ✓ | ✓ | Slow | Medium |
| large | 1550 M | ✗ | ✓ | Very Slow | High |

## 🔧 FAQ

### Q: Why is transcription slow?
A: Transcription speed depends on video length, Whisper model size, and hardware performance. Try using smaller models (like tiny or base) to improve speed.

### Q: Which video platforms are supported?
A: All platforms supported by yt-dlp, including but not limited to: YouTube, TikTok, Facebook, Instagram, Twitter, Bilibili, Youku, iQiyi, Tencent Video, etc.

### Q: What local file types and size limits apply?
A: Allowed extensions include `.txt`, `.mp3`, `.mp4`, `.m4a`, `.wav`, `.webm`, `.mkv`, `.ogg`, `.flac`. Default max size is **200 MB** per file; override with the `UPLOAD_MAX_MB` environment variable on the server.

### Q: What if the AI optimization features are unavailable?
A: AI features require an API key from any OpenAI-compatible provider (OpenAI, OpenRouter, etc.). You can enter it directly in the **AI Settings** panel in the UI — no server restart needed. Alternatively, set `OPENAI_API_KEY` as an environment variable for a server-side default.

### Q: YouTube returns "下载视频失败: ERROR: [download] Got error: timed out" or "Sign in to confirm you're not a bot"
A: YouTube increasingly blocks unauthenticated requests from VPS / datacenter IPs. Both the in-app "Got error: timed out" wrapper and yt-dlp's "Sign in to confirm you're not a bot" message ultimately come from the same anti-bot check. Supply YouTube cookies from a logged-in browser:

**Option 1 — cookies file (recommended for VPS/Docker):**
1. Open YouTube in your **personal browser** (logged in to a YouTube account).
2. Install a "Get cookies.txt" extension (e.g. "Get cookies.txt LOCALLY" for Chrome/Firefox) and export cookies from `youtube.com` as Netscape format.
3. Upload `cookies.txt` to the server, then set the env var:
   ```bash
   export YT_DLP_COOKIES_FILE=/absolute/path/to/cookies.txt
   ```
4. Restart the service. The same file is reused for all yt-dlp calls (info probe, subtitle download, audio download).

**Option 2 — read directly from a browser on the same host** (only useful if a logged-in browser is installed alongside the server):
```bash
export YT_DLP_COOKIES_BROWSER=chrome           # or firefox, edge, brave, ...
# Or with an explicit profile / user-data-dir:
export YT_DLP_COOKIES_BROWSER=chrome:Default
export YT_DLP_COOKIES_BROWSER=chrome:/home/you/.config/google-chrome
```

**Notes & tips:**
- Re-export cookies if YouTube starts rejecting them again (cookies expire / get rotated, especially after long idle periods).
- Use a low-traffic / throwaway YouTube account if you're worried about it being rate-limited.
- For Docker, mount the cookies file read-only and pass through the env var:
  ```bash
  docker run -v /host/path/cookies.txt:/data/cookies.txt:ro \
    -e YT_DLP_COOKIES_FILE=/data/cookies.txt \
    -p 8000:8000 --env-file .env ai-video-transcriber
  ```
- For other platforms (Bilibili, TikTok, etc.) the same env vars apply — export cookies from your logged-in browser on that platform.
- If you still see download timeouts even with valid cookies, the upstream link may be slow; bump `YT_DLP_SOCKET_TIMEOUT` and `YT_DLP_RETRIES`.

### Q: YouTube returns `ERROR: Requested format is not available`
A: yt-dlp couldn't decode YouTube's `n` URL parameter (since 2026.x, YouTube enforces a JS-based anti-bot challenge on most videos). Without a JS runtime + solver script, yt-dlp only sees storyboard formats, so format selection like `bestaudio/best` fails.

The bundled Docker image already installs **deno** and the solver is downloaded automatically on first use (via `YT_DLP_REMOTE_COMPONENTS=ejs:github`). For a **bare-metal** install:

1. Install a JS runtime (deno is the lightest):
   ```bash
   curl -fsSL https://deno.land/install.sh | sh -s -- -y --no-modify-path
   export PATH=$HOME/.deno/bin:$PATH
   # (or install Node.js: `apt install nodejs` / `nvm install --lts`)
   ```
2. Make sure `YT_DLP_REMOTE_COMPONENTS` is **not** set to empty (default `ejs:github` already works).
3. Restart the service.

If you don't want yt-dlp to fetch the solver from GitHub at runtime, you can pre-install the `ejs` bundle yourself and set `YT_DLP_REMOTE_COMPONENTS=` (empty). See yt-dlp's [EJS docs](https://github.com/yt-dlp/yt-dlp/wiki/EJS) for details.

### Q: I get HTTP 500 errors when starting/using the service. Why?
A: In most cases this is an environment configuration issue rather than a code bug. Please check:
- Ensure a virtualenv is activated: `source venv/bin/activate`
- Install deps inside the venv: `pip install -r requirements.txt`
- Configure your API key in the **AI Settings** panel, or set `OPENAI_API_KEY` as an env var
- Install FFmpeg: `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Debian/Ubuntu)
- If port 8000 is occupied, stop the old process or change `PORT`

### Q: How to handle long videos?
A: The system can process videos of any length, but processing time will increase accordingly. For very long videos, consider using smaller Whisper models.

### Q: How to use Docker for deployment?
A: Docker provides the easiest deployment method:

**Prerequisites:**
- Install Docker Desktop from https://www.docker.com/products/docker-desktop/
- Ensure Docker service is running

**Quick Start:**
```bash
# Clone and setup
git clone https://github.com/wendy7756/AI-Video-Transcriber.git
cd AI-Video-Transcriber
cp .env.example .env
# Edit .env file to set server-side defaults (optional)

# Start with Docker Compose (recommended)
docker-compose up -d

# Or build and run manually
docker build -t ai-video-transcriber .
docker run -p 8000:8000 --env-file .env ai-video-transcriber
```

**Common Docker Issues:**
- **Port conflict**: Change port mapping `-p 8001:8000` if 8000 is occupied
- **Permission denied**: Ensure Docker Desktop is running and you have proper permissions
- **Build fails**: Check disk space (need ~2GB free) and network connection
- **Container won't start**: Check Docker logs with `docker logs <container_id>`

**Docker Commands:**
```bash
# View running containers
docker ps

# Check container logs
docker logs ai-video-transcriber-ai-video-transcriber-1

# Stop service
docker-compose down

# Rebuild after changes
docker-compose build --no-cache
```

### Q: What are the memory requirements?
A: Memory usage varies depending on the deployment method and workload:

**Docker Deployment:**
- **Base memory**: ~128MB for idle container
- **During processing**: 500MB - 2GB depending on video length and Whisper model
- **Docker image size**: ~1.6GB disk space required
- **Recommended**: 4GB+ RAM for smooth operation

**Traditional Deployment:**
- **Base memory**: ~50-100MB for FastAPI server
- **Whisper models memory usage**:
  - `tiny`: ~150MB
  - `base`: ~250MB  
  - `small`: ~750MB
  - `medium`: ~1.5GB
  - `large`: ~3GB
- **Peak usage**: Base + Model + Video processing (~500MB additional)

**Memory Optimization Tips:**
```bash
# Use smaller Whisper model to reduce memory usage
WHISPER_MODEL_SIZE=tiny  # or base

# For Docker, limit container memory if needed
docker run -m 1g -p 8000:8000 --env-file .env ai-video-transcriber

# Monitor memory usage
docker stats ai-video-transcriber-ai-video-transcriber-1
```

### Q: Network connection errors or timeouts?
A: If you encounter network-related errors during video downloading or API calls, try these solutions:

**Common Network Issues:**
- Video download fails with "Unable to extract" or timeout errors
- OpenAI API calls return connection timeout or DNS resolution failures
- Docker image pull fails or is extremely slow

**Solutions:**
1. **Switch VPN/Proxy**: Try connecting to a different VPN server or switch your proxy settings
2. **Check Network Stability**: Ensure your internet connection is stable
3. **Retry After Network Change**: Wait 30-60 seconds after changing network settings before retrying
4. **Use Alternative Endpoints**: If using custom OpenAI endpoints, verify they're accessible from your network
5. **Docker Network Issues**: Restart Docker Desktop if container networking fails

**Quick Network Test:**
```bash
# Test video platform access
curl -I https://www.youtube.com/

# Test your AI provider endpoint
curl -I https://openrouter.ai

# Test Docker Hub access
docker pull hello-world
```

## 🎯 Supported Languages

### Transcription
- Supports 100+ languages through Whisper
- Automatic language detection
- High accuracy for major languages

### Summary Generation
- English
- Chinese (Simplified)
- Japanese
- Korean
- Spanish
- French
- German
- Portuguese
- Russian
- Arabic
- And more...

## 📈 Performance Tips

- **Hardware Requirements**:
  - Minimum: 4GB RAM, dual-core CPU
  - Recommended: 8GB RAM, quad-core CPU
  - Ideal: 16GB RAM, multi-core CPU, SSD storage

- **Processing Time Estimates**:

  | Video Length | Subtitle Mode | Whisper Mode | Notes |
  |-------------|---------------|--------------|-------|
  | 1 minute | ~5s | 30s–1 min | Subtitle mode needs no audio download |
  | 5 minutes | ~10s | 2–5 min | YouTube auto-captions trigger subtitle mode |
  | 15 minutes | ~15s | 5–15 min | Most YouTube videos support subtitle mode |
  | 30+ minutes | ~20s | 15–60 min | Podcast/audio-only always uses Whisper |

## 🤝 Contributing

We welcome Issues and Pull Requests!

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Powerful video downloading tool
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Efficient Whisper implementation
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [OpenAI](https://openai.com/) - Intelligent text processing API

## 📞 Contact

For questions or suggestions, please submit an Issue or contact Wendy.

---

## 🚀 Try the Full Product — sipsip.ai

This tool is the open-source part of **[sipsip.ai](https://sipsip.ai)**.

The full product goes further:
- 📧 **Daily email briefs** — follow your favorite creators and get an AI-curated digest in your inbox every morning
- ⚡ Transcribe & summarize any video or podcast on demand
- 🌐 Multi-language support across all features

**Free to start** — no credit card required.

➡️ [sipsip.ai](https://sipsip.ai)

---

## ⭐ Star History

If you find this project helpful, please consider giving it a star!
