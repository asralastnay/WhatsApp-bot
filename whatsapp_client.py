import requests
import time
import os
# استيراد الإعدادات من ملف config
from config import (
    WAHA_BASE_URL, 
    WAHA_API_KEY, 
    MAX_MESSAGE_LENGTH, 
    DELAY_BETWEEN_PARTS,
    MY_BOT_URL
)

class GreenClient:
    def __init__(self):
        # استخدام الرابط الموجود في config.py
        self.base_url = WAHA_BASE_URL
        self.api_key = WAHA_API_KEY
        
        # نقاط الاتصال (Endpoints)
        self.send_text_url = f"{self.base_url}/api/sendText"
        self.send_file_url = f"{self.base_url}/api/sendFile"

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }

    # --- 1. إرسال النص ---
    def send_text(self, chat_id, text):
        if not text: return
        headers = self._get_headers()
        
        # إرسال مباشر إذا كانت الرسالة قصيرة
        if len(text) <= MAX_MESSAGE_LENGTH:
            payload = { "chatId": chat_id, "text": text }
            try:
                requests.post(self.send_text_url, json=payload, headers=headers)
            except Exception as e:
                print(f"Error Send Text: {e}")
            return

        # تقسيم الرسائل الطويلة
        parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for i, part in enumerate(parts):
            payload = { "chatId": chat_id, "text": part }
            try:
                requests.post(self.send_text_url, json=payload, headers=headers)
                time.sleep(DELAY_BETWEEN_PARTS)
            except Exception as e:
                print(f"Error Part {i}: {e}")

    # --- 2. إرسال الملفات (Audio File Mode) ---
    def send_file(self, chat_id, file_path_or_url, caption=""):
        try:
            headers = self._get_headers()
            final_url = ""
            
            # ✅ تحديد النوع: audio/mp4 هو الأفضل لملفات MP3 على الواتساب
            # هذا النوع يضمن أن الواتساب يعامله كملف صوتي عالي الجودة وليس Voice Note
            mimetype = 'audio/mp4' 

            # 1. معالجة الرابط أو المسار
            if str(file_path_or_url).startswith("http"):
                # رابط خارجي مباشر
                final_url = file_path_or_url
            else:
                # ملف محلي (تم دمجه بـ FFmpeg)
                filename = os.path.basename(file_path_or_url)
                # نحوله لرابط ليتمكن سيرفر الواتساب من تحميله
                final_url = f"{MY_BOT_URL}/audio/{filename}"
                print(f"🔄 Converted local path to URL: {final_url}")

            # 2. تجهيز البيانات
            payload = {
                'chatId': chat_id,
                'file': { 'url': final_url },
                'mimetype': mimetype,
                'caption': caption,
                # ⛔️ هام جداً: PTT مغلق (False) لحل مشكلة الآيفون
                # هذا سيجعل الملف يظهر مع زر تشغيل واسم الملف، ويحافظ على الجودة الأصلية
                'ptt': False 
            }
            
            print(f"📤 Sending Audio File to Node.js: {final_url}")
            
            # 3. الإرسال
            response = requests.post(self.send_file_url, json=payload, headers=headers)
            
            if response.status_code in [200, 201]:
                print("✅ Audio File sent successfully!")
            else:
                print(f"❌ Server Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error sending file: {e}")

    # --- 3. القوائم (نصية) ---
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        self.send_text_menu_fallback(chat_id, rows, title, description)

    def send_text_menu_fallback(self, chat_id, rows, title, description):
        msg = f"*{title}*\n{description}\n\n📋 *القائمة:*\n"
        for row in rows:
            cmd = row.get('rowId', '')
            row_title = row.get('title', '')
            
            display_cmd = ""
            if 'CMD_SURAH' in cmd:
                try:
                    num = cmd.split('_')[2]
                    display_cmd = f"({num})"
                except: pass
            
            msg += f"🔸 {row_title} {display_cmd}\n"
            
        msg += "\n✏️ *للإختيار، أرسل الرقم أو الاسم.*"
        self.send_text(chat_id, msg)
