import json
import requests
import time
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- بيانات GREEN-API ---
ID_INSTANCE = "7105395235"
API_TOKEN_INSTANCE = "7a7cf9442dbc4d9cb736b48c11ff9c5a077f22ed00fc465dbe"
API_URL = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"

# --- تحميل البيانات ---
def load_data():
    try:
        print("جاري تحميل ملف البيانات...")
        with open("mainDataQuran.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"خطأ في تحميل الملف: {e}")
        return []

data = load_data()

# --- دالة الإرسال الذكية (تقسيم الرسائل) ---
def send_message_smart(chat_id, text):
    headers = {'Content-Type': 'application/json'}
    
    # الحد الأقصى الآمن للرسالة الواحدة
    MAX_LENGTH = 2000
    
    # إذا كانت الرسالة قصيرة، أرسلها فوراً
    if len(text) <= MAX_LENGTH:
        payload = {"chatId": chat_id, "message": text}
        requests.post(API_URL, json=payload, headers=headers)
        return

    # إذا كانت طويلة، قسمها وأرسل بتتابع
    parts = [text[i:i+MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]
    
    for i, part in enumerate(parts):
        payload = {"chatId": chat_id, "message": part}
        try:
            requests.post(API_URL, json=payload, headers=headers)
            print(f"تم إرسال الجزء {i+1} من {len(parts)}")
            # انتظار ثانيتين بين كل رسالة والأخرى
            time.sleep(2) 
        except Exception as e:
            print(f"فشل إرسال الجزء {i}: {e}")

# --- رسالة الترحيب والمساعدة ---
def get_help_message():
    return (
        "👋 *أهلاً بك في بوت القرآن الكريم*\n\n"
        "أنا هنا لمساعدتك في قراءة القرآن بسهولة. إليك قائمة الأوامر المتاحة:\n\n"
        "📖 *للبحث عن سورة:*\n"
        "اكتب حرف (س) ثم اسم السورة\n"
        "مثال: `س البقرة`\n\n"
        "🔢 *للبحث عن آية محددة:*\n"
        "اكتب (آ) ثم السورة ثم رقم الآية\n"
        "مثال: `آ ال عمران 50`\n\n"
        "📄 *لعرض صفحة من المصحف:*\n"
        "اكتب (ص) ثم رقم الصفحة\n"
        "مثال: `ص 100`\n\n"
        "ℹ️ *للمساعدة في أي وقت:*\n"
        "أرسل كلمة `مساعدة` أو `قائمة`"
    )

# --- معالجة الطلبات ---
def process_message(msg):
    msg = msg.strip()
    
    # 1. أوامر المساعدة والقائمة
    if msg.lower() in ['start', 'مرحبا', 'قائمة', 'menu', 'help', 'مساعدة']:
        return get_help_message()

    # 2. بحث سورة (مع التقسيم)
    if msg.startswith("س "):
        surah_name = msg[2:].strip()
        surah = next((s for s in data if s['name']['ar'] == surah_name), None)
        if surah:
            verses = " ".join([f"{a['text']['ar']} ({a['number']})" for a in surah['verses']])
            header = f"✨ *سورة {surah['name']['ar']}* ✨\n\n"
            if surah['number'] != 1 and surah['number'] != 9:
                header += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
            return header + verses
        return "❌ لم أتمكن من العثور على السورة. تأكد من كتابة الاسم صحيحاً (مثال: س الكهف)."

    # 3. بحث آية
    if msg.startswith("آ "):
        try:
            parts = msg[2:].split()
            if len(parts) < 2: return "يرجى كتابة رقم الآية."
            surah_name = parts[0]
            ayah_num = int(parts[1])
            surah = next((s for s in data if s['name']['ar'] == surah_name), None)
            if surah:
                ayah = next((a for a in surah['verses'] if a['number'] == ayah_num), None)
                if ayah:
                    return f"🔹 *{surah_name} ({ayah_num})*\n\n{ayah['text']['ar']}"
            return "❌ لم أجد السورة أو الآية المطلوبة."
        except:
            return get_help_message()

    # 4. بحث صفحة
    if msg.startswith("ص "):
        try:
            page = int(msg[2:].strip())
            verses = [f"{a['text']['ar']} ({a['number']})" for s in data for a in s['verses'] if a['page'] == page]
            if verses:
                return f"📄 *الصفحة {page}*\n\n" + " ".join(verses)
            return "❌ رقم الصفحة غير صحيح (من 1 إلى 604)."
        except:
            pass

    # إذا لم يفهم البوت الرسالة، يرسل المساعدة
    return get_help_message()

# --- الويب هوك (استقبال الرسائل) ---
@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    if not body: return "No Data", 200
    
    try:
        type_webhook = body.get('typeWebhook', '')
        if type_webhook == 'incomingMessageReceived':
            message_data = body.get('messageData', {})
            if message_data.get('typeMessage') == 'textMessage':
                text_content = message_data.get('textMessageData', {}).get('textMessage', '')
                sender_chat_id = body.get('senderData', {}).get('chatId', '')
                
                # لا ترد على الرسائل الخاصة بالبوت نفسه (لتجنب التكرار)
                if not sender_chat_id.endswith('@c.us'): 
                    return "OK", 200

                print(f"رسالة من {sender_chat_id}: {text_content}")
                
                # معالجة النص
                reply_text = process_message(text_content)
                
                # إرسال الرد (الذكي)
                if reply_text:
                    send_message_smart(sender_chat_id, reply_text)

    except Exception as e:
        print(f"Error: {e}")

    return "OK", 200

# --- صفحة Ping لابقاء السيرفر حياً ---
@app.route("/ping")
def ping():
    return "I am alive!", 200

# --- دالة التنشيط الذاتي (Keep Alive) ---
def keep_alive_loop():
    while True:
        try:
            # انتظر 4 دقائق (240 ثانية)
            time.sleep(240)
            # حاول عمل Ping لنفس السيرفر (استبدل الرابط برابطك الحقيقي في Render)
            # ملاحظة: في Render الرابط المحلي هو 127.0.0.1
            requests.get("http://127.0.0.1:5000/ping")
            print("✅ Keep-Alive Ping Sent!")
        except:
            pass

# تشغيل التنشيط في خلفية التطبيق
threading.Thread(target=keep_alive_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5000)
