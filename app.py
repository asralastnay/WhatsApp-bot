# app.py
import threading
import time
import requests
from flask import Flask, request
from message_processor import process_message

app = Flask(__name__)

# دالة الاستقبال (Webhook)
@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    if not body: return "No Data", 200
    
    try:
        type_webhook = body.get('typeWebhook', '')
        if type_webhook == 'incomingMessageReceived':
            msg_data = body.get('messageData', {})
            type_msg = msg_data.get('typeMessage', '')
            sender_id = body.get('senderData', {}).get('chatId', '')

            # تجاهل رسائل البوت لنفسه
            if not sender_id.endswith('@c.us'): return "OK", 200

            text = ""
            # استخراج النص سواء كان كتابة أو اختيار من قائمة
            if type_msg == 'textMessage':
                text = msg_data.get('textMessageData', {}).get('textMessage', '')
            elif type_msg == 'listResponseMessage':
                text = msg_data.get('listResponseMessageData', {}).get('selectedRowId', '')

            if text:
                # أرسل النص للمعالج المنطقي
                process_message(sender_id, text)

    except Exception as e:
        print(f"Webhook Error: {e}")

    return "OK", 200

# Keep Alive (لمنع توقف Render)
@app.route("/ping")
def ping(): return "Alive", 200

def keep_alive():
    while True:
        time.sleep(200)
        try: requests.get("http://127.0.0.1:5000/ping")
        except: pass

threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5000)
