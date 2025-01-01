# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 19:02:27 2024

@author: user
"""
import logging 
import requests
import datetime
import os
import io
import zipfile
from pydub import AudioSegment



class RPSGame:
    RPS_MAP = {
        "剪刀": {"beats": "布", "image_url": "static/rps/scissors.png"},
        "石頭": {"beats": "剪刀", "image_url": "static/rps/rock.png"},
        "布": {"beats": "石頭", "image_url": "static/rps/paper.png"}
    }
    @staticmethod
    def determine_winner(user_choice, bot_choice):
        if user_choice == bot_choice:
            return "平手"
        elif RPSGame.RPS_MAP[user_choice]["beats"] == bot_choice:
            return "你贏了！"
        else:
            return "你輸了！"



def setup_ffmpeg():
    # 動態下載 ffmpeg
    ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.zip"
    ffmpeg_zip = "/tmp/ffmpeg.zip"
    ffmpeg_dir = "/tmp/ffmpeg"

    if not os.path.exists(ffmpeg_dir):
        response = requests.get(ffmpeg_url, stream=True)
        with open(ffmpeg_zip, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        
        # 解壓文件
        with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
    
    ffmpeg_path = os.path.join(ffmpeg_dir, "bin", "ffmpeg")
    ffprobe_path = os.path.join(ffmpeg_dir, "bin", "ffprobe")

    os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
    return ffmpeg_path, ffprobe_path

def get_audio_duration(url):
    """
    計算遠程音頻文件的時長（毫秒）。

    :param url: 音頻文件的 URL
    :return: 時長（毫秒）
    """
    try:
        # 設置 ffmpeg 和 ffprobe
        ffmpeg_path, ffprobe_path = setup_ffmpeg()
        AudioSegment.ffmpeg = ffmpeg_path
        AudioSegment.ffprobe = ffprobe_path

        # 發送 GET 請求下載音頻文件到內存
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # 嘗試自動檢測音頻格式
        content_type = response.headers.get("Content-Type")
        if not content_type:
            raise ValueError("無法檢測音頻文件的 Content-Type")
        
        # 映射 Content-Type 到 Pydub 格式
        format_map = {
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/ogg": "ogg",
            "audio/aac": "aac"
        }
        file_format = format_map.get(content_type)
        if not file_format:
            raise ValueError(f"不支持的音頻格式: {content_type}")

        # 使用 pydub 解析音頻文件
        audio = AudioSegment.from_file(io.BytesIO(response.content), format=file_format)
        duration_ms = len(audio)  # 時長以毫秒計算

        if duration_ms > 0:
            return duration_ms
        else:
            raise ValueError("計算的時長為非正數")
    except requests.exceptions.RequestException as re:
        logging.error(f"HTTP 請求錯誤：{re}")
    except ValueError as ve:
        logging.error(f"無效的音頻文件：{ve}")
    except Exception as e:
        logging.error(f"無法計算音頻時長：{e}")

    # 預設值，作為最後的保險
    logging.info("返回預設音頻時長：10000 毫秒")
    return 10000  # 預設為 10 秒


def search_youtube_this_year(api_key, query, max_results=10):
    # 定義今年的時間範圍
    current_year = datetime.datetime.now().year-1 #原本 current_year = datetime.datetime.now().year(調整原因今年剛開始還沒有結果)
    start_date = f"{current_year}-01-01T00:00:00Z"  # 今年的開始時間
    end_date = f"{current_year}-12-31T23:59:59Z"    # 今年的結束時間

    # YouTube Data API URL 和請求參數
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "videoCategoryId": "10",  # 音樂類別
        "order": "viewCount",    # 按播放量排序
        "key": api_key,
        "maxResults": max_results,
        "publishedAfter": start_date,
        "publishedBefore": end_date
    }

    # 發送請求
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])

        # 提取每個視頻的標題和 URL
        results = []
        for item in items:
            video_id = item["id"].get("videoId")
            title = item["snippet"].get("title")
            if video_id and title:
                results.append({
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                })

        return results
    else:
        raise RuntimeError(f"Failed to fetch YouTube data: {response.status_code}")