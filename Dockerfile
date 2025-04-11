FROM python:3.10-slim

# 安裝 ffmpeg 和其他系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt (若有) 或直接安裝所需套件
COPY requirements.txt* ./ 
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; \
    else pip install streamlit pydub openai python-dotenv; fi

# 複製 Streamlit 配置目錄
COPY .streamlit/ ./.streamlit/

# 複製應用程式碼
COPY . .

# 設定 ffmpeg 環境變數
ENV FFMPEG_PATH=/usr/bin/ffmpeg
ENV FFPROBE_PATH=/usr/bin/ffprobe

# 設定 Streamlit 環境變數 - 解決 WebSocket 連接問題
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=true
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=1000
ENV STREAMLIT_CLIENT_TOOLBAR_MODE=minimal

# 暴露 Streamlit 的預設端口
EXPOSE 8501

# 啟動 Streamlit 應用，使用指定參數確保可以從容器外訪問
CMD ["streamlit", "run", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableCORS=true", "--server.maxUploadSize=1000", "app.py"] 