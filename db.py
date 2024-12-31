# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 17:03:20 2024

@author: user
"""

from firebase_admin import credentials, initialize_app, _apps
from google.cloud import storage
import os 
import base64
import json
import requests
import logging

def init_firebase_storage():
    credentials_content = os.getenv("FIREBASE_CREDENTIALS")
    if not credentials_content:
        raise ValueError("未找到 FIREBASE_CREDENTIALS 環境變數")

    try:
        # 解碼憑證內容
        decoded_credentials = base64.b64decode(credentials_content).decode("utf-8")
        credentials_info = json.loads(decoded_credentials)

        # 檢查 Firebase 是否已經初始化
        if not _apps:
            # 使用內存中的憑證初始化 Firebase
            cred = credentials.Certificate(credentials_info)
            initialize_app(cred)
            logging.info("Firebase 已成功初始化，無需寫入檔案。")
        else:
            logging.info("Firebase 已經初始化過。")

        # 返回 Storage 客戶端
        return storage.Client(credentials=credentials_info)
    except Exception as e:
        logging.error(f"初始化 Firebase Storage 客戶端失敗：{e}")
        raise RuntimeError(f"初始化 Firebase Storage 客戶端失敗：{e}")

    
        

def list_blob_names(client: storage.Client, bucket_name: str, prefix: str = "") -> list:
    try:
        # Get bucket and list blobs
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        blob_names = [blob.name for blob in blobs]
        logging.info(f"Retrieved {len(blob_names)} blobs from bucket '{bucket_name}' with prefix '{prefix}'.")
        return blob_names
    except Exception as e:
        logging.error(f"Failed to list blobs: {e}")
        raise RuntimeError(f"Failed to list blobs: {e}")

def get_signed_url(client: storage.Client, bucket_name: str, blob_name: str, expiration: int = 3600) -> str:
    try:
        # Get bucket and blob
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Generate signed URL
        url = blob.generate_signed_url(version="v4", expiration=expiration, method="GET")
        logging.info("Signed URL generated successfully.")
        return url
    except Exception as e:
        logging.error(f"Failed to generate signed URL: {e}")
        raise RuntimeError(f"Failed to generate signed URL: {e}")
        
        
def generate_signed_urls(client: storage.Client, bucket_name: str, blob_names: list, expiration: int = 3600) -> dict:
    """
    為指定檔案名稱生成簽名 URL 並映射其名稱。

    Args:
        client (storage.Client): GCS 客戶端。
        bucket_name (str): 存儲桶名稱。
        blob_names (list): 檔案名稱列表。
        expiration (int): 簽名 URL 過期時間，單位為秒，預設 3600 秒。

    Returns:
        dict: 包含有效檔案名稱與其對應簽名 URL 的字典。

    Raises:
        RuntimeError: 如果生成簽名 URL 失敗。
    """
    try:
        signed_urls_map = {}
        for blob_name in blob_names:
            # 提取名稱部分作為鍵 (去掉資料夾與副檔名)
            base_name = blob_name.split('/')[-1].rsplit('.', 1)[0]
            
            # 如果名稱為空或無效，跳過該項
            if not base_name:
                logging.warning(f"Blob {blob_name} has an empty or invalid name. Skipping.")
                continue
            
            # 獲取簽名 URL
            signed_url = get_signed_url(client, bucket_name, blob_name, expiration)
            if not signed_url:
                logging.warning(f"Signed URL for blob {blob_name} is empty. Skipping.")
                continue
            
            # 如果名稱包含 "-", 只保留去掉前綴的部分
            if '-' in base_name:
                refined_name = base_name.split('-', 1)[-1]
                signed_urls_map[refined_name] = signed_url
            else:
                signed_urls_map[base_name] = signed_url
        
        return signed_urls_map
    except Exception as e:
        logging.error(f"Failed to generate signed URLs: {e}")
        raise RuntimeError(f"Failed to generate signed URLs: {e}")




  
