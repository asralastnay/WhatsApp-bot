import threading
import time
import requests
import os
from flask import Flask, request, send_from_directory
from handlers import handle_incoming_message 
from config import AUDIO_CACHE_DIR 

app = Flask(__name__)

# رابط سيرفر الواتساب (Node.js) الذي قمت برفعه
# تأكد أن هذا الرابط هو الرابط الصحيح لسيرفر البايليز الجديد
WHATSAPP_SERVER_URL = "https://surver-for-whatsapp.onrender.com"

# ---------------------------------------------------------
# 1. تقديم ملفات الصوت (مهم جداً للربط مع Node.js)
# ---------------------------------------------------------
# بما أننا نرسل "روابط" في الكود الجديد، يجب أن يكون هذا المسار متاحاً
# سيقوم سيرفر الواتساب بتحميل الملف من:
# https://your-python-bot.onrender.com/audio/filename.mp3
@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_CACHE_DIR, filename)

# ---------------------------------------------------------
# 2. استقبال الرسائل (Webhook)
# ---------------------------------------------------------
@app.route("/webhook", methods=['POST'])
def webhook():
    data = request.get_json()
    if not data: return "OK", 200

    # التنسيق الجديد القادم من Node.js هو:
    # { "event": "message", "payload": { "from": "...", "body": "...", "fromMe": false } }
    event = data.get('event')
    
    if event == 'message':
        payload = data.get('payload', {})
        
        # تجاهل الرسائل الصادرة من البوت نفسه
        if payload.get('fromMe'): 
            return "OK", 200
        
        chat_id = payload.get('from', '') # الرقم المرسل
        text = payload.get('body', '')    # نص الرسالة
        
        print(f"📩 رسالة جديدة من {chat_id}: {text}")
        
        if text:
            # هنا يتم معالجة الرسالة في ملف handlers
            handle_incoming_message(chat_id, text)

    return "OK", 200

# ---------------------------------------------------------
# 3. الحفاظ على السيرفر نشطاً (Keep Alive)
# ---------------------------------------------------------
@app.route("/ping")
def ping(): return "Alive", 200

def keep_alive():
    while True:
        time.sleep(120) # كل دقيقتين
        try:
            # تنشيط سيرفر البايثون نفسه
            # ملاحظة: في Render قد تحتاج لاستخدام الرابط الخارجي بدلاً من localhost لضمان عدم النوم
            # requests.get("https://your-python-app.onrender.com/ping") 
            requests.get("http://127.0.0.1:5000/ping")
            
            # تنشيط سيرفر الواتساب (Node.js)
            # نقوم بطلب الصفحة الرئيسية فقط لأن /api/sessions غير موجودة في الكود الجديد
            print("Ping Whatsapp Server...")
            requests.get(f"{WHATSAPP_SERVER_URL}/")
        except Exception as e:
            print(f"Keep Alive Error: {e}")
            pass

# تشغيل الـ Keep Alive في الخلفية
threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    # تعديل مهم: Render يحدد البورت تلقائياً عبر متغير البيئة PORT
    # ويجب استخدام host='0.0.0.0' ليكون متاحاً للعامة
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
