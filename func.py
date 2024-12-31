# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 19:02:27 2024

@author: user
"""
import requests
import datetime

def search_youtube_this_year(api_key, query, max_results=10):
    # 定義今年的時間範圍
    current_year = datetime.datetime.now().year
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
