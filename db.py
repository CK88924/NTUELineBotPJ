# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 17:03:20 2024

@author: user
"""

import os
import logging
import base64
import json
import random as rand
from firebase_admin import credentials, initialize_app, storage

firebase_app = None
def init_firebase_storage():
    """
    初始化 Firebase Storage 並返回 Bucket 客戶端。
    """
    global firebase_app  # 確保 firebase_app 是全局變數
    if firebase_app is None:
        credentials_content = os.getenv("FIREBASE_CREDENTIALS")
        if not credentials_content:
            raise ValueError("未找到 FIREBASE_CREDENTIALS 環境變數")
        
        try:
            # 解碼憑證內容
            decoded_credentials = base64.b64decode(credentials_content).decode("utf-8")
            credentials_info = json.loads(decoded_credentials)
            cred = credentials.Certificate(credentials_info)

            # 從環境變數獲取存儲桶名稱
            bucket_name = os.getenv("BUCKET_NAME")
            if not bucket_name:
                raise ValueError("未設置 BUCKET_NAME 環境變數")
            
            # 初始化 Firebase Admin SDK
            firebase_app = initialize_app(cred, {"storageBucket": bucket_name})
            logging.info(f"Firebase 已成功初始化，存儲桶：{bucket_name}")
        except Exception as e:
            logging.error(f"初始化 Firebase 客戶端失敗：{e}")
            raise RuntimeError(f"初始化 Firebase 客戶端失敗：{e}")
    
    # 返回 Storage Bucket 客戶端
    try:
        bucket = storage.bucket()
        return bucket
    except Exception as e:
        logging.error(f"獲取 Firebase Storage Bucket 失敗：{e}")
        raise RuntimeError(f"獲取 Firebase Storage Bucket 失敗：{e}")



def list_blob_names(bucket, prefix: str = "") -> list:
    """
    列出指定 Bucket 中的所有 Blob 名稱。
    """
    try:
        blobs = bucket.list_blobs(prefix=prefix)
        blob_names = [blob.name for blob in blobs]
        logging.info(f"從 Bucket 中檢索到 {len(blob_names)} 個 Blob，前綴為 '{prefix}'。")
        return blob_names
    except Exception as e:
        logging.error(f"列出 Blobs 失敗：{e}")
        raise RuntimeError(f"列出 Blobs 失敗：{e}")


def get_signed_url(bucket, blob_name: str, expiration: int = 3600) -> str:
    """
    為指定的 Blob 生成簽名 URL。
    """
    try:
        blob = bucket.blob(blob_name)
        url = blob.generate_signed_url(version="v4", expiration=expiration, method="GET")
        logging.info(f"成功為 Blob '{blob_name}' 生成簽名 URL。")
        return url
    except Exception as e:
        logging.error(f"生成簽名 URL 失敗：{e}")
        raise RuntimeError(f"生成簽名 URL 失敗：{e}")


def generate_signed_urls(bucket, blob_names: list, expiration: int = 3600) -> dict:
    """
    為指定的 Blob 名稱列表生成簽名 URL。
    """
    try:
        signed_urls_map = {}
        for blob_name in blob_names:
            base_name = blob_name.split('/')[-1].rsplit('.', 1)[0]
            
            if not base_name:
                logging.warning(f"Blob {blob_name} 名稱為空或無效，跳過。")
                continue
            
            try:
                signed_url = get_signed_url(bucket, blob_name, expiration)
                if '-' in base_name:
                    refined_name = base_name.split('-', 1)[-1]
                    signed_urls_map[refined_name] = signed_url
                else:
                    signed_urls_map[base_name] = signed_url
            except Exception as e:
                logging.warning(f"生成 {blob_name} 的簽名 URL 失敗，跳過。原因：{e}")
        
        return signed_urls_map
    except Exception as e:
        logging.error(f"批量生成簽名 URL 失敗：{e}")
        raise RuntimeError(f"批量生成簽名 URL 失敗：{e}")
        
def generate_signed_urls_with_groups(bucket, blob_names: list, expiration: int = 3600):
    """
    為指定的 Blob 名稱列表生成簽名 URL，並分組圖片作為遊戲答案。
    """
    try:
        if not blob_names:
            raise ValueError("Blob 名稱列表為空，無法生成簽名 URL。")

        # 分組容器
        grouped_urls = {}

        for blob_name in blob_names:
            if not blob_name:
                logging.warning("Blob 名稱無效或為空，跳過。")
                continue

            base_name = blob_name.split('/')[-1].rsplit('.', 1)[0]
            if not base_name:
                logging.warning(f"Blob {blob_name} 名稱提取後為空，跳過。")
                continue

            try:
                signed_url = get_signed_url(bucket, blob_name, expiration)
                
                # 分組邏輯，使用 "-" 前部分作為組名
                group_key = base_name.split('-', 1)[0] if '-' in base_name else base_name
                
                # 初始化分組
                if group_key not in grouped_urls:
                    grouped_urls[group_key] = []

                grouped_urls[group_key].append(signed_url)

            except Exception as e:
                logging.warning(f"生成 {blob_name} 的簽名 URL 失敗，跳過。原因：{e}")

        # 檢查分組結果
        if not grouped_urls:
            raise ValueError("沒有有效的圖片組可用！")

        # 隨機選擇一組作為答案
        selected_group = rand.choice(list(grouped_urls.items()))
        group_name, urls = selected_group

        # 生成模板所需數據結構
        columns = [
            {
                "imageUrl": url,
                "action": {
                    "type": "message",
                    "label": "猜答案",
                    "text": group_name
                }
            }
            for url in urls
        ]

        return {"group_name": group_name, "columns": columns}

    except Exception as e:
        logging.error(f"批量生成簽名 URL 並分組失敗：{e}")
        raise RuntimeError("批量生成簽名 URL 並分組失敗。")

