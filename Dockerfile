# AI影片轉錄器 Docker鏡像 - 支援 GPU 和 CPU 模式
FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# 設置非互動模式和更快的 apt 鏡像
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    gcc \
    g++ \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 創建 python 符號連結
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# 安裝 PyTorch (CPU版本，GPU版本會在運行時自動檢測)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 複製requirements.txt並安裝Python依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 創建臨時目錄並設置權限
RUN mkdir -p /app/temp && \
    chmod 755 /app/temp

# 設置環境變數
ENV HOST=0.0.0.0 \
    PORT=8893 \
    WHISPER_MODEL_SIZE=base \
    PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8893

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8893/ || exit 1

# 啟動命令
CMD ["python3", "start.py", "--prod"]
