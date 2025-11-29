import requests
import time
import os
from config import WAHA_BASE_URL, WAHA_API_KEY, MAX_MESSAGE_LENGTH, DELAY_BETWEEN_PARTS

class GreenClient:
    def __init__(self):
        self.base_url = WAHA_BASE_URL
        self.api_key = WAHA_API_KEY
        self.send_text_url = f"{self.base_url}/api/sendText"
        self.send_file_url = f"{self.base_url}/api/sendFile"

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }

    # --- 1. إرسال النص ---
    def send_text(self, chat_id, text):
        headers = self._get_headers()
        
        if len(text) <= MAX_MESSAGE_LENGTH:
            payload = {
                "chatId": chat_id,
                "text": text,
                "session": "default"
            }
            try:
                requests.post(self.send_text_url, json=payload, headers=headers)
            except Exception as e:
                print(f"Error Send: {e}")
            return

        parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for i, part in enumerate(parts):
            payload = {
                "chatId": chat_id,
                "text": part,
                "session": "default"
            }
            try:
                requests.post(self.send_text_url, json=payload, headers=headers)
                time.sleep(DELAY_BETWEEN_PARTS)
            except Exception as e:
                print(f"Error Part {i}: {e}")

    # --- 2. إرسال الملفات (رفع مباشر - الحل الأكيد) ---
    def send_file(self, chat_id, file_path):
        if not os.path.exists(file_path):
            print(f"❌ الملف غير موجود: {file_path}")
            return

        try:
            filename = os.path.basename(file_path)
            
            # هنا السر: نستخدم الهيدر للمفتاح فقط، ونترك requests تضبط نوع الملف تلقائياً
            # ملاحظة: لا تضع 'Content-Type': 'multipart/form-data' يدوياً أبداً!
            headers_for_upload = {
                'X-Api-Key': self.api_key
            }
            
            # تجهيز البيانات كـ فورم (Form Data)
            data_payload = {
                'chatId': chat_id,
                'session': 'default',
                'caption': '🎧 تلاوة'
            }
            
            # فتح الملف وإرساله
            with open(file_path, 'rb') as f:
                # 'file' هو الاسم الذي ينتظره WAHA
                files_payload = {
                    'file': (filename, f, 'audio/mpeg') 
                }
                
                print(f"📤 رفع الملف مباشرة إلى WAHA: {filename}...")
                
                response = requests.post(
                    self.send_file_url, 
                    data=data_payload, 
                    files=files_payload, 
                    headers=headers_for_upload
                )
            
            if response.status_code == 200 or response.status_code == 201:
                print("✅ تم إرسال الصوت بنجاح!")
            else:
                print(f"❌ خطأ من WAHA: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error sending file WAHA: {e}")

    # --- 3. القوائم ---
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        self.send_text_menu_fallback(chat_id, rows)

    def send_text_menu_fallback(self, chat_id, rows):
        msg = "📋 *القائمة:*\n\n"
        for row in rows:
            cmd = row.get('rowId', '')
            if 'CMD_SURAH' in cmd:
                try:
                    num = cmd.split('_')[2]
                    msg += f"🔸 {row['title']} (أرسل: `{num}`)\n"
                except: pass
            else:
                msg += f"🔸 {row['title']}\n"
        self.send_text(chat_id, msg)
