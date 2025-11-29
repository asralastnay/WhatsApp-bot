import threading
import time
import requests
from flask import Flask, request

# استيراد المعالج (تأكد أن الملف handlers.py موجود ويعمل)
from handlers import handle_incoming_message 
# ملاحظة: إذا كنت تستخدم message_processor.py كجسر، فاستخدمه، لكن handlers هو الأحدث

app = Flask(__name__)

# رابط سيرفر الواتس لعمل Keep Alive
WAHA_URL = "https://surver-for-whatsapp.onrender.com"

@app.route("/webhook", methods=['POST'])
def webhook():
    data = request.get_json()
    if not data: return "OK", 200

    # WAHA Event Structure
    # { "event": "message", "payload": { "from": "...", "body": "..." } }
    
    event = data.get('event')
    
    if event == 'message':
        payload = data.get('payload', {})
        
        # تجاهل رسائل البوت لنفسه
        if payload.get('fromMe'): return "OK", 200
        
        # استخراج البيانات
        chat_id = payload.get('from', '')
        text = payload.get('body', '')
        
        # إصلاح بسيط: أحياناً يأتي الرقم بدون @c.us، نتأكد منه
        # لكن WAHA عادة يرسله صحيحاً.
        
        print(f"📩 رسالة جديدة من {chat_id}: {text}")
        
        if text:
            # إرسال للمعالج
            handle_incoming_message(chat_id, text)

    return "OK", 200

# Keep Alive مزدوج (للبوت وللواتساب)
@app.route("/ping")
def ping(): return "Alive", 200

def keep_alive():
    while True:
        time.sleep(120) # كل دقيقتين
        try:
            # 1. إيقاظ البوت
            requests.get("http://127.0.0.1:5000/ping")
            
            # 2. إيقاظ الواتساب (مهم جداً عشان ما يفصل)
            requests.get(f"{WAHA_URL}/api/sessions")
            print("✅ Keep-Alive Ping sent to both servers")
        except: pass

threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5000)
