import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- بيانات GREEN-API الخاصة بك ---
ID_INSTANCE = "7105395235"
API_TOKEN_INSTANCE = "7a7cf9442dbc4d9cb736b48c11ff9c5a077f22ed00fc465dbe"

# رابط API للإرسال
API_URL = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"

# تحميل بيانات القرآن
def load_data():
    try:
        print("جاري تحميل ملف البيانات...")
        with open("mainDataQuran.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"خطأ في تحميل الملف: {e}")
        return []

data = load_data()

# دالة إرسال الرسالة عبر GREEN-API
def send_message(chat_id, text):
    payload = {
        "chatId": chat_id,
        "message": text
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        print(f"حالة الإرسال: {response.status_code}")
    except Exception as e:
        print(f"خطأ في الإرسال: {e}")

# دالة تجهيز الرد
def get_reply(msg):
    msg = msg.strip()
    
    # 1. القائمة والمساعدة
    if msg.lower() in ['start', 'مرحبا', 'قائمة', 'menu', 'هلا']:
        return "مرحباً بك في بوت القرآن الكريم 📖\n\nأرسل ما تريد:\n🔹 *س البقرة* (لإرسال السورة كاملة)\n🔹 *آ البقرة 255* (لإرسال آية محددة)\n🔹 *ص 5* (لإرسال صفحة)"
    
    # 2. بحث سورة
    if msg.startswith("س "):
        surah_name = msg[2:].strip()
        surah = next((s for s in data if s['name']['ar'] == surah_name), None)
        if surah:
            verses = " ".join([f"{a['text']['ar']} ({a['number']})" for a in surah['verses']])
            full_text = f"*{surah['name']['ar']}*\n\n{verses}"
            # نرسل أول 4000 حرف لتجنب مشاكل الطول
            return full_text[:4000] 
        return "لم أتمكن من العثور على السورة، تأكد من كتابة الاسم صحيحاً (مثال: س الكهف)."

    # 3. بحث آية
    if msg.startswith("آ "):
        try:
            parts = msg[2:].split()
            surah_name = parts[0]
            ayah_num = int(parts[1])
            surah = next((s for s in data if s['name']['ar'] == surah_name), None)
            if surah:
                ayah = next((a for a in surah['verses'] if a['number'] == ayah_num), None)
                if ayah:
                    return f"*{surah_name} ({ayah_num})*\n{ayah['text']['ar']}"
        except:
            pass
        return "تأكد من الصيغة الصحيحة، مثال: آ البقرة 255"

    # 4. بحث صفحة
    if msg.startswith("ص "):
        try:
            page = int(msg[2:].strip())
            verses = [f"{a['text']['ar']} ({a['number']})" for s in data for a in s['verses'] if a['page'] == page]
            if verses:
                return f"*الصفحة {page}*\n" + " ".join(verses)
        except:
            pass
        return "رقم الصفحة غير صحيح."

    return None

# نقطة استقبال الرسائل (Webhook)
@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    
    # إذا لم تصل بيانات، نتجاهل الطلب
    if not body:
        return "No Data", 200
        
    try:
        # Green-API يرسل أنواع مختلفة، نحن نريد incomingMessageReceived
        type_webhook = body.get('typeWebhook', '')
        
        if type_webhook == 'incomingMessageReceived':
            message_data = body.get('messageData', {})
            type_message = message_data.get('typeMessage', '')
            
            # نتأكد أنها رسالة نصية
            if type_message == 'textMessage':
                text_content = message_data.get('textMessageData', {}).get('textMessage', '')
                sender_chat_id = body.get('senderData', {}).get('chatId', '')
                
                print(f"رسالة جديدة من {sender_chat_id}: {text_content}")
                
                # نجهز الرد
                reply = get_reply(text_content)
                
                # إذا كان هناك رد، نرسله
                if reply:
                    send_message(sender_chat_id, reply)

    except Exception as e:
        print(f"خطأ عام في الويب هوك: {e}")

    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000)
