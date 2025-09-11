# AI影片轉錄器 Docker映像 - 支援 GPU 和 CPU 模式
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 設定非互動模式和更快的 apt 映像
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

# 建立 python 符號連結
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# 安裝 PyTorch (CPU版本，GPU版本會在執行時自動偵測)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 複製requirements.txt並安裝Python依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 建立暫存目錄並設定權限
RUN mkdir -p /app/temp && \
    chmod 755 /app/temp

# 設定環境變數
ENV HOST=0.0.0.0 \
    PORT=8893 \
    WHISPER_MODEL_SIZE=base \
    PYTHONUNBUFFERED=1

# 開放連接埠
EXPOSE 8893

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8893/ || exit 1

# 啟動命令
CMD ["python3", "start.py", "--prod"]