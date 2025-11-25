import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# تخزين مؤقت لطلبات المستخدمين (رقم المرسل: الرابط)
user_requests = {}

def get_cobalt_url(youtube_url, is_audio=False):
    """جلب الرابط المباشر من Cobalt بأسرع طريقة"""
    try:
        api_url = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        payload = {
            "url": youtube_url,
            "vQuality": "480", # جودة متوسطة لضمان السرعة وقبول واتساب
            "isAudioOnly": is_audio,
            "aFormat": "mp3" if is_audio else None
        }

        # نطلب الرابط بمهلة زمنية قصيرة (10 ثواني) لضمان عدم توقف البوت
        response = requests.post(api_url, json=payload, headers=headers, timeout=12)
        data = response.json()
        
        # محاولة استخراج الرابط
        if 'url' in data:
            return data['url']
        elif 'picker' in data:
            for item in data['picker']:
                if 'url' in item:
                    return item['url']
        return None
    except Exception as e:
        print(f"Error extracting URL: {e}")
        return None

@app.route('/bot', methods=['POST'])
def bot():
    # استلام الرسالة
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    # تجهيز الرد (بدون مفاتيح، رد مباشر فقط)
    resp = MessagingResponse()
    msg = resp.message()

    # --- الحالة 1: المستخدم أرسل رابط يوتيوب ---
    if "youtu" in incoming_msg.lower():
        user_requests[sender] = incoming_msg
        msg.body("✅ استلمت الرابط!\n\nاختر الصيغة المطلوبة بسرعة:\n1️⃣ صوت (MP3)\n2️⃣ فيديو (MP4)")
        return str(resp)

    # --- الحالة 2: المستخدم اختار 1 أو 2 ---
    elif sender in user_requests:
        selection = incoming_msg
        
        if selection not in ['1', '2']:
            msg.body("الرجاء إرسال رقم 1 أو 2 فقط.")
            return str(resp)

        youtube_url = user_requests[sender]
        is_audio = (selection == '1')

        # محاولة جلب الرابط المباشر
        direct_url = get_cobalt_url(youtube_url, is_audio)

        if direct_url:
            # هنا الحركة الذكية: نعطي واتساب الرابط وهو يقوم بالباقي
            msg.body("جاري التحميل... 📦")
            msg.media(direct_url)
        else:
            msg.body("❌ عذراً، لم أتمكن من جلب هذا الفيديو (قد يكون محمياً أو المصدر مشغول).")
        
        # مسح الطلب من الذاكرة
        del user_requests[sender]
        return str(resp)

    # --- الحالة 3: رسالة ترحيب ---
    else:
        msg.body("مرحباً! أرسل لي رابط فيديو من يوتيوب لأقوم بتحميله لك.")
        return str(resp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
