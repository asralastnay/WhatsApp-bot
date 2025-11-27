import requests
import time
import os
from config import INSTANCE_ID, API_TOKEN, MAX_MESSAGE_LENGTH, DELAY_BETWEEN_PARTS

class GreenClient:
    def __init__(self):
        self.api_url = f"https://api.green-api.com/waInstance{INSTANCE_ID}"
        self.send_url = f"{self.api_url}/sendMessage/{API_TOKEN}"
        self.list_url = f"{self.api_url}/sendListMessage/{API_TOKEN}"
        self.upload_url = f"{self.api_url}/sendFileByUpload/{API_TOKEN}"

    # --- 1. إرسال النص (مع التقسيم الذكي) ---
    def send_text(self, chat_id, text):
        headers = {'Content-Type': 'application/json'}
        
        # إذا كانت الرسالة قصيرة
        if len(text) <= MAX_MESSAGE_LENGTH:
            try:
                payload = {"chatId": chat_id, "message": text}
                requests.post(self.send_url, json=payload, headers=headers)
            except Exception as e:
                print(f"Error Send: {e}")
            return

        # إذا كانت طويلة (تقسيم)
        parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for i, part in enumerate(parts):
            try:
                payload = {"chatId": chat_id, "message": part}
                requests.post(self.send_url, json=payload, headers=headers)
                print(f"Sent Part {i+1}/{len(parts)}")
                time.sleep(DELAY_BETWEEN_PARTS)
            except Exception as e:
                print(f"Error Part {i}: {e}")

    # --- 2. إرسال الملفات (صوت، صورة، إلخ) - [الميزة الجديدة] ---
    def send_file(self, chat_id, file_path):
        """يرفع الملف إلى Green-API ويرسله للمستخدم"""
        if not os.path.exists(file_path):
            print(f"❌ الملف غير موجود: {file_path}")
            return

        try:
            filename = os.path.basename(file_path)
            # إعداد الملف للرفع
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'audio/mpeg')}
                payload = {'chatId': chat_id, 'fileName': filename}
                
                print(f"📤 جاري رفع الملف الصوتي: {filename}...")
                
                # ملاحظة: عند رفع الملفات لا نضع header json
                response = requests.post(self.upload_url, data=payload, files=files)
                
                if response.status_code == 200:
                    print("✅ تم إرسال الملف الصوتي بنجاح.")
                else:
                    print(f"❌ فشل إرسال الملف: {response.status_code} - {response.text}")
                    
        except Exception as e:
            print(f"Error sending file: {e}")

    # --- 3. إرسال القوائم (مع الخطة البديلة النصية) ---
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        headers = {'Content-Type': 'application/json'}
        
        safe_title = (title[:50] + '..') if len(title) > 50 else title
        safe_btn = (btn_text[:20])      if len(btn_text) > 20 else btn_text
        safe_desc = (description[:50])  if len(description) > 50 else description

        payload = {
            "chatId": chat_id,
            "message": safe_desc,
            "title": safe_title,
            "buttonText": safe_btn,
            "footer": "بوت القرآن الكريم",
            "sections": [{"title": "الخيارات", "rows": rows}]
        }
        
        try:
            response = requests.post(self.list_url, json=payload, headers=headers)
            if response.status_code != 200:
                print("⚠️ فشل إرسال القائمة، التحويل للنص...")
                self.send_text_menu_fallback(chat_id, rows)
        except Exception as e:
            print(f"Error List: {e}")
            self.send_text_menu_fallback(chat_id, rows)

    def send_text_menu_fallback(self, chat_id, rows):
        msg = "📋 *القائمة:*\n\n"
        for row in rows:
            msg += f"🔸 {row['title']}\n"
        self.send_text(chat_id, msg)
