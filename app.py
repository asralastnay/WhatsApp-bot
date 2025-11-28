import threading
import time
import requests
import json
from flask import Flask, request
from message_processor import process_message

app = Flask(__name__)

# --- استقبال الرسائل (Webhook) ---
@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    if not body: return "No Data", 200
    
    try:
        # 1. طباعة كل شيء يوصل عشان نفهم الآيفون ايش يرسل (Debug)
        # سيظهر لك هذا في اللوج بلون أبيض، ابحث عنه
        # print(f"📩 JSON RECEIVED: {json.dumps(body, ensure_ascii=False)}")
        
        type_webhook = body.get('typeWebhook', '')

        # نريد فقط الرسائل الواردة
        if type_webhook == 'incomingMessageReceived':
            msg_data = body.get('messageData', {})
            type_msg = msg_data.get('typeMessage', '')
            sender_data = body.get('senderData', {})
            sender_id = sender_data.get('chatId', '')
            sender_name = sender_data.get('senderName', 'Unknown')

            print(f"🔔 رسالة جديدة من {sender_name} ({sender_id}) - النوع: {type_msg}")

            # تجاهل رسائل البوت لنفسه
            if not sender_id.endswith('@c.us'): 
                return "OK", 200

            text = ""

            # --- محاولات استخراج النص (لحل مشكلة الآيفون) ---

            # الحالة 1: نص عادي (Android غالباً)
            if type_msg == 'textMessage':
                text = msg_data.get('textMessageData', {}).get('textMessage', '')

            # الحالة 2: نص مطور (iPhone غالباً)
            elif type_msg == 'extendedTextMessage':
                text = msg_data.get('extendedTextMessageData', {}).get('text', '')
                # أحياناً يكون النص في description أو title
                if not text:
                    text = msg_data.get('extendedTextMessageData', {}).get('description', '')

            # الحالة 3: رسالة مقتبسة (رد على رسالة)
            elif type_msg == 'quotedMessage':
                # الآيفون يضع الرد داخل extendedTextMessageData داخل quotedMessage
                # هذا هيكل معقد، سنحاول أخذه
                extended_data = msg_data.get('extendedTextMessageData', {})
                if extended_data:
                    text = extended_data.get('text', '')
                
                # لو ما نفع، نجرب textMessageData
                if not text:
                    text_data = msg_data.get('textMessageData', {})
                    text = text_data.get('textMessage', '')

            # الحالة 4: أزرار وقوائم
            elif type_msg == 'listResponseMessage':
                text = msg_data.get('listResponseMessageData', {}).get('selectedRowId', '')
            elif type_msg == 'buttonsResponseMessage':
                text = msg_data.get('buttonsResponseMessageData', {}).get('selectedButtonId', '')

            # --- التنفيذ ---
            if text:
                print(f"✅ تم استخراج النص: {text}")
                process_message(sender_id, text)
            else:
                print(f"⚠️ لم يتم العثور على نص في الرسالة من نوع: {type_msg}")
                # (اختياري) اطبع محتوى الرسالة الغريبة لنفهمها
                print(json.dumps(msg_data, ensure_ascii=False))

    except Exception as e:
        print(f"❌ Webhook Error: {e}")

    return "OK", 200

# --- Keep Alive ---
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
