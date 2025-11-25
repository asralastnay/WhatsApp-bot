import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

user_requests = {}

def get_media_link(url, is_audio=False):
    """
    دالة تتصل بـ API خارجي (Cobalt) لجلب رابط التحميل المباشر
    لتجنب حظر يوتيوب لسيرفرات Render
    """
    # نستخدم سيرفر Cobalt العام
    api_url = "https://api.cobalt.tools/api/json"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": url,
        # إذا كان صوت نطلب MP3، وإلا فيديو MP4 جودة 480 (للواتساب)
        "vCodec": "h264",
        "vQuality": "480",
        "isAudioOnly": is_audio,
        "aFormat": "mp3" if is_audio else None
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        data = response.json()
        
        # التحقق مما إذا كان هناك رابط مباشر
        if 'url' in data:
            return data['url']
        elif 'picker' in data:
            # أحياناً يعطي عدة خيارات، نأخذ أول واحد
            for item in data['picker']:
                if 'url' in item:
                    return item['url']
        
        print(f"API Error: {data}")
        return None
        
    except Exception as e:
        print(f"Request Error: {e}")
        return None

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    resp = MessagingResponse()
    msg = resp.message()

    # 1. استقبال الرابط
    if "youtube.com" in incoming_msg or "youtu.be" in incoming_msg:
        user_requests[sender] = incoming_msg
        msg.body("✅ تم استلام الرابط!\nبسبب حظر يوتيوب للسيرفرات، سنستخدم طريقة بديلة.\n\nاختر الصيغة:\n1️⃣ صوت (MP3)\n2️⃣ فيديو (MP4)")
        return str(resp)

    # 2. معالجة الاختيار
    elif sender in user_requests:
        youtube_url = user_requests[sender]
        
        if incoming_msg == '1':
            msg.body("🎵 جاري جلب رابط الصوت...")
            direct_link = get_media_link(youtube_url, is_audio=True)
            
            if direct_link:
                # نرسل الرابط المباشر كملف
                msg = resp.message("")
                msg.media(direct_link)
                msg.body("تم الجلب بنجاح! 🎧")
            else:
                msg.body("عذراً، لم نتمكن من جلب الرابط لهذا الفيديو. حاول بفيديو آخر.")
            
            del user_requests[sender]

        elif incoming_msg == '2':
            msg.body("🎬 جاري جلب رابط الفيديو...")
            direct_link = get_media_link(youtube_url, is_audio=False)
            
            if direct_link:
                msg = resp.message("")
                msg.media(direct_link)
                msg.body("تم الجلب بنجاح! 🎬")
            else:
                msg.body("عذراً، لم نتمكن من جلب الرابط. قد يكون الفيديو طويلاً جداً أو مقيداً.")
            
            del user_requests[sender]

        else:
            msg.body("الرجاء إرسال رقم 1 أو 2 فقط.")
    
    # 3. رسالة الترحيب
    else:
        msg.body("مرحباً! 👋\nأنا بوت تحميل من يوتيوب.\nأرسل لي الرابط وسأحاول جلبه لك.")

    return str(resp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
