import threading
import time
import requests
import os
from flask import Flask, request, send_from_directory
from handlers import handle_incoming_message 
from config import AUDIO_CACHE_DIR # <--- استيراد مهم

app = Flask(__name__)

# رابط سيرفر الواتس لعمل Keep Alive
WAHA_URL = "https://surver-for-whatsapp.onrender.com"

# --- دالة جديدة: للسماح بتحميل الملفات الصوتية ---
@app.route("/audio/<path:filename>")
def serve_audio(filename):
    # هذه الدالة تجعل مجلد audio_temp متاحاً عبر الرابط
    return send_from_directory(AUDIO_CACHE_DIR, filename)

# --- استقبال الرسائل ---
@app.route("/webhook", methods=['POST'])
def webhook():
    data = request.get_json()
    if not data: return "OK", 200

    event = data.get('event')
    if event == 'message':
        payload = data.get('payload', {})
        if payload.get('fromMe'): return "OK", 200
        
        chat_id = payload.get('from', '')
        text = payload.get('body', '')
        
        print(f"📩 رسالة من {chat_id}: {text}")
        if text:
            handle_incoming_message(chat_id, text)

    return "OK", 200

# Keep Alive
@app.route("/ping")
def ping(): return "Alive", 200

def keep_alive():
    while True:
        time.sleep(120)
        try:
            requests.get("http://127.0.0.1:5000/ping")
            requests.get(f"{WAHA_URL}/api/sessions")
        except: pass

threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5000)
