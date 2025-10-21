<div align="center">

# AI Video Transcriber

English | [中文](README_ZH.md)

An AI-powered video transcription and summarization tool that supports multiple video platforms including YouTube, Tiktok, Bilibili, and 30+ platforms, **as well as local video file uploads.**

![Interface](en-video.png)

</div>

## ✨ Features

- 🎥 **Multi-Platform Support**: Works with YouTube, Tiktok, Bilibili, and 30+ more. **Supports direct upload of local video files.**
- 🗣️ **Intelligent Transcription**: High-accuracy speech-to-text using Faster-Whisper
- 🤖 **AI Text Optimization**: Automatic typo correction, sentence completion, and intelligent paragraphing
- 🌍 **Multi-Language Summaries**: Generate intelligent summaries in multiple languages
- ⚡ **Real-Time Progress**: Live progress tracking and status updates
- ⚙️ **Conditional Translation**: When the selected summary language differs from the detected transcript language, the system auto-translates with LLM (OpenAI/Ollama)
- 📱 **Mobile-Friendly**: Perfect support for mobile devices
- ✂️ **Long Video Segmentation**: Automatically segments long videos into 20-minute chunks for processing, ensuring efficient handling of extended content.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg
- Optional: OpenAI API key (for OpenAI AI features) or Ollama service (for local LLM features)

### Installation

#### Method 1: Automatic Installation

```bash
# Clone the repository
git clone https://github.com/tiandaoyuxi/AI-Video-Transcriber.git
cd AI-Video-Transcriber

# Run installation script
chmod +x install.sh
./install.sh
```

#### Method 2: Docker

```bash
# Clone the repository
git clone https://github.com/tiandaoyuxi/AI-Video-Transcriber.git
cd AI-Video-Transcriber

# Using Docker Compose (easiest)
cp .env.example .env
# Edit .env file and set your OPENAI_API_KEY or OLLAMA_BASE_URL/OLLAMA_MODEL_NAME
docker-compose up -d

# Or using Docker directly
docker build -t ai-video-transcriber .
docker run -p 8000:8000 --env-file .env ai-video-transcriber
```

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

3. **Configure Environment Variables**
```bash
# For OpenAI API
export OPENAI_API_KEY="your_openai_api_key_here"
# Optional: only if you use a custom OpenAI-compatible gateway
export OPENAI_BASE_URL="https://oneapi.basevec.com/v1"
export OPENAI_MODEL_NAME="gpt-4o" # Optional, default is gpt-4o

# For Ollama (prioritized if set)
export OLLAMA_BASE_URL="http://xxx.xxx.xxx.xxx:xxxxx/v1" # Your Ollama service address
export OLLAMA_MODEL_NAME="xxxxx:xb" # Your preferred Ollama model
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
# Example for OpenAI
export OPENAI_API_KEY=your_api_key_here
# export OPENAI_BASE_URL=https://oneapi.basevec.com/v1   # if using a custom endpoint
# export OPENAI_MODEL_NAME="gpt-4o"

# Example for Ollama
export OLLAMA_BASE_URL="http://xxx.xxx.xxx.xxx:xxxxx/v1"
export OLLAMA_MODEL_NAME="xxxxx:xb"

python3 start.py --prod
```

## 📖 Usage Guide

1. **Input Video**: Choose between **pasting a video URL** (from YouTube, Bilibili, or other supported platforms) or **uploading a local video file**.
2. **Select Summary Language**: Choose the language for the generated summary
3. **Start Processing**: Click the "Start" button
4. **Monitor Progress**: Watch real-time progress through multiple stages:
   - Video download/upload and parsing
   - Audio transcription with Faster-Whisper
   - AI-powered transcript optimization (typo correction, sentence completion, intelligent paragraphing)
   - AI summary generation in selected language
   - **Note**: For long videos, the system automatically segments them into 20-minute chunks for processing.
5. **View Results**: Review the optimized transcript and intelligent summary
   - If transcript language ≠ selected summary language, a third tab “Translation” is shown containing a translated transcript
6. **Download Files**: Click download buttons to save Markdown-formatted files (Transcript / Translation / Summary)

## 🛠️ Technical Architecture

### Backend Stack
- **FastAPI**: Modern Python web framework
- **yt-dlp**: Video downloading and processing
- **Faster-Whisper**: Efficient speech transcription
- **LLM API (OpenAI/Ollama)**: Intelligent text summarization and translation

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
│   └── translator.py       # Translation module
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
| `OPENAI_API_KEY` | OpenAI API key (used if Ollama is not configured) | - | No |
| `OPENAI_BASE_URL` | Custom OpenAI-compatible API endpoint (e.g., for self-hosted LLMs or proxies) | `https://api.openai.com/v1` | No |
| `OPENAI_MODEL_NAME` | OpenAI model name (e.g., `gpt-4o`, `gpt-3.5-turbo`) | `gpt-4o` | No |
| `OLLAMA_BASE_URL` | Ollama service API endpoint (e.g., `http://localhost:11434/v1`) | - | No (but recommended for local LLM) |
| `OLLAMA_MODEL_NAME` | Ollama model name (e.g., `llama3`, `xxxxx:xb`) | - | No (but recommended for local LLM) |
| `HOST` | Server address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `WHISPER_MODEL_SIZE` | Whisper model size | `base` | No |

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

### Q: What if the AI optimization features are unavailable?
A: Both transcript optimization and summary generation require either an OpenAI API key or a configured Ollama service. Without either, the system provides the raw transcript from Whisper and a simplified summary.

### Q: I get HTTP 500 errors when starting/using the service. Why?
A: In most cases this is an environment configuration issue rather than a code bug. Please check:
- Ensure a virtualenv is activated: `source venv/bin/activate`
- Install deps inside the venv: `pip install -r requirements.txt`
- Set `OPENAI_API_KEY` (if using OpenAI API) or `OLLAMA_BASE_URL`/`OLLAMA_MODEL_NAME` (if using Ollama)
- If using a custom gateway, ensure `OPENAI_BASE_URL` or `OLLAMA_BASE_URL` is set correctly and ensure network access
- Install FFmpeg: `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Debian/Ubuntu)
- If port 8000 is occupied, stop the old process or change `PORT`

### Q: How to handle long videos?
A: The system automatically segments videos longer than 20 minutes into 20-minute chunks for processing. This helps mitigate issues with LLM context windows and API timeouts. For very long videos, consider using smaller Whisper models.

### Q: How to use Docker for deployment?
A: Docker provides the easiest deployment method:

**Prerequisites:**
- Install Docker Desktop from https://www.docker.com/products/docker-desktop/
- Ensure Docker service is running

**Quick Start:**
```bash
# Clone and setup
git clone https://github.com/tiandaoyuxi/AI-Video-Transcriber.git
cd AI-Video-Transcriber
cp .env.example .env
# Edit .env file to set your OPENAI_API_KEY or OLLAMA_BASE_URL/OLLAMA_MODEL_NAME

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
- **Container won't start**: Verify .env file exists and contains valid API keys/Ollama config. Check container logs (`docker logs <container_id>`).

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
- LLM API calls return connection timeout or DNS resolution failures
- Docker image pull fails or is extremely slow

**Solutions:**
1. **Switch VPN/Proxy**: Try connecting to a different VPN server or switch your proxy settings
2. **Check Network Stability**: Ensure your internet connection is stable
3. **Retry After Network Change**: Wait 30-60 seconds after changing network settings before retrying
4. **Use Alternative Endpoints**: If using custom LLM endpoints, verify they're accessible from your network
5. **Docker Network Issues**: Restart Docker Desktop if container networking fails

**Quick Network Test:**
```bash
# Test video platform access
curl -I https://www.youtube.com/

# Test LLM API access (replace with your endpoint)
curl -I http://xxx.xxx.xxx.xxx:xxxxx/v1

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
  | Video Length | Estimated Time | Notes |
  |-------------|----------------|-------|
  | 1 minute | 30s-1 minute | Depends on network and hardware |
  | 5 minutes | 2-5 minutes | Recommended for first-time testing |
  | 15 minutes | 5-15 minutes | Suitable for regular use |
  | >20 minutes | Variable | Automatically segmented into 20-minute chunks. Total time depends on number of chunks and LLM processing speed. |

## 🤝 Contributing

We welcome Issues and Pull Requests!

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## Acknowledgments
- [wendy7756]https://github.com/wendy7756/AI-Video-Transcriber
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Powerful video downloading tool
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Efficient Whisper implementation
- [LLM API (OpenAI/Ollama)](https://openai.com/) - Intelligent text summarization and translation

## 📞 Contact

For questions or suggestions, please submit an Issue or contact Wendy.

## ⭐ Star History

If you find this project helpful, please consider giving it a star!
