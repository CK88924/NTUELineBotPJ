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
    StickerMessage,
    TemplateMessage,
    ImageCarouselTemplate,
    ImageCarouselColumn,
    MessageAction,
    QuickReply,
    QuickReplyItem,
    MessagingApiBlob,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    FollowEvent
)

app = Flask(__name__)

# Load environment variables
#load_dotenv()
configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
game_states = {}
RPS_MAPPING = {
    "剪刀": "scissors",
    "石頭": "rock",
    "布": "paper"
}

# Rich menu creation
def create_rich_menu():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_blob_api = MessagingApiBlob(api_client)

        # Delete all existing rich menus
        try:
            rich_menus = line_bot_api.get_rich_menu_list()
            for menu in rich_menus:
                line_bot_api.delete_rich_menu(menu.rich_menu_id)
                print(f"Deleted rich menu: {menu.rich_menu_id}")
        except Exception as e:
            print(f"Error fetching or deleting rich menus: {e}")

        # Create rich menu
        headers = {
            'Authorization': 'Bearer ' + os.getenv('CHANNEL_ACCESS_TOKEN'),
            'Content-Type': 'application/json'
        }
        body = {
            "size": {"width": 2500, "height": 1686},
            "selected": True,
            "name": "圖文選單",
            "chatBarText": "快捷指令",
            "areas": [
                {"bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                 "action": {"type": "postback", "data": "Drama", "displayText": "動漫劇名"}},
                {"bounds": {"x": 834, "y": 0, "width": 833, "height": 843},
                 "action": {"type": "postback", "data": "Role", "displayText": "動漫角色"}},
                {"bounds": {"x": 1663, "y": 0, "width": 834, "height": 843},
                 "action": {"type": "postback", "data": "Music", "displayText": "動漫音樂"}},
                {"bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
                 "action": {"type": "postback", "data": "Game", "displayText": "動漫小遊戲"}},
                {"bounds": {"x": 834, "y": 843, "width": 833, "height": 843},
                 "action": {"type": "postback", "data": "Part", "displayText": "角色猜猜看"}},
                {"bounds": {"x": 1662, "y": 843, "width": 838, "height": 843},
                 "action": {"type": "postback", "data": "Top", "displayText": "十大音樂"}}
            ]
        }

        response = requests.post('https://api.line.me/v2/bot/richmenu', headers=headers, data=json.dumps(body).encode('utf-8'))
        response = response.json()
        rich_menu_id = response.get("richMenuId")

        if rich_menu_id:
            # Upload rich menu image
            with open('static/newrichmenu.jpg', 'rb') as image:
                line_bot_blob_api.set_rich_menu_image(
                    rich_menu_id=rich_menu_id,
                    body=bytearray(image.read()),
                    _headers={'Content-Type': 'image/jpeg'}
                )

            # Set default rich menu
            line_bot_api.set_default_rich_menu(rich_menu_id)
        else:
            print("Error creating rich menu:", response)

create_rich_menu()

# Helper functions
def get_game_state(user_id):
    return game_states.get(user_id)

def handle_game_logic(user_message, game_state, user_id, chance):
    correct_answer = game_state["answer"]  # 正確答案
    attempts = game_state["attempts"]  # 當前已嘗試次數

    # 如果用戶回答正確
    if user_message == correct_answer:
        del game_states[user_id]  # 清除該用戶的遊戲狀態
        return [TextMessage(text="恭喜答對！遊戲結束。")]

    # 更新嘗試次數
    attempts += 1
    game_state["attempts"] = attempts

    # 如果嘗試次數達到上限
    if attempts >= chance:
        del game_states[user_id]  # 清除該用戶的遊戲狀態
        return [TextMessage(text=f"很可惜，答案是：{correct_answer}。遊戲結束！")]

    # 如果回答錯誤但仍有剩餘次數
    return [TextMessage(text=f"答錯了哦！還有 {chance - attempts} 次機會，請再試試看吧！")]


def handle_image_guess_game(event, line_bot_api, prefix, game_type, question_text):
    bucket = db.init_firebase_storage()
    try:
        blob_names = db.list_blob_names(bucket, prefix)
        signed_urls_map = db.generate_signed_urls(bucket, blob_names)
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
        game_states[event.source.user_id] = {
            "game": game_type,
            "attempts": 0,
            "answer": correct_answer
        }
        replys = [
            ImageMessage(original_content_url=url, preview_image_url=url),
            TextMessage(text=question_text)
        ]
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=replys
            )
        )
    except Exception as e:
        logging.error(f"處理 {game_type} 遊戲過程中發生錯誤：{e}")
        replys = [TextMessage(text="發生錯誤，請稍後再試！")]
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=replys
            )
        )
        
def handle_music_guess_game(event, line_bot_api, prefix, game_type, question_text):
    bucket = db.init_firebase_storage()
    try:
        blob_names = db.list_blob_names(bucket, prefix)
        signed_urls_map = db.generate_signed_urls(bucket, blob_names)
        if not signed_urls_map:
            replys = [TextMessage(text="目前沒有可用的音檔，請稍後再試！")]
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )
            return

        correct_answer, url = rand.choice(list(signed_urls_map.items()))
        game_states[event.source.user_id] = {
            "game": game_type,
            "attempts": 0,
            "answer": correct_answer
        }
        replys = [
            AudioMessage(original_content_url=url, duration=func.get_audio_duration_with_mutagen(url)),
            TextMessage(text=question_text)
        ]
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=replys
            )
        )
    except Exception as e:
        logging.error(f"處理 {game_type} 遊戲過程中發生錯誤：{e}")
        replys = [TextMessage(text="發生錯誤，請稍後再試！")]
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=replys
            )
        )

def handle_group_image_guess_game(event, line_bot_api, prefix, game_type, question_text):
    """
    使用 ImageCarouselTemplate 處理分組圖片猜謎遊戲邏輯。
    """
    try:
        # 初始化 Firebase Storage Bucket
        bucket = db.init_firebase_storage()

        # 獲取 Blob 名稱並生成簽名 URL 與分組
        blob_names = db.list_blob_names(bucket, prefix)
        if not blob_names:
            raise ValueError("目前沒有可用的圖片檔案！")

        # 使用 generate_signed_urls_with_groups 生成分組數據
        game_data = db.generate_signed_urls_with_groups(bucket, blob_names)
        if not game_data or not game_data.get("columns"):
            raise ValueError("生成遊戲數據失敗，沒有有效的圖片分組！")

        # 生成 ImageCarouselColumn 的模板，限制最多顯示 10 張圖片
        carousel_columns = [
            ImageCarouselColumn(
                image_url=column["imageUrl"],
                action=MessageAction(
                    label=f"選擇圖片 {i+1}",
                    text=f"選擇圖片 {i+1}"  # 點擊後的訊息不暴露答案
                )
            )
            for i, column in enumerate(game_data["columns"][:10])  # 限制最多顯示 10 列
        ]

        # 生成 ImageCarouselTemplate
        image_carousel_template = ImageCarouselTemplate(columns=carousel_columns)

        # 包裝為 TemplateMessage
        template_message = TemplateMessage(
            alt_text="請猜測圖片答案！",
            template=image_carousel_template
        )

        # 記錄遊戲狀態
        game_states[event.source.user_id] = {
            "game": game_type,
            "attempts": 0,
            "answer": game_data["group_name"],  # 分組名稱作為正確答案
            "options": [f"選擇圖片 {i+1}" for i in range(len(game_data["columns"][:10]))]  # 記錄選項
        }

        # 發送回應
        reply_request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[template_message]
        )
        line_bot_api.reply_message(reply_request)

    except ValueError as ve:
        # 處理值錯誤的特殊情況
        logging.error(f"處理 {game_type} 遊戲過程中發生錯誤：{ve}")
        reply_request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=str(ve))]
        )
        line_bot_api.reply_message(reply_request)

    except Exception as e:
        # 捕獲其他未預期的錯誤
        logging.error(f"處理 {game_type} 遊戲過程中發生未知錯誤：{e}")
        reply_request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text="發生未知錯誤，請稍後再試！")]
        )
        line_bot_api.reply_message(reply_request)


def get_secure_url(base_url, path):
    """生成 HTTPS 安全 URL"""
    full_url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if full_url.startswith("http:"):
        full_url = full_url.replace("http:", "https:")
    return full_url

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 處理 follow 事件（用戶加為好友）
@line_handler.add(FollowEvent)
def handle_follow(event):
    welcome_message = welcome_message = """
🎉 歡迎來到動漫世界 LINE 官方帳號！ 🎉 這裡是專屬於動漫迷的夢幻天地！🌟 加入我們，您將可以探索：

🌸 動漫劇名猜猜看：測試您的動漫劇名記憶力！
✨ 動漫角色探索：尋找您心中的最佳角色靈魂伴侶。
🎵 動漫音樂聆聽：重溫那些讓人熱血沸騰的經典旋律。
🎮 動漫小遊戲挑戰：趣味互動，解鎖隱藏彩蛋！
❓ 角色猜猜看：和好友一起挑戰動漫角色知識！
🏆 Top10 動漫金曲排名：一起票選出屬於我們的動漫音樂排行榜！

立即點擊加入，讓我們一起進入 動漫的奇幻世界！✨
動起手指，動漫世界由你主宰！ 🎊

快來和我們一起探索動漫的無限可能吧！✨
🎉 追蹤我們，讓動漫成為你生活的一部分！
"""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        # 歡迎訊息的貼圖 (貼圖包 ID 和貼圖 ID)
        sticker_message = StickerMessage(
            package_id='789',  # 貼圖包 ID
            sticker_id='10869'  # 貼圖 ID
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[welcome_message,sticker_message]
            )
        )

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
            replys = [TextMessage(text="目前沒有進行中的遊戲，請選擇圖文選單中的選項來開始遊戲！")]
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )
            return

        if game_state["game"] == "Top" and game_state["status"] == "waiting_for_keyword":
            api_key = os.getenv("YOUTUBE_API_KEY")
            query = user_message

            try:
                search_results = func.search_youtube_this_year(api_key, query, max_results=10)
                if not isinstance(search_results, list) or not search_results:
                    replys = [TextMessage(text="很抱歉，未找到相關結果！")]
                else:
                    message_content = "以下是搜尋結果：\n" + "\n".join(
                        [f"{i+1}. 影片標題: {result['title']}\n網址: {result['url']}" for i, result in enumerate(search_results)])
                    replys = [TextMessage(text=message_content[:2000])]

                del game_states[user_id]

            except Exception as e:
                logging.error(f"Error searching YouTube: {e}")
                replys = [TextMessage(text="搜尋時發生錯誤，請稍後再試！")]

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )
            return
        
        if game_state["game"] == "Rps":
            if user_message in ["剪刀", "石頭", "布"]:
                base_url = request.url_root
                bot_choice = rand.choice(["剪刀", "石頭", "布"])
                result = func.RPSGame.determine_winner(user_message, bot_choice)
                user_image_name = RPS_MAPPING[user_message]
                bot_image_name = RPS_MAPPING[bot_choice]

                replys = [
    
                    TextMessage(text=f"你選擇了：{user_message}"),
                    ImageMessage(
                        original_content_url=get_secure_url(base_url, f"static/rps/{user_image_name}.png"),
                        preview_image_url=get_secure_url(base_url, f"static/rps/{user_image_name}.png")
                    ),
                    
                    TextMessage(text=f"機器人選擇了：{bot_choice}"),
                    ImageMessage(
                        original_content_url=get_secure_url(base_url, f"static/rps/{bot_image_name}.png"),
                        preview_image_url=get_secure_url(base_url, f"static/rps/{bot_image_name}.png")
                    ),
                    
                    TextMessage(text=result)
                ]
               
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=replys
                    )
                ) 
                del game_states[user_id]
                return
            else:
                replys = [TextMessage(text="請從快速回覆中選擇剪刀、石頭或布。")]
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=replys
                    )
                )
                return

        replys = handle_game_logic(user_message, game_state, user_id, chance=3)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=replys
            )
        )

@line_handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    user_id = event.source.user_id
    
    # Logging current game state and postback data
    logging.info(f"Current game_states: {game_states}")
    logging.info(f"Postback data: {data}, user_id: {user_id}")
    
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

        if data == 'Drama':
            handle_image_guess_game(event, line_bot_api, "劇名圖片/", "Drama", "請猜測圖片是哪部劇？(並將其打在訊息框)")
        elif data == 'Role':
            handle_image_guess_game(event, line_bot_api, "角色圖片/", "Role", "請猜測圖片是哪位角色？(並將其打在訊息框)")
        elif data == 'Top':
            game_states[user_id] = {
                "game": "Top",
                "status": "waiting_for_keyword"
            }
            replys = [TextMessage(text="請輸入想搜尋的影音關鍵詞，我將幫您查詢 YouTube 當年度的熱門影片！")]
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )
        elif data == 'Game':
            game_states[user_id] = {
                "game": "Rps"
            }
            base_url = request.url_root
            replys = [
                TextMessage(
                    text="剪刀石頭布遊戲開始！請選擇：",
                    quick_reply=QuickReply(
                        items=[
                            QuickReplyItem(
                                action=MessageAction(
                                    label="剪刀",
                                    text="剪刀"
                                ),
                                image_url=get_secure_url(base_url, "static/rps/scissors.png")
                            ),
                            QuickReplyItem(
                                action=MessageAction(
                                    label="石頭",
                                    text="石頭"
                                ),
                                image_url=get_secure_url(base_url, "static/rps/rock.png")
                            ),
                            QuickReplyItem(
                                action=MessageAction(
                                    label="布",
                                    text="布"
                                ),
                                image_url=get_secure_url(base_url, "static/rps/paper.png")
                            )
                        ]
                    )
                )
            ]
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )
        elif data == 'Music':
            handle_music_guess_game(event, line_bot_api, "音檔/", "Music", "請猜測播放的音樂名稱？(並將答案打在訊息框)")
        elif data =='Part':
            handle_group_image_guess_game(event, line_bot_api, "三階段猜圖/", 'Part', "請猜測是哪位角色的部位？(並將答案打在訊息框)")
        else:
            logging.error(f"Unknown postback data: {data}")
            replys = [TextMessage(text="未知的請求類型，請稍後再試！")]
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=replys
                )
            )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )
    app.run()