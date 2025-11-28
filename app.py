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
        # طباعة نوع الويب هوك للمراقبة
        type_webhook = body.get('typeWebhook', '')
        
        # نحن نهتم فقط بالرسائل الواردة
        if type_webhook == 'incomingMessageReceived':
            msg_data = body.get('messageData', {})
            type_msg = msg_data.get('typeMessage', '')
            sender_id = body.get('senderData', {}).get('chatId', '')

            # طباعة تشخيصية لنعرف من يراسلنا وما هو نوع الرسالة
            # print(f"📥 استلام: {type_msg} من {sender_id}")

            # تجاهل رسائل البوت لنفسه
            if not sender_id.endswith('@c.us'): return "OK", 200

            text = ""
            
            # ------------------------------------------------
            # التعديل هنا: دعم جميع أنواع النصوص
            # ------------------------------------------------
            
            # 1. رسالة نصية عادية
            if type_msg == 'textMessage':
                text = msg_data.get('textMessageData', {}).get('textMessage', '')
            
            # 2. رسالة نصية مطورة (Extended) - هذا ما كان ينقصك!
            elif type_msg == 'extendedTextMessage':
                text = msg_data.get('extendedTextMessageData', {}).get('text', '')
                
            # 3. رسالة مقتبسة (Quoted) - أحياناً تأتي هكذا
            elif type_msg == 'quotedMessage':
                 # نحاول استخراج النص من داخل الاقتباس إذا وجد
                 # (هيكل معقد قليلاً، نكتفي بالأعلى حالياً)
                 pass

            # 4. رسالة زر أو قائمة
            elif type_msg == 'listResponseMessage':
                text = msg_data.get('listResponseMessageData', {}).get('selectedRowId', '')
            elif type_msg == 'buttonsResponseMessage':
                text = msg_data.get('buttonsResponseMessageData', {}).get('selectedButtonId', '')

            # إذا وجدنا نصاً، نرسله للمعالج
            if text:
                process_message(sender_id, text)
            else:
                # طباعة تحذير في اللوج إذا وصلت رسالة غريبة
                print(f"⚠️ تجاهل رسالة من نوع: {type_msg}")

    except Exception as e:
        print(f"❌ Webhook Error: {e}")

    return "OK", 200

# --- إبقاء السيرفر حياً (Keep Alive) ---
@app.route("/ping")
def ping(): return "Alive", 200

def keep_alive():
    while True:
        time.sleep(200) # كل 3 دقائق
        try: requests.get("http://127.0.0.1:5000/ping")
        except: pass

threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5000)
