# AI视频转录器 Docker镜像 - 使用更小的Alpine镜像
FROM python:3.9-alpine

# 设置工作目录
WORKDIR /app

# 安装系统依赖 - Alpine使用apk包管理器
RUN apk update && apk add --no-cache \
    ffmpeg \
    curl \
    gcc \
    musl-dev \
    python3-dev

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建临时目录
RUN mkdir -p temp

# 设置环境变量
ENV HOST=0.0.0.0
ENV PORT=8000
ENV WHISPER_MODEL_SIZE=base

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 启动命令
CMD ["python3", "start.py", "--prod"]
