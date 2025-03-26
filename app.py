import streamlit as st
import os
import time
from pydub import AudioSegment
from openai import OpenAI
from io import BytesIO
import dotenv
import platform
import shutil
import subprocess

try:
    dotenv.load_dotenv()
except:
    pass

# 設定 OpenAI API 金鑰
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    st.error("找不到 OpenAI API 金鑰，請確認環境變數或 .env 檔案設定")
    st.stop()

# 設定 ffmpeg 路徑
def find_ffmpeg():
    # 嘗試從環境變數中獲取 ffmpeg 路徑
    ffmpeg_path = os.getenv("FFMPEG_PATH")
    ffprobe_path = os.getenv("FFPROBE_PATH")
    
    # 如果環境變數已設置，則直接使用
    if ffmpeg_path and os.path.exists(ffmpeg_path) and ffprobe_path and os.path.exists(ffprobe_path):
        return ffmpeg_path, ffprobe_path
    
    # 嘗試在系統路徑中查找 ffmpeg
    ffmpeg_command = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    ffprobe_command = "ffprobe.exe" if platform.system() == "Windows" else "ffprobe"
    
    ffmpeg_in_path = shutil.which(ffmpeg_command)
    ffprobe_in_path = shutil.which(ffprobe_command)
    
    if ffmpeg_in_path and ffprobe_in_path:
        return ffmpeg_in_path, ffprobe_in_path
    
    # 如果是 Windows，嘗試常見安裝路徑
    if platform.system() == "Windows":
        common_paths = [
            r"D:\ffmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
        ]
        common_ffprobe_paths = [
            r"D:\ffmpeg\bin\ffprobe.exe",
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe"
        ]
        
        for i, path in enumerate(common_paths):
            if os.path.exists(path) and os.path.exists(common_ffprobe_paths[i]):
                return path, common_ffprobe_paths[i]
    
    return None, None

# 取得 ffmpeg 路徑
ffmpeg_path, ffprobe_path = find_ffmpeg()

if ffmpeg_path and ffprobe_path:
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffprobe = ffprobe_path
else:
    st.error("""
    找不到 ffmpeg 和 ffprobe，請確保已安裝。
    
    安裝方法：
    - Windows: 下載 ffmpeg 並添加到系統路徑或設定環境變數 FFMPEG_PATH 和 FFPROBE_PATH
    - macOS: 使用 brew install ffmpeg
    - Linux: 使用 apt-get install ffmpeg 或對應的包管理器命令
    
    或者在環境變數中設定 FFMPEG_PATH 和 FFPROBE_PATH 指向 ffmpeg 和 ffprobe 的完整路徑
    """)
    st.stop()

# 設定音檔分段長度和輸出目錄
max_segment_ms = 10 * 60 * 1000  # 10分鐘
output_dir = "temp_segments"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

st.title("語音轉文字")
uploaded_file = st.file_uploader("上傳音檔", type=["mp3", "wav", "ogg", "flac", "aac", "m4a", "wma"])

if uploaded_file is not None:
    # 過濾檔名中的特殊字元
    safe_filename = ''.join(c for c in uploaded_file.name if c.isalnum() or c in ('_', '-', '.'))
    file_path = os.path.join(os.getcwd(), safe_filename)

    # (1) 保存檔案到硬碟
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    time.sleep(0.5)  # 稍等避免還未寫完

    try:
        # (2) 將檔案讀到記憶體後立刻刪檔 ############
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        os.remove(file_path)  # 立即刪除硬碟上的原始檔案

        # (3) 以 BytesIO 形式載入
        audio = AudioSegment.from_file(BytesIO(file_bytes)) ############
        st.success("音檔匯入成功！")

        # 顯示音檔資訊
        duration_seconds = len(audio) / 1000
        st.info(f"音檔長度: {int(duration_seconds // 60)} 分 {int(duration_seconds % 60)} 秒")

    except Exception as e:
        st.error(f"匯入音檔失敗：{str(e)}")
        # 若匯入失敗且還沒刪檔，就刪除
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as del_e:
                st.error(f"刪除檔案失敗：{str(del_e)}")
        st.stop()

    # 分割音檔並轉錄
    transcription = []
    total_length_ms = len(audio)
    total_segments = (total_length_ms + max_segment_ms - 1) // max_segment_ms
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 確保臨時目錄存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i in range(int(total_segments)):
        progress = (i + 1) / total_segments
        progress_bar.progress(progress)
        status_text.text(f'處理進度: {int(progress * 100)}%')
        
        start_ms = i * max_segment_ms
        end_ms = min((i + 1) * max_segment_ms, total_length_ms)
        segment = audio[start_ms:end_ms]
        segment_filename = os.path.join(output_dir, f'segment_{i}.mp3')
        segment.export(segment_filename, format="mp3")

        # 使用 OpenAI Whisper API 進行轉錄
        with open(segment_filename, "rb") as audio_file:
            with st.spinner(f'正在轉錄第 {i+1}/{int(total_segments)} 段...'):
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        response = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file
                        )
                        transcription_text = response.text
                        transcription.append(transcription_text)
                        st.write(f"**第 {i+1} 段轉錄結果：**")
                        st.write(transcription_text)
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            st.error(f"第 {i+1} 段轉錄失敗：{str(e)}")
                        else:
                            time.sleep(2)  # 等待後重試
                            audio_file.seek(0)  # 重置檔案指標

    # 合併所有轉錄文本
    final_transcription = "\n".join(transcription)
    transcription_filename = safe_filename + '_轉錄結果.txt'

    # 顯示成功訊息並提供下載按鈕
    st.success("所有段落轉錄完成！")
    st.download_button(
        label="下載轉錄文本",
        data=final_transcription,
        file_name=transcription_filename,
        mime="text/plain"
    )

    # 清理臨時文件
    try:
        for i in range(int(total_segments)):
            segment_filename = os.path.join(output_dir, f'segment_{i}.mp3')
            if os.path.exists(segment_filename):
                os.remove(segment_filename)
        if os.path.exists(output_dir) and not os.listdir(output_dir):
            os.rmdir(output_dir)
    except Exception as e:
        st.warning(f"清理臨時檔案時發生錯誤：{str(e)}")