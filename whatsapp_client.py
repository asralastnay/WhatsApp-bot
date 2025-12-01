import requests
import time
import os
# تأكد من أن ملف config يحتوي على هذه المتغيرات أو قم بتعريفها هنا مباشرة
from config import WAHA_BASE_URL, WAHA_API_KEY, MAX_MESSAGE_LENGTH, DELAY_BETWEEN_PARTS

class GreenClient:
    def __init__(self):
        # ضع رابط سيرفرك الجديد هنا (الذي رفعته على Render)
        # ملاحظة: لا تضع /webhook هنا، نحن نتكلم مع الـ API لإرسال الرسائل
        self.base_url = "https://surver-for-whatsapp.onrender.com"  # ⚠️ استبدل هذا برابط تطبيقك الحقيقي
        self.api_key = "12345" # إذا كنت لا تتحقق منه في Node.js فلا داعي للقلق بشأنه
        
        # النقاط النهائية (Endpoints) كما عرفناها في كود Node.js
        self.send_text_url = f"{self.base_url}/api/sendText"
        self.send_file_url = f"{self.base_url}/api/sendFile"

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            # 'X-Api-Key': self.api_key # اختياري حسب كود السيرفر
        }

    # --- 1. إرسال النص ---
    def send_text(self, chat_id, text):
        headers = self._get_headers()
        
        # التأكد من طول الرسالة وتقسيمها إذا لزم الأمر
        if len(text) <= MAX_MESSAGE_LENGTH:
            payload = {
                "chatId": chat_id,
                "text": text
            }
            try:
                # إرسال طلب JSON بسيط
                requests.post(self.send_text_url, json=payload, headers=headers)
            except Exception as e:
                print(f"Error Send: {e}")
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

    # --- 2. إرسال الملفات ---
    def send_file(self, chat_id, file_url, caption=""):
        """
        ملاحظة: السيرفر الجديد يتوقع رابط مباشر للملف (URL)
        إذا كنت تريد إرسال ملف من جهازك، يجب رفعه أولاً أو تعديل السيرفر ليقبل Base64.
        هنا نفترض أن file_url هو رابط مباشر للصوت (مثلاً رابط قرآن mp3).
        """
        try:
            headers = self._get_headers()
            
            # تحديد نوع الملف بناءً على الرابط (تخميني) أو افتراضي
            mimetype = 'audio/mp4' 
            if str(file_url).endswith('.pdf'):
                mimetype = 'application/pdf'
            elif str(file_url).endswith('.jpg') or str(file_url).endswith('.png'):
                mimetype = 'image/jpeg'

            # تجهيز البيانات كـ JSON كما يتوقعه كود Node.js
            # app.post('/api/sendFile', async (req, res) => { const { chatId, file, mimetype, caption } ...
            payload = {
                'chatId': chat_id,
                'file': { 'url': file_url }, # نرسل الرابط داخل كائن file
                'mimetype': mimetype,
                'caption': caption
            }
            
            print(f"📤 Sending file URL to Node.js: {file_url}...")
            
            response = requests.post(
                self.send_file_url, 
                json=payload,  # نستخدم json بدلاً من data/files
                headers=headers
            )
            
            if response.status_code == 200 or response.status_code == 201:
                print("✅ تم إرسال الملف بنجاح!")
            else:
                print(f"❌ خطأ من السيرفر: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error sending file: {e}")

    # --- 3. القوائم (النصية البديلة) ---
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        # واتساب أوقف القوائم القديمة، نستخدم القوائم النصية كبديل
        self.send_text_menu_fallback(chat_id, rows, title, description)

    def send_text_menu_fallback(self, chat_id, rows, title, description):
        msg = f"*{title}*\n{description}\n\n📋 *القائمة:*\n"
        for row in rows:
            cmd = row.get('rowId', '')
            row_title = row.get('title', '')
            
            # محاولة استخراج الرقم لتسهيل الرد
            # مثال: إذا كان الأمر CMD_SURAH_001 نكتب: سورة الفاتحة (1)
            display_cmd = ""
            if 'CMD_SURAH' in cmd:
                try:
                    num = cmd.split('_')[2]
                    display_cmd = f"(رقم: {num})"
                except: pass
            
            msg += f"🔸 {row_title} {display_cmd}\n"
            
        msg += "\n✏️ *للإختيار، أرسل اسم السورة أو رقمها.*"
        self.send_text(chat_id, msg)
