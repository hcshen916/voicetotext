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

# 設定 Streamlit 頁面配置
st.set_page_config(
    page_title="語音轉文字",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 設定上傳檔案大小限制提示
st.title("語音轉文字")
st.markdown("### 支援上傳最大檔案大小：1GB")
st.markdown("注意：處理大型檔案可能需要更長時間，請耐心等待")

@st.cache_data
def process_audio_segment(_segment_data, segment_index, total_segments):
    """處理音頻段落並進行轉錄，使用快取以提高效能"""
    # 使用 try-finally 確保資源釋放
    segment_filename = os.path.join(output_dir, f'segment_{segment_index}.mp3')
    try:
        # 導出段落到臨時檔案
        _segment_data.export(segment_filename, format="mp3")
        
        # 使用 OpenAI Whisper API 進行轉錄
        with open(segment_filename, "rb") as audio_file:
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    return response.text
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        return f"轉錄失敗：{str(e)}"
                    else:
                        time.sleep(2)  # 等待後重試
                        audio_file.seek(0)  # 重置檔案指標
    finally:
        # 確保處理完後刪除臨時檔案
        if os.path.exists(segment_filename):
            try:
                os.remove(segment_filename)
            except Exception:
                pass
    return "處理失敗"

uploaded_file = st.file_uploader("上傳音檔", type=["mp3", "wav", "ogg", "flac", "aac", "m4a", "wma"])

if uploaded_file is not None:
    # 顯示處理中提示
    with st.spinner("正在處理音檔，請稍候..."):
        # 過濾檔名中的特殊字元
        safe_filename = ''.join(c for c in uploaded_file.name if c.isalnum() or c in ('_', '-', '.'))
        file_path = os.path.join(output_dir, safe_filename)
        
        # 確保臨時目錄存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 直接保存到臨時目錄，避免使用主工作目錄
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            # 使用檔案路徑直接載入，而不是先讀入記憶體
            audio = AudioSegment.from_file(file_path)
            
            # 顯示音檔資訊
            duration_seconds = len(audio) / 1000
            st.success(f"音檔匯入成功！長度: {int(duration_seconds // 60)} 分 {int(duration_seconds % 60)} 秒")
            
            # 設置進度顯示
            progress_text = st.empty()
            progress_bar = st.progress(0)
            segments_results = st.container()
            
            # 分割音檔並轉錄
            transcription = []
            total_length_ms = len(audio)
            total_segments = (total_length_ms + max_segment_ms - 1) // max_segment_ms
            
            for i in range(int(total_segments)):
                progress = (i + 1) / total_segments
                progress_bar.progress(progress)
                progress_text.text(f'處理進度: {int(progress * 100)}% (段落 {i+1}/{int(total_segments)})')
                
                # 處理音頻段落
                start_ms = i * max_segment_ms
                end_ms = min((i + 1) * max_segment_ms, total_length_ms)
                segment = audio[start_ms:end_ms]
                
                # 轉錄並顯示結果
                with segments_results.container():
                    with st.spinner(f'正在轉錄第 {i+1}/{int(total_segments)} 段...'):
                        transcription_text = process_audio_segment(segment, i, total_segments)
                        transcription.append(transcription_text)
                        st.write(f"**第 {i+1} 段轉錄結果：**")
                        st.write(transcription_text)
                
                # 釋放記憶體
                del segment
            
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
            
        except Exception as e:
            st.error(f"處理音檔失敗：{str(e)}")
        finally:
            # 清理臨時文件
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # 清理其他可能剩餘的臨時文件
                for filename in os.listdir(output_dir):
                    if filename.startswith('segment_'):
                        os.remove(os.path.join(output_dir, filename))
            except Exception as e:
                st.warning(f"清理臨時檔案時發生錯誤：{str(e)}")