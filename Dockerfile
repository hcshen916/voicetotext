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

# 複製應用程式碼
COPY . .

# 設定 ffmpeg 環境變數
ENV FFMPEG_PATH=/usr/bin/ffmpeg
ENV FFPROBE_PATH=/usr/bin/ffprobe

# 暴露 Streamlit 的預設端口
EXPOSE 8501

# 啟動 Streamlit 應用
CMD ["streamlit", "run", "app.py"] 