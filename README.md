# 語音轉文字

這是一個使用 Streamlit 和 OpenAI Whisper 開發的極簡工具，可將音訊檔案轉換為文字，提供以使用量計價的方案。

## 功能

- 支援多種音訊格式（mp3、wav、ogg、flac、aac、m4a、wma）
- 自動分割較長音訊檔案處理轉錄文字
- 使用 OpenAI Whisper API 執行語音轉文字
- 提供完整下載轉錄結果 .txt

## 系統需求

- Python 3.7 或更高版本
- FFmpeg（用於音訊處理）

## 安裝

1. 安裝必要的 Python 套件：

```bash
pip install -r requirements.txt
```

2. 安裝 FFmpeg：

**Windows：**
- 從 [FFmpeg 官網](https://ffmpeg.org/download.html) 下載 FFmpeg
- 解壓縮後將 bin 目錄添加到系統環境變數 PATH 中，或在 .env 檔案中設定路徑

**macOS：**
```bash
brew install ffmpeg
```

**Linux：**
```bash
sudo apt-get update && sudo apt-get install ffmpeg
```

## 設定

1. 建立 `.env` 檔案並設定 OpenAI API Key；如有需要請設定 FFmpeg PATH：

```
OPENAI_API_KEY=your_openai_api_key

# FFmpeg PATH 設定（可另行設定，如果 FFmpeg 不在系統 PATH 中）
# FFMPEG_PATH=/path/to/ffmpeg
# FFPROBE_PATH=/path/to/ffprobe
```

## 使用方法

1. 啟動：

```bash
streamlit run app.py
```

2. 使用瀏覽器瀏覽 Streamlit App

3. 上傳音訊檔案並等待轉錄完成，較長的音檔會分段

4. 下載轉錄結果

## 部署到 Streamlit Cloud

該專案可自動部署到 Streamlit Cloud 。

### 首次部署步驟

1. 在 GitHub 上建立一個新的公開 Repo

```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/yourusername/voicetotext.git
git push -u origin main
```

3. 登入 [Streamlit Community Cloud](https://streamlit.io/cloud)

4. "New app"

5. 連接 GitHub Repo 並設定部署選項：
   - 分支：main
   - 主程式：app.py
   - 進階設定：
     - 設定 `OPENAI_API_KEY`

6. "Deploy"

完成上述步驟後，每次變更 GitHub main，應用程式會自動部署更新。

## 疑難排解

### FFmpeg 問題

如果遇到 FFmpeg 相關錯誤（也可能造成 403 錯誤），請確認：

1. FFmpeg 已正確安裝在您的系統上
2. 執行 `ffmpeg -version` 和 `ffprobe -version` 確認
3. 也可在 `.env` 檔案中設定 `FFMPEG_PATH` 和 `FFPROBE_PATH`

### API Key

設定 OpenAI API Key 在 `.env` 檔案中或在部署的環境變數中。

## 授權

MIT 