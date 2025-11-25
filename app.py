import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# إعداد تطبيق Flask
app = Flask(__name__)

# متغير لتخزين حالة المستخدمين (بديل لـ context.user_data في تيليجرام)
# التنسيق: {'whatsapp_number': {'state': '...', 'page': 0}}
users_state = {}

# تحميل بيانات السور والآيات
def load_data():
    try:
        with open("mainDataQuran.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print("ملف قاعدة البيانات غير موجود.")
        return []

data = load_data()

# دالة لتقسيم الرسائل الطويلة (واتساب حدوده 1600 حرف تقريباً)
def send_long_message(resp, text):
    max_length = 1500
    for i in range(0, len(text), max_length):
        resp.message(text[i:i + max_length])

# دالة البحث عن سورة (نفس المنطق السابق)
def get_surah_text(surah_name):
    surah = next((s for s in data if s['name']['ar'] == surah_name), None)
    if surah:
        verses = [f"{ayah['text']['ar']} ({ayah['number']})" for ayah in surah['verses']]
        response = f"*{surah['name']['ar']}*\n"
        if surah['number'] != 1 and surah['number'] != 9:
            response += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
        response += " ".join(verses)
        return response
    return None

# دالة البحث عن آية
def get_ayah_text(surah_name, start_ayah, end_ayah=None):
    surah = next((s for s in data if s['name']['ar'] == surah_name), None)
    if surah:
        if end_ayah is None:
            end_ayah = start_ayah
        if 1 <= start_ayah <= len(surah['verses']) and 1 <= end_ayah <= len(surah['verses']):
            verses = [f"{surah['verses'][i-1]['text']['ar']} ({surah['verses'][i-1]['number']})" for i in range(start_ayah, end_ayah + 1)]
            response = f"سورة {surah['name']['ar']} - الآيات {start_ayah}-{end_ayah}\n"
            response += " ".join(verses)
            return response
    return None

# دالة البحث عن صفحة
def get_page_text(page_number):
    verses = [f"{ayah['text']['ar']} ({ayah['number']})" for surah in data for ayah in surah['verses'] if ayah['page'] == page_number]
    if verses:
        response = f"*الصفحة {page_number}*\n" + " ".join(verses)
        return response
    return None

# دالة البحث عن جزء
def get_part_text(part_number):
    verses = [f"{ayah['text']['ar']} ({ayah['number']})" for surah in data for ayah in surah['verses'] if ayah['juz'] == part_number]
    if verses:
        response = f"*الجزء {part_number}*\n" + " ".join(verses)
        return response
    return None

@app.route("/bot", methods=['POST'])
def bot():
    # استقبال الرسالة من واتساب
    incoming_msg = request.values.get('Body', '').strip()
    sender_id = request.values.get('From', '')
    
    # تهيئة الاستجابة
    resp = MessagingResponse()
    
    # تهيئة حالة المستخدم إذا لم تكن موجودة
    if sender_id not in users_state:
        users_state[sender_id] = {'state': 'main', 'page_index': 0}
    
    user = users_state[sender_id]
    
    # --- القائمة الرئيسية والأوامر ---
    
    # 1. القائمة الرئيسية
    if incoming_msg.lower() in ['start', 'مرحبا', 'قائمة', 'menu']:
        user['state'] = 'main'
        msg = "*مرحباً بك في بوت القرآن الكريم 📖*\n\n"
        msg += "أرسل الرقم للاختيار:\n"
        msg += "1️⃣ عرض السور\n"
        msg += "2️⃣ عرض الأجزاء\n"
        msg += "3️⃣ عرض صفحة محددة\n\n"
        msg += "*أوامر البحث السريع:*\n"
        msg += "- `س البقرة` (للبحث عن سورة)\n"
        msg += "- `آ البقرة 255` (للبحث عن آية)\n"
        msg += "- `ص 5` (لعرض صفحة)\n"
        resp.message(msg)
        return str(resp)

    # 2. معالجة أوامر البحث المباشر (س، آ، ص)
    if incoming_msg.startswith("س "):
        surah_name = incoming_msg[2:].strip()
        text = get_surah_text(surah_name)
        if text:
            send_long_message(resp, text)
        else:
            resp.message("لم أتمكن من العثور على السورة.")
        return str(resp)

    elif incoming_msg.startswith("آ "):
        parts = incoming_msg[2:].strip().split()
        if len(parts) >= 2:
            surah_name = parts[0]
            try:
                start = int(parts[1])
                end = int(parts[3]) if len(parts) == 4 and parts[2] == 'إلى' else start
                text = get_ayah_text(surah_name, start, end)
                if text:
                    send_long_message(resp, text)
                else:
                    resp.message("لم أتمكن من العثور على الآية.")
            except ValueError:
                resp.message("تأكد من كتابة الأرقام بشكل صحيح.")
        else:
            resp.message("الصيغة: آ البقرة 5")
        return str(resp)

    elif incoming_msg.startswith("ص "):
        try:
            page = int(incoming_msg[2:].strip())
            text = get_page_text(page)
            if text:
                send_long_message(resp, text)
            else:
                resp.message("رقم الصفحة غير صحيح.")
        except ValueError:
            resp.message("يرجى إدخال رقم صحيح.")
        return str(resp)

    # --- معالجة الحالات (State Handling) ---

    # العودة للقائمة الرئيسية
    if incoming_msg == '0':
        user['state'] = 'main'
        resp.message("تم الرجوع للقائمة الرئيسية. أرسل 'قائمة' للعرض.")
        return str(resp)

    # معالجة اختيار المستخدم من القائمة الرئيسية
    if user['state'] == 'main':
        if incoming_msg == '1':
            user['state'] = 'browsing_surahs'
            user['page_index'] = 0
            # عرض الصفحة الأولى من السور
            show_surahs_list(resp, 0)
        elif incoming_msg == '2':
            user['state'] = 'browsing_parts'
            msg = "*اختر الجزء (أرسل رقم الجزء من 1-30):*\n"
            msg += "أو أرسل 0 للرجوع."
            resp.message(msg)
        elif incoming_msg == '3':
            user['state'] = 'awaiting_page_num'
            resp.message("أدخل رقم الصفحة التي تريدها (1-604):\nأو أرسل 0 للرجوع.")
        else:
            resp.message("خيار غير صحيح. أرسل 'قائمة' للبدء.")

    # حالة تصفح السور
    elif user['state'] == 'browsing_surahs':
        if incoming_msg == 'التالي' or incoming_msg == '+':
            user['page_index'] += 1
            show_surahs_list(resp, user['page_index'])
        elif incoming_msg == 'السابق' or incoming_msg == '-':
            if user['page_index'] > 0:
                user['page_index'] -= 1
            show_surahs_list(resp, user['page_index'])
        elif incoming_msg.isdigit():
            # المستخدم اختار رقم سورة
            surah_num = int(incoming_msg)
            surah = next((s for s in data if s['number'] == surah_num), None)
            if surah:
                text = get_surah_text(surah['name']['ar'])
                send_long_message(resp, text)
            else:
                resp.message("رقم سورة غير صحيح.")
        else:
            resp.message("أرسل رقم السورة، أو (+) للتالي، أو (-) للسابق، أو (0) للرجوع.")

    # حالة تصفح الأجزاء
    elif user['state'] == 'browsing_parts':
        if incoming_msg.isdigit():
            part = int(incoming_msg)
            if 1 <= part <= 30:
                text = get_part_text(part)
                send_long_message(resp, text)
            else:
                resp.message("الجزء يجب أن يكون بين 1 و 30.")
        else:
            resp.message("يرجى إرسال رقم الجزء فقط.")

    # حالة انتظار رقم الصفحة
    elif user['state'] == 'awaiting_page_num':
        if incoming_msg.isdigit():
            page = int(incoming_msg)
            text = get_page_text(page)
            if text:
                send_long_message(resp, text)
                user['state'] = 'main' # إعادة للقائمة الرئيسية بعد الطلب
            else:
                resp.message("رقم صفحة غير موجود.")
        else:
            resp.message("يرجى إرسال أرقام فقط.")

    return str(resp)

# دالة مساعدة لعرض قائمة السور كنص
def show_surahs_list(resp, page_index):
    surahs_per_page = 14
    start_index = page_index * surahs_per_page
    end_index = start_index + surahs_per_page
    current_surahs = data[start_index:end_index]
    
    if not current_surahs:
        resp.message("لا توجد سور أخرى.")
        return

    msg = f"*قائمة السور (صفحة {page_index + 1})*\n"
    msg += "أرسل رقم السورة لعرضها:\n\n"
    
    for surah in current_surahs:
        msg += f"{surah['number']}. {surah['name']['ar']}\n"
    
    msg += "\n--------\n"
    msg += "أرسل (+) للتالي\n"
    if page_index > 0:
        msg += "أرسل (-) للسابق\n"
    msg += "أرسل (0) للرجوع للقائمة الرئيسية"
    
    resp.message(msg)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
