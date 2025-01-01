# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 19:02:27 2024

@author: user
"""
import logging 
import requests
import datetime
import io
from mutagen.mp3 import MP3


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

def get_audio_duration(url):
    """
    計算遠程音頻文件的時長（毫秒）。

    :param url: 音頻文件的 URL
    :return: 時長（毫秒）
    """
    try:
        # 發送 GET 請求下載音頻文件到內存
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 使用 mutagen.mp3 解析音頻文件元數據
        audio = MP3(io.BytesIO(response.content))
        if audio and audio.info:
            duration_seconds = audio.info.length
            return int(duration_seconds * 1000)  # 轉換為毫秒
        else:
            raise ValueError("無法獲取音頻文件時長信息")
    except Exception as e:
        logging.error(f"無法計算音頻時長：{e}")
        return 0  # 預設為 0 秒


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