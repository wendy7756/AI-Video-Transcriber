# AI视频转录器 Docker镜像 — Python 与本地推荐环境对齐（3.12），依赖与 requirements.txt 一致
FROM python:3.12-slim-bookworm

WORKDIR /app

# 系统依赖（FFmpeg：链接下载与本地上传转码；deno：yt-dlp 的 JS 挑战求解器运行时）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    ca-certificates \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 安装 Deno —— yt-dlp 解 YouTube `n` 参数（player.js 中的 JS 挑战）需要 JS 运行时。
# 没装的话 yt-dlp 只能返回 storyboard 等少量格式，bestaudio/best 会报
# “Requested format is not available”。
# 安装到 /usr/local/bin 让所有用户可用，并通过 DENO_DIR 集中缓存。
ENV DENO_DIR=/opt/deno/cache
RUN curl -fsSL https://deno.land/install.sh \
    | DENO_INSTALL=/usr/local sh -s -- -y --no-modify-path \
    && deno --version

# 先升级 pip，再按 requirements 安装（与本地 `pip install -r requirements.txt` 行为一致，取满足下界的最新版）
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建临时目录
RUN mkdir -p temp

# 设置环境变量
ENV HOST=0.0.0.0
ENV PORT=8000
ENV WHISPER_MODEL_SIZE=base
ENV UPLOAD_MAX_MB=200

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 启动命令
CMD ["python3", "start.py", "--prod"]
