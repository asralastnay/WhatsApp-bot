import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# تصحيح تعريف الفلاسك
app = Flask(__name__)

# تخزين مؤقت لطلبات المستخدمين
user_requests = {}

def get_cobalt_url(youtube_url, is_audio=False):
    """
    الاتصال بخدمة Cobalt للحصول على رابط مباشر
    نستخدم إعدادات لتقليل حجم الفيديو لضمان قبول واتساب له
    """
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json", 
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Compatible; WhatsAppBot/1.0)"
    }
    
    # الإعدادات: نطلب 480p للفيديو ليكون خفيفاً وسريعاً
    payload = {
        "url": youtube_url,
        "vQuality": "480", 
        "isAudioOnly": is_audio,
        "aFormat": "mp3" if is_audio else None
    }

    try:
        # مهلة 10 ثواني فقط لكي لا يتأخر الرد على واتساب
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        data = response.json()
        
        # محاولات استخراج الرابط من أشكال الاستجابة المختلفة
        if 'url' in data:
            return data['url']
        elif 'picker' in data:
            for item in data['picker']:
                if 'url' in item:
                    return item['url']
        return None
    except Exception as e:
        print(f"Error getting URL: {e}")
        return None

@app.route('/bot', methods=['POST'])
def bot():
    # استقبال البيانات
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    resp = MessagingResponse()
    msg = resp.message()

    # --- الحالة 1: المستخدم أرسل رابط يوتيوب ---
    # نستقبل الرابط ونحفظه في الذاكرة وننتظر الاختيار
    if "youtu" in incoming_msg.lower():
        user_requests[sender] = incoming_msg
        msg.body("✅ تم استلام الرابط!\n\nاختر الصيغة:\n1️⃣ صوت (MP3)\n2️⃣ فيديو (MP4)")
        return str(resp)

    # --- الحالة 2: المستخدم اختار 1 أو 2 ---
    elif sender in user_requests:
        selection = incoming_msg
        
        # التأكد من صحة الاختيار
        if selection not in ['1', '2']:
            msg.body("الرجاء إرسال رقم 1 أو 2 فقط.")
            return str(resp)

        youtube_url = user_requests[sender]
        is_audio = (selection == '1')
        
        # جلب الرابط المباشر
        direct_url = get_cobalt_url(youtube_url, is_audio)
        
        if direct_url:
            # الحل السحري: بدلاً من التحميل للسيرفر (الذي يأخذ وقتاً ويفصل البوت)
            # نعطي واتساب الرابط المباشر وهو يقوم بالباقي
            msg.body("تم المعالجة! 📦\nجاري إرسال الملف...")
            msg.media(direct_url)
        else:
            msg.body("❌ فشل جلب الفيديو. قد يكون محمياً أو المصدر مشغول.")
            
        # مسح الطلب من الذاكرة لتوفير المساحة
        del user_requests[sender]
        return str(resp)

    # --- الحالة 3: رسالة ترحيب ---
    else:
        msg.body("أهلاً بك! 🤖\nأرسل رابط فيديو من يوتيوب للبدء.")
        return str(resp)

@app.route('/')
def home():
    return "Bot is running perfectly! 🚀"

if __name__ == '__main__':
    # تشغيل التطبيق
    app.run(host='0.0.0.0', port=5000)
