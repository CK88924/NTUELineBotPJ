# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 17:52:19 2024

@author: user
"""

import os
import logging
import requests
import json
import random as rand
import db
import func
from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler,
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    
    TextMessage,
    AudioMessage,
    ImageMessage,
    TemplateMessage,
    
    ImageCarouselTemplate,
    ImageCarouselColumn,
    
    QuickReply,
    QuickReplyItem,
    
    MessagingApiBlob,
   
    )

from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
)

app = Flask(__name__)

#load_dotenv()
configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
client = db.init_firebase_storage (os.getenv("FIREBASE_CREDENTIALS"))
game_states = {}

def create_rich_menu_2():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_blob_api = MessagingApiBlob(api_client)

        # Create rich menu
        headers = {
            'Authorization': 'Bearer ' + os.getenv('CHANNEL_ACCESS_TOKEN'),
            'Content-Type': 'application/json'
        }
        body = {
            "size": {
                "width": 2500,
                "height": 1686
            },
            "selected": True,
            "name": "圖文選單 1",
            "chatBarText": "快捷指令",
            "areas": [
                {
                    "bounds": {
                        "x": 0,
                        "y": 0,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "Drama",
                        "displayText": "劇名"
                    }
                },
                {
                    "bounds": {
                        "x": 834,
                        "y": 0,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "Role",
                        "displayText": "角色"
                    }
                },
                {
                    "bounds": {
                        "x": 1663,
                        "y": 0,
                        "width": 834,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "Music",
                        "displayText": "音樂"
                    }
                },
                {
                    "bounds": {
                        "x": 0,
                        "y": 843,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "Game",
                        "displayText": "小遊戲"
                    }
                },
                {
                    "bounds": {
                        "x": 834,
                        "y": 843,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "Part",
                        "displayText": "角色部位"
                    }
                },
                {
                    "bounds": {
                        "x": 1662,
                        "y": 843,
                        "width": 838,
                        "height": 843
                    },
                    "action": {
                       "type": "postback",
                       "data": "Top",
                       "displayText": "十大音樂"
                    }
                }
            ]
        }

        response = requests.post('https://api.line.me/v2/bot/richmenu', headers=headers, data=json.dumps(body).encode('utf-8'))
        response = response.json()
        print(response)
        rich_menu_id = response["richMenuId"]
        
        # Upload rich menu image
        with open('static/richmenu.jpg', 'rb') as image:
            line_bot_blob_api.set_rich_menu_image(
                rich_menu_id=rich_menu_id,
                body=bytearray(image.read()),
                _headers={'Content-Type': 'image/jpeg'}
            )

        line_bot_api.set_default_rich_menu(rich_menu_id)

create_rich_menu_2()

# 工具函數
def get_game_state(user_id):
    return game_states.get(user_id)

def handle_game_logic(user_message, game_state, user_id, chance):
    correct_answer = game_state["answer"]
    attempts = game_state["attempts"]

    if user_message == correct_answer:
        del game_states[user_id]
        return [TextMessage(text="恭喜答對！遊戲結束。")]

    attempts += 1
    game_state["attempts"] = attempts

    if attempts >= chance:
        del game_states[user_id]
        return [TextMessage(text=f"很可惜，答案是：{correct_answer}。遊戲結束！")]

    return [TextMessage(text=f"答錯了哦！還有 {chance - attempts} 次機會，請再試試看吧！")]

def format_search_results(results):
    message_content = "以下是搜尋結果：\n"
    for i, result in enumerate(results, 1):
        message_content += f"{i}. 影片標題: {result['title']}\n網址: {result['url']}\n\n"
    return message_content

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'



#處理訊息事件
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    logging.info(f"Received message: {user_message} from user: {user_id}")

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        game_state = get_game_state(user_id)

        if not game_state:
            logging.info(f"No game state found for user: {user_id}")
            replys = [
                TextMessage(text="目前沒有進行中的遊戲，請選擇圖文選單中的選項來開始遊戲！")
            ]
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )
            return

        if game_state["game"] == "Top" and game_state["status"] == "waiting_for_keyword":
            # 處理搜尋邏輯
            api_key = os.getenv("YOUTUBE_API_KEY")
            query = user_message

            try:
                search_results = func.search_youtube_this_year(api_key, query, max_results=10)
                # 檢查 search_results 是否為列表
                if not isinstance(search_results, list):
                    logging.error("search_results is not a list")
                    replys = [TextMessage(text="搜尋結果格式有誤，請稍後再試！")]
                    line_bot_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=event.reply_token,
                                messages=replys
                            )
                    )
                    return
                
                if not search_results:
                    replys = [TextMessage(text="很抱歉，未找到相關結果！")]
                else:
                    message_content = format_search_results(search_results)

                    # 超過 2000 字限制處理
                    if len(message_content) > 2000:
                        chunks = [
                            message_content[i:i + 2000]
                            for i in range(0, len(message_content), 2000)
                        ]
                        replys = [TextMessage(text=chunk) for chunk in chunks]
                    else:
                        replys = [TextMessage(text=message_content)]

                # 搜尋成功，清除遊戲狀態
                del game_states[user_id]

            except Exception as e:
                logging.error(f"Error searching YouTube: {e}")
                replys = [TextMessage(text="搜尋時發生錯誤，請稍後再試！")]

            # 回覆訊息
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )
            return

        # 處理其他遊戲邏輯
        replys = handle_game_logic(user_message, game_state, user_id, chance=3)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=replys
            )
        )


#處理Postback事件
@line_handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    user_id = event.source.user_id

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if user_id in game_states:
            replys = [TextMessage(text="您已經在遊戲中，請完成當前遊戲後再開始新遊戲！")]
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )
            return

        bucket_name = os.getenv("BUCKET_NAME")

        if data == 'Drama':
            blob_names = db.list_blob_names(client, bucket_name, "劇名圖片/")
            signed_urls_map = db.generate_signed_urls(client, bucket_name, blob_names)
            if not signed_urls_map:
                replys = [TextMessage(text="目前沒有可用的圖片，請稍後再試！")]
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=replys
                    )
                )
                return

            correct_answer, url = rand.choice(list(signed_urls_map.items()))
            game_states[user_id] = {
                "game": "Drama",
                "attempts": 0,
                "answer": correct_answer
            }
            replys = [
                ImageMessage(original_content_url=url, preview_image_url=url),
                TextMessage(text="請猜測圖片是哪部劇？(並將其打在訊息框)")
            ]

        elif data == 'Role':
            blob_names = db.list_blob_names(client, bucket_name, "角色圖片/")
            signed_urls_map = db.generate_signed_urls(client, bucket_name, blob_names)
            if not signed_urls_map:
                replys = [TextMessage(text="目前沒有可用的圖片，請稍後再試！")]
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=replys
                    )
                )
                return

            correct_answer, url = rand.choice(list(signed_urls_map.items()))
            game_states[user_id] = {
                "game": "Role",
                "attempts": 0,
                "answer": correct_answer
            }
            replys = [
                ImageMessage(original_content_url=url, preview_image_url=url),
                TextMessage(text="請猜測圖片是哪個角色？(並將其打在訊息框)")
            ]

        elif data == 'Top':
            game_states[user_id] = {
                "game": "Top",
                "status": "waiting_for_keyword"
            }
            replys = [TextMessage(text="請輸入想搜尋的影音關鍵詞，我將幫您查詢 YouTube 當年度的熱門影片！")]

        else:
            logging.error(f"Unknown postback data: {data}")
            return

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=replys
            )
        )







if __name__ == "__main__":
    
    # 設定日誌格式
    logging.basicConfig(
        level=logging.INFO,  # 設定最低日誌層級
        format="%(asctime)s [%(levelname)s] %(message)s",  # 自訂格式
        handlers=[
            logging.StreamHandler()  # 輸出到終端
        ]
    )
    
    app.run()