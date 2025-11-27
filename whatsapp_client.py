# whatsapp_client.py
import requests
import time
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
                requests.post(self.send_url, json={"chatId": chat_id, "message": text}, headers=headers)
            except Exception as e:
                print(f"Error Send: {e}")
            return

        # إذا كانت طويلة (تقسيم)
        parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for i, part in enumerate(parts):
            try:
                requests.post(self.send_url, json={"chatId": chat_id, "message": part}, headers=headers)
                print(f"Sent Part {i+1}/{len(parts)}")
                time.sleep(DELAY_BETWEEN_PARTS)
            except Exception as e:
                print(f"Error Part {i}: {e}")

    # إرسال قائمة أزرار (List Message)
    def send_list(self, chat_id, title, btn_text, rows, description=""):
        headers = {'Content-Type': 'application/json'}
        payload = {
            "chatId": chat_id,
            "message": description,
            "title": title,
            "buttonText": btn_text,
            "sections": [{"title": "الخيارات", "rows": rows}]
        }
        try:
            requests.post(self.list_url, json=payload, headers=headers)
        except Exception as e:
            print(f"Error List: {e}")
