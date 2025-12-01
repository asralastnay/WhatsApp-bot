import threading
import time
import requests
import os
from flask import Flask, request, send_from_directory
from handlers import handle_incoming_message 
# استيراد الإعدادات لضمان التوافق وعدم تكرار الروابط
from config import AUDIO_CACHE_DIR, WAHA_BASE_URL, MY_BOT_URL

app = Flask(__name__)

# ---------------------------------------------------------
# 1. تقديم ملفات الصوت (Audio Server)
# ---------------------------------------------------------
# هذه الدالة ضرورية جداً! 
# هي التي تسمح لسيرفر الواتساب بتحميل الملفات المدمجة من عندك
# الرابط يكون: https://your-app.onrender.com/audio/filename.mp3
@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_CACHE_DIR, filename)

# ---------------------------------------------------------
# 2. استقبال الرسائل (Webhook Endpoint)
# ---------------------------------------------------------
@app.route("/webhook", methods=['POST'])
def webhook():
    data = request.get_json()
    if not data: return "OK", 200

    # تحليل البيانات القادمة من سيرفر Node.js
    event = data.get('event')
    
    if event == 'message':
        payload = data.get('payload', {})
        
        # تجاهل الرسائل التي يرسلها البوت لنفسه
        if payload.get('fromMe'): 
            return "OK", 200
        
        chat_id = payload.get('from', '')
        text = payload.get('body', '')
        
        print(f"📩 رسالة جديدة من {chat_id}: {text}")
        
        if text:
            # إرسال البيانات للملف المسؤول عن المنطق (Handlers)
            try:
                handle_incoming_message(chat_id, text)
            except Exception as e:
                print(f"❌ خطأ في معالجة الرسالة: {e}")

    return "OK", 200

# ---------------------------------------------------------
# 3. الحفاظ على السيرفر نشطاً (Keep Alive)
# ---------------------------------------------------------
@app.route("/ping")
def ping(): return "Alive", 200

def keep_alive():
    while True:
        time.sleep(120) # الانتظار دقيقتين
        try:
            # 1. تنشيط سيرفر الواتساب (Node.js)
            print(f"💓 Ping Node.js Server: {WAHA_BASE_URL}")
            requests.get(f"{WAHA_BASE_URL}/")
            
            # 2. تنشيط سيرفر البايثون نفسه (هذا السيرفر)
            # نستخدم الرابط الخارجي لضمان عدم نوم السيرفر في الاستضافات المجانية
            if MY_BOT_URL:
                requests.get(f"{MY_BOT_URL}/ping")
            else:
                # بديل: استخدام اللوكل هوست إذا لم يوجد رابط خارجي
                port = os.environ.get("PORT", 5000)
                requests.get(f"http://127.0.0.1:{port}/ping")
                
        except Exception as e:
            print(f"⚠️ Keep Alive Error: {e}")

# تشغيل الـ Keep Alive في خيط منفصل (Background Thread)
threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    # الحصول على المنفذ من بيئة العمل (ضروري لـ Render)
    port = int(os.environ.get("PORT", 5000))
    # تشغيل السيرفر ليكون متاحاً للعامة (0.0.0.0)
    app.run(host='0.0.0.0', port=port)
