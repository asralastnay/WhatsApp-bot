import requests
import time
import os
import json
import base64  # <--- مكتبة جديدة مهمة
from config import WAHA_BASE_URL, WAHA_API_KEY, MAX_MESSAGE_LENGTH, DELAY_BETWEEN_PARTS

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
        payload = {
            "session": self.session,
            "chatId": chat_id,
            "text": text
        }
        try:
            requests.post(url, json=payload, headers=self.headers)
        except Exception as e:
            print(f"Error Send: {e}")

    # --- 2. إرسال الملفات (باستخدام Base64 - الطريقة الأضمن) ---
    def send_file(self, chat_id, file_path):
        if not os.path.exists(file_path):
            print("❌ الملف غير موجود")
            return

        url = f"{self.base_url}/api/sendFile"
        filename = os.path.basename(file_path)
        
        try:
            print(f"🔄 جاري تشفير الملف: {filename}...")
            
            # 1. قراءة الملف وتحويله إلى Base64
            with open(file_path, "rb") as file:
                encoded_string = base64.b64encode(file.read()).decode('utf-8')
            
            # 2. تجهيز البيانات كـ JSON (هكذا لن يرفضها السيرفر)
            payload = {
                "session": self.session,
                "chatId": chat_id,
                "file": {
                    "mimetype": "audio/mpeg", # نوع الملف mp3
                    "filename": filename,
                    "data": encoded_string
                },
                "caption": "🎧 تلاوة مدمجة"
            }
            
            # 3. الإرسال
            print(f"📤 جاري إرسال البيانات للسيرفر...")
            response = requests.post(url, json=payload, headers=self.headers)
            
            if response.status_code == 200:
                print("✅ تم إرسال الملف الصوتي بنجاح")
            else:
                print(f"❌ خطأ من WAHA: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error sending file: {e}")

    # --- 3. إرسال القوائم ---
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        self.send_text_menu_fallback(chat_id, rows)

    def send_text_menu_fallback(self, chat_id, rows):
        msg = "📋 *القائمة:*\n━━━━━━━━━\n"
        for row in rows:
            cmd = row['rowId']
            if "CMD_SURAH_" in cmd:
                display_cmd = f"س {cmd.split('_')[2]}"
            elif "LIST_PAGE_" in cmd:
                display_cmd = cmd
            else:
                display_cmd = cmd
            
            msg += f"🔸 *{row['title']}*\n   اكتب: `{display_cmd}`\n\n"
        
        self.send_text(chat_id, msg)
