# NTUELineBotPJ
 NTUELineBotPJ
## Python Version
3.9.19
## 項目目標

**NTUELineBotPJ** 是一個旨在為動漫愛好者提供互動娛樂的 LINE Bot 項目，用戶可以通過與 Bot 的交互體驗以下功能：

### 1. **猜動漫劇名（場景全圖）**
用戶通過觀察動漫場景的完整圖片，嘗試猜出對應的動漫名稱。

### 2. **猜動漫角色（全圖）**
用戶根據完整的角色圖片，猜測角色的名字。

### 3. **動漫音樂（片段）**
用戶通過聆聽一段動漫音樂片段，猜測對應的動漫或歌曲名稱。

### 4. **動漫小遊戲（猜拳）**
與 Bot 進行經典的猜拳遊戲，享受簡單的互動樂趣。

### 5. **動漫猜猜看（角色部位圖）**
Bot 將展示動漫角色的一部分（例如眼睛、手或發型），用戶需根據提示猜出完整角色。

### 6. **抓取十大歌曲排行榜**
提供十大熱門歌曲排行榜。
---

## 項目技術
### 主要技術棧
- **LINE Messaging API**：實現 Bot 與用戶的交互。
- **YouTube Data API**：用於抓取YouTube Data。
- **Firebase/Storage**：用於存儲圖檔及音樂。
- **Vercel**：Line Bot托管平台。
- **Flask**：作為 Web 框架，提供 Bot 的後端服務支持。
---

# 功能詳情

### **1. 猜動漫劇名**
- Bot 發送一張動漫場景的完整圖片。
- 用戶輸入答案，Bot 判斷答案是否正確並提供反饋。

### **2. 猜動漫角色**
- Bot 發送角色的全身圖。
- 用戶回答角色名稱，Bot 檢查答案的準確性。

### **3. 動漫音樂**
- Bot 播放一段 10-15 秒的動漫音樂片段。
- 用戶根據音樂猜測對應的動漫或歌曲名稱。

### **4. 動漫小遊戲（猜拳）**
- 用戶選擇 "石頭"、"剪刀" 或 "布"，Bot 隨機出招。
- 判斷勝負。

### **5. 動漫猜猜看**
- Bot 顯示角色的一部分（例如眼睛、發型等）。
- 用戶輸入答案，Bot 根據答案給出正誤反饋。

### **6. 抓取十大歌曲排行榜**
- Bot 提供熱門歌曲排行榜。
---