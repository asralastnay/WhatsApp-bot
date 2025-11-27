# whatsapp_client.py
import requests
import time
import json
from config import INSTANCE_ID, API_TOKEN, MAX_MESSAGE_LENGTH, DELAY_BETWEEN_PARTS

class GreenClient:
    def __init__(self):
        self.api_url = f"https://api.green-api.com/waInstance{INSTANCE_ID}"
        self.send_url = f"{self.api_url}/sendMessage/{API_TOKEN}"
        self.list_url = f"{self.api_url}/sendListMessage/{API_TOKEN}"

    # إرسال رسالة نصية (مع التقسيم الذكي)
    def send_text(self, chat_id, text):
        headers = {'Content-Type': 'application/json'}
        
        # إذا كانت قصيرة
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

    # إرسال قائمة أزرار (مع الخطة البديلة)
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        headers = {'Content-Type': 'application/json'}
        
        # تقصير النصوص لتناسب حدود واتساب الصارمة
        safe_title = (title[:50] + '..') if len(title) > 50 else title
        safe_btn = (btn_text[:20])      if len(btn_text) > 20 else btn_text
        safe_desc = (description[:50])  if len(description) > 50 else description

        # تجهيز البيانات
        payload = {
            "chatId": chat_id,
            "message": safe_desc,
            "title": safe_title,
            "buttonText": safe_btn,
            "footer": "بوت القرآن الكريم", # إلزامي
            "sections": [
                {
                    "title": "الخيارات",
                    "rows": rows
                }
            ]
        }
        
        try:
            print("⏳ محاولة إرسال القائمة التفاعلية...")
            response = requests.post(self.list_url, json=payload, headers=headers)
            
            # طباعة رد السيرفر للتوضيح
            print(f"Green-API Status: {response.status_code}")
            print(f"Green-API Response: {response.text}")

            # إذا فشل الإرسال (أي رقم غير 200)، نلجأ للخطة البديلة
            if response.status_code != 200:
                print("⚠️ فشل إرسال القائمة التفاعلية، جاري إرسال القائمة النصية...")
                self.send_text_menu_fallback(chat_id, rows)

        except Exception as e:
            print(f"Error List Sending: {e}")
            self.send_text_menu_fallback(chat_id, rows)

    # الخطة البديلة: تحويل القائمة إلى نص عادي
    def send_text_menu_fallback(self, chat_id, rows):
        msg = "📋 *قائمة السور المتاحة:*\n\n"
        msg += "للاختيار، انسخ وارسل الأمر الموجود تحت السورة:\n\n"
        
        for row in rows:
            title = row['title']
            desc = row.get('description', '')
            cmd_id = row['rowId']
            
            # إذا كان زر تنقل (التالي/السابق)
            if "LIST_PAGE" in cmd_id:
                msg += f"〰️〰️〰️\n*{title}*\nاكتب: `{cmd_id}`\n"
            else:
                # إذا كان سورة، نستخرج رقم السورة من الأمر CMD_SURAH_2
                try:
                    surah_num = cmd_id.split('_')[2]
                    # نسهل الأمر على المستخدم: يكتب "س 2" أو "س البقرة"
                    msg += f"🔸 *{title}* ({desc})\nاكتب: `س {title.split('.')[1].strip()}`\n\n"
                except:
                    msg += f"🔸 {title}\n"

        self.send_text(chat_id, msg)
