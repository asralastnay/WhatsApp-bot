import requests
import time
import os
import json
from config import WAHA_BASE_URL, WAHA_API_KEY, MAX_MESSAGE_LENGTH, DELAY_BETWEEN_PARTS

class GreenClient:
    def __init__(self):
        # اسم الجلسة التي أنشأتها
        self.session = "default"
        self.base_url = WAHA_BASE_URL
        # إعداد الهيدر مع المفتاح الجديد
        self.headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': WAHA_API_KEY
        }

    # --- 1. إرسال النص ---
    def send_text(self, chat_id, text):
        url = f"{self.base_url}/api/sendText"
        
        # إذا كانت الرسالة قصيرة
        if len(text) <= MAX_MESSAGE_LENGTH:
            self._post_text(url, chat_id, text)
            return

        # إذا كانت طويلة (تقسيم)
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

    # --- 2. إرسال الملفات (الصوت) ---
    def send_file(self, chat_id, file_path):
        if not os.path.exists(file_path): return

        url = f"{self.base_url}/api/sendFile"
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                # WAHA يفضل استقبال الملفات بهذه الطريقة
                files = {
                    'file': (filename, f, 'audio/mp3')
                }
                data = {
                    'session': self.session,
                    'chatId': chat_id,
                    'caption': "🎧 تلاوة مدمجة"
                }
                # ملاحظة: لا نرسل Content-Type هنا لأن requests تضبطها تلقائياً مع الملفات
                # لكن نرسل المفتاح
                headers_files = {'X-Api-Key': WAHA_API_KEY}
                
                print(f"📤 جاري إرسال الملف: {filename}")
                requests.post(url, data=data, files=files, headers=headers_files)
                print("✅ تم الإرسال")
        except Exception as e:
            print(f"Error sending file: {e}")

    # --- 3. إرسال القوائم (تحويل لنص بديل) ---
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        # WAHA Free لا يدعم القوائم التفاعلية جيداً، نستخدم النص الأضمن
        self.send_text_menu_fallback(chat_id, rows)

    def send_text_menu_fallback(self, chat_id, rows):
        msg = "📋 *القائمة:*\n━━━━━━━━━\n"
        for row in rows:
            cmd = row['rowId']
            # تبسيط شكل الأمر للمستخدم
            if "CMD_SURAH_" in cmd:
                display_cmd = f"س {cmd.split('_')[2]}"
            elif "LIST_PAGE_" in cmd:
                display_cmd = cmd
            else:
                display_cmd = cmd
            
            msg += f"🔸 *{row['title']}*\n   اكتب: `{display_cmd}`\n\n"
        
        self.send_text(chat_id, msg)
