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

# --- دالة الإرسال الذكية (طويلة المدى) ---
def send_message_smart(chat_id, text):
    headers = {'Content-Type': 'application/json'}
    
    # --- التعديل هنا: رفعنا الحد إلى 7000 حرف ---
    # واتساب يتحمل حتى 65000 نظرياً، لكن 7000 هو الحد الآمن جداً لضمان عدم ضياع النص
    MAX_LENGTH = 7000 
    
    # إذا كانت الرسالة أقل من الحد، أرسلها دفعة واحدة
    if len(text) <= MAX_LENGTH:
        payload = {"chatId": chat_id, "message": text}
        try:
            requests.post(API_URL, json=payload, headers=headers)
            print("تم إرسال الرسالة كاملة.")
        except Exception as e:
            print(f"خطأ إرسال: {e}")
        return

    # إذا كانت أطول، قسمها
    parts = [text[i:i+MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]
    
    print(f"سيتم تقسيم الرسالة إلى {len(parts)} أجزاء...")

    for i, part in enumerate(parts):
        payload = {"chatId": chat_id, "message": part}
        try:
            requests.post(API_URL, json=payload, headers=headers)
            print(f"تم إرسال الجزء {i+1} من {len(parts)}")
            
            # بما أن الرسالة ضخمة، ننتظر 3 ثواني لكي يستوعبها الواتساب
            time.sleep(3) 
        except Exception as e:
            print(f"فشل إرسال الجزء {i}: {e}")

# --- رسالة المساعدة ---
def get_help_message():
    return (
        "👋 *أهلاً بك في بوت القرآن الكريم*\n\n"
        "إليك الأوامر المتاحة:\n\n"
        "🔹 *س البقرة* (لإرسال السورة كاملة)\n"
        "🔹 *آ ال عمران 50* (لآية محددة)\n"
        "🔹 *ص 100* (لصفحة محددة)\n\n"
        "📝 *ملاحظة:* يتم إرسال السور الطويلة في أجزاء لضمان وصولها كاملة."
    )

# --- معالجة الطلبات ---
def process_message(msg):
    msg = msg.strip()
    
    # قائمة المساعدة
    if msg.lower() in ['start', 'مرحبا', 'قائمة', 'menu', 'help', 'مساعدة', 'السلام عليكم']:
        return get_help_message()

    # بحث سورة
    if msg.startswith("س "):
        surah_name = msg[2:].strip()
        surah = next((s for s in data if s['name']['ar'] == surah_name), None)
        if surah:
            verses = " ".join([f"{a['text']['ar']} ({a['number']})" for a in surah['verses']])
            header = f"✨ *سورة {surah['name']['ar']}* ✨\n\n"
            if surah['number'] != 1 and surah['number'] != 9:
                header += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
            return header + verses
        return "❌ لم أجد السورة. تأكد من الاسم (مثال: س الكهف)."

    # بحث آية
    if msg.startswith("آ "):
        try:
            parts = msg[2:].split()
            if len(parts) < 2: return "اكتب رقم الآية."
            surah_name = parts[0]
            ayah_num = int(parts[1])
            surah = next((s for s in data if s['name']['ar'] == surah_name), None)
            if surah:
                ayah = next((a for a in surah['verses'] if a['number'] == ayah_num), None)
                if ayah:
                    return f"🔹 *{surah_name} ({ayah_num})*\n\n{ayah['text']['ar']}"
            return "❌ لم أجد الآية."
        except:
            return "تأكد من الصيغة: آ البقرة 5"

    # بحث صفحة
    if msg.startswith("ص "):
        try:
            page = int(msg[2:].strip())
            verses = [f"{a['text']['ar']} ({a['number']})" for s in data for a in s['verses'] if a['page'] == page]
            if verses:
                return f"📄 *الصفحة {page}*\n\n" + " ".join(verses)
        except:
            pass

    return get_help_message()

# --- الويب هوك (نظام الخلفية لمنع التوقف) ---
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
                
                # تجاهل رسائل البوت نفسه
                if not sender_chat_id.endswith('@c.us'): 
                    return "OK", 200

                print(f"طلب جديد: {text_content}")
                
                reply_text = process_message(text_content)
                
                if reply_text:
                    # تشغيل الإرسال في الخلفية (Thread) ليتمكن السيرفر من الرد بـ OK فوراً
                    threading.Thread(target=send_message_smart, args=(sender_chat_id, reply_text)).start()

    except Exception as e:
        print(f"Error: {e}")

    return "OK", 200

# --- صفحة Ping (لإبقاء البوت حياً) ---
@app.route("/ping")
def ping():
    return "Alive", 200

def keep_alive_loop():
    while True:
        time.sleep(200) # كل 3 دقائق
        try:
            # يرسل طلب لنفسه ليقول لـ Render "أنا مستيقظ"
            requests.get("http://127.0.0.1:5000/ping")
            print("Ping Sent ✅")
        except:
            pass

# تشغيل التنشيط في الخلفية
threading.Thread(target=keep_alive_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5000)
