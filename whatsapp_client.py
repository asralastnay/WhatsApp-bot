import requests
import time
import os
# استيراد الإعدادات من ملف config لضمان التوافق
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
            payload = {
                "chatId": chat_id,
                "text": text
            }
            try:
                requests.post(self.send_text_url, json=payload, headers=headers)
            except Exception as e:
                print(f"Error Send Text: {e}")
            return

        # تقسيم الرسائل الطويلة
        parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for i, part in enumerate(parts):
            payload = {
                "chatId": chat_id,
                "text": part
            }
            try:
                requests.post(self.send_text_url, json=payload, headers=headers)
                time.sleep(DELAY_BETWEEN_PARTS)
            except Exception as e:
                print(f"Error Part {i}: {e}")

    # --- 2. إرسال الملفات (مع معالجة الروابط المحلية) ---
    def send_file(self, chat_id, file_path_or_url, caption=""):
        try:
            headers = self._get_headers()
            final_url = ""
            
            # تحديد نوع الملف الافتراضي
            mimetype = 'audio/mp4' 

            # --- المنطق الذكي لتحويل المسارات ---
            # 1. إذا كان القادم رابط إنترنت (مثل: https://server8.mp3quran.net/...)
            if str(file_path_or_url).startswith("http"):
                final_url = file_path_or_url
            
            # 2. إذا كان ملفاً محلياً في السيرفر (مثل: audio_temp/merged.mp3)
            else:
                filename = os.path.basename(file_path_or_url)
                # نحوله لرابط باستخدام رابط بوت البايثون
                final_url = f"{MY_BOT_URL}/audio/{filename}"
                print(f"🔄 Converted local path to URL: {final_url}")

            # محاولة تخمين نوع الملف من الامتداد
            if str(final_url).endswith('.pdf'): mimetype = 'application/pdf'
            elif str(final_url).endswith('.jpg') or str(final_url).endswith('.png'): mimetype = 'image/jpeg'
            elif str(final_url).endswith('.mp3'): mimetype = 'audio/mp4'

            # تجهيز البيانات كـ JSON
            payload = {
                'chatId': chat_id,
                'file': { 'url': final_url }, # السيرفر ينتظر رابطاً هنا
                'mimetype': mimetype,
                'caption': caption
            }
            
            print(f"📤 Sending file request to Node.js: {final_url}")
            
            response = requests.post(
                self.send_file_url, 
                json=payload, 
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                print("✅ File Sent Successfully!")
            else:
                print(f"❌ Server Error ({response.status_code}): {response.text}")

        except Exception as e:
            print(f"Error sending file: {e}")

    # --- 3. القوائم (Fallback to Text) ---
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        # نستخدم القائمة النصية لأنها أكثر استقراراً
        self.send_text_menu_fallback(chat_id, rows, title, description)

    def send_text_menu_fallback(self, chat_id, rows, title, description):
        msg = f"*{title}*\n{description}\n\n📋 *القائمة:*\n"
        for row in rows:
            cmd = row.get('rowId', '')
            row_title = row.get('title', '')
            
            # استخراج الأرقام لتسهيل الاختيار
            display_cmd = ""
            if 'CMD_SURAH' in cmd:
                try:
                    num = cmd.split('_')[2]
                    display_cmd = f"({num})"
                except: pass
            
            msg += f"🔸 {row_title} {display_cmd}\n"
            
        msg += "\n✏️ *للإختيار، أرسل الرقم أو الاسم.*"
        self.send_text(chat_id, msg)
