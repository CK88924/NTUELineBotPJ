# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 19:02:27 2024

@author: user
"""
import requests
import datetime
import io
import logging
from mutagen import File

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
def get_audio_duration_with_mutagen(url: str) -> int:
    """
    從指定的 URL 讀取音檔 metadata 並計算時長（以毫秒為單位返回）。
    """
    try:
        # 下載音檔
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # 將音檔內容讀取到內存
        audio_data = response.content

        # 使用 mutagen 解析音檔
        audio_file = File(io.BytesIO(audio_data))
        if audio_file is None or not hasattr(audio_file.info, 'length'):
            logging.warning(f"無法從 URL 解析時長：{url}")
            return 0

        # 將時長轉換為毫秒並返回整數
        duration_in_milliseconds = int(audio_file.info.length * 1000)  # 時長轉換為毫秒
        logging.info(f"成功計算音檔時長：{duration_in_milliseconds} 毫秒。")
        return duration_in_milliseconds
    except Exception as e:
        logging.error(f"無法計算音檔時長：{e}")
        return 0
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