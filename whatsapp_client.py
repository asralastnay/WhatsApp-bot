import requests
import time
import os
import json
# 👇 هنا كان النقص: أضفنا MY_BOT_URL في الاستدعاء
from config import WAHA_BASE_URL, WAHA_API_KEY, MAX_MESSAGE_LENGTH, DELAY_BETWEEN_PARTS, MY_BOT_URL

class GreenClient:
    def __init__(self):
        self.session = "default"
        self.base_url = WAHA_BASE_URL
        self.headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': WAHA_API_KEY
        }

    # --- 1. إرسال النص ---
    def send_text(self, chat_id, text):
        url = f"{self.base_url}/api/sendText"
        if len(text) <= MAX_MESSAGE_LENGTH:
            self._post_text(url, chat_id, text)
            return

        parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for i, part in enumerate(parts):
            self._post_text(url, chat_id, part)
            time.sleep(DELAY_BETWEEN_PARTS)

    def _post_text(self, url, chat_id, text):
        payload = {"session": self.session, "chatId": chat_id, "text": text}
        try:
            requests.post(url, json=payload, headers=self.headers)
        except Exception as e:
            print(f"Error Send: {e}")

    # --- 2. إرسال الملفات (طريقة الرابط - الذكية) ---
    def send_file(self, chat_id, file_path):
        if not os.path.exists(file_path):
            print("❌ الملف غير موجود")
            return

        url = f"{self.base_url}/api/sendFile"
        filename = os.path.basename(file_path)
        
        # تكوين الرابط العام للملف
        public_file_url = f"{MY_BOT_URL}/audio/{filename}"
        
        try:
            print(f"🔗 محاولة إرسال الملف عبر الرابط: {public_file_url}")
            
            payload = {
                "session": self.session,
                "chatId": chat_id,
                "file": {
                    "url": public_file_url,
                    "filename": filename,
                    "mimetype": "audio/mpeg" # 👈 عشان يوصل صوت
                },
                "caption": "🎧 تلاوة مدمجة"
            }
            
            response = requests.post(url, json=payload, headers=self.headers)
            
            if response.status_code == 200:
                print("✅ تم إرسال طلب الملف الصوت بنجاح")
            else:
                print(f"❌ خطأ من WAHA: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error sending file: {e}")

    # --- 3. القوائم ---
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        self.send_text_menu_fallback(chat_id, rows)

    def send_text_menu_fallback(self, chat_id, rows):
        msg = "📋 *القائمة:*\n━━━━━━━━━\n"
        for row in rows:
            cmd = row['rowId']
            if "CMD_SURAH_" in cmd: display_cmd = f"س {cmd.split('_')[2]}"
            elif "LIST_PAGE_" in cmd: display_cmd = cmd
            else: display_cmd = cmd
            msg += f"🔸 *{row['title']}*\n   اكتب: `{display_cmd}`\n\n"
        self.send_text(chat_id, msg)
