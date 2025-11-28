import threading
import time
import requests
import json
from flask import Flask, request
from message_processor import process_message

app = Flask(__name__)

@app.route("/webhook", methods=['POST'])
def webhook():
    # 1. طباعة البيانات الخام فوراً (للتشخيص)
    try:
        raw_body = request.get_data(as_text=True)
        # print(f"📥 RAW DATA: {raw_body}") # فعل هذا السطر فقط إذا كنت يائساً جداً
        body = json.loads(raw_body)
    except:
        return "Invalid JSON", 200

    if not body: return "No Data", 200
    
    try:
        type_webhook = body.get('typeWebhook', '')

        if type_webhook == 'incomingMessageReceived':
            msg_data = body.get('messageData', {})
            sender_data = body.get('senderData', {})
            sender_id = sender_data.get('chatId', '')
            sender_name = sender_data.get('senderName', 'Unknown')
            
            # طباعة من يراسلنا
            print(f"🔔 رسالة من: {sender_name} | ID: {sender_id}")

            # تجاهل البوت لنفسه
            if sender_id.endswith('@c.us') and sender_data.get('senderName') == 'Quran Bot': 
                 return "OK", 200

            # محاولة استخراج النص بأي طريقة ممكنة
            text = ""
            
            # 1. Text Message
            text = msg_data.get('textMessageData', {}).get('textMessage')
            
            # 2. Extended Text Message
            if not text:
                text = msg_data.get('extendedTextMessageData', {}).get('text')
            
            # 3. Quoted Message (الردود)
            if not text:
                # أحياناً تكون داخل stanzaId، نحاول البحث بعمق
                ext_data = msg_data.get('extendedTextMessageData', {})
                text = ext_data.get('description') or ext_data.get('title')

            # 4. Buttons / Lists
            if not text:
                text = msg_data.get('listResponseMessageData', {}).get('selectedRowId')
            if not text:
                text = msg_data.get('buttonsResponseMessageData', {}).get('selectedButtonId')

            if text:
                print(f"✅ النص المستخرج: {text}")
                # إرسال للمعالج
                process_message(sender_id, text)
            else:
                print("⚠️ وصل إشعار رسالة لكن لم أستطع استخراج نص منها!")
                # اطبع هيكل الرسالة لنفهم السبب
                print(json.dumps(msg_data, ensure_ascii=False))

    except Exception as e:
        print(f"❌ Webhook Error: {e}")

    return "OK", 200

# Keep Alive
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
