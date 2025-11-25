import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import yt_dlp

app = Flask(__name__)

# تخزين مؤقت لحالة المستخدم (الرابط الذي أرسله)
# format: {'phone_number': 'youtube_link'}
user_requests = {}

# إعدادات Twilio (سنحصل عليها لاحقاً من الموقع)
# لكن في الرد التلقائي (Webhook) قد لا نحتاج وضع الـ SID والـ Token مباشرة للإرسال البسيط
# سنعتمد على مكتبة TwiML للرد المباشر

def download_media(url, type_choice):
    """
    دالة لتحميل الفيديو أو الصوت وإرجاع رابط الملف المباشر
    ملاحظة: في بيئة السيرفر الحقيقية، يجب رفع الملف لسحابة وتوفير رابط، 
    ولكن هنا سنعتمد على رابط مباشر من yt-dlp إذا توفر أو نحفظه في مجلد static
    """
    ydl_opts = {
        'outtmpl': 'static/%(id)s.%(ext)s',
        'format': 'bestaudio/best' if type_choice == 'audio' else 'best[ext=mp4][height<=480]', # جودة متوسطة لتناسب واتساب
        'noplaylist': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # الحصول على رابط السيرفر الحالي لإرساله لواتساب
            base_url = request.host_url
            file_url = base_url + filename
            return file_url, info.get('title', 'Media')
    except Exception as e:
        print(f"Error: {e}")
        return None, None

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    resp = MessagingResponse()
    msg = resp.message()

    # 1. إذا أرسل المستخدم رابط يوتيوب
    if "youtube.com" in incoming_msg or "youtu.be" in incoming_msg:
        user_requests[sender] = incoming_msg
        msg.body("تم استلام الرابط! 📥\nيرجى اختيار الصيغة:\n1️⃣ للتحميل كملف صوتي (MP3)\n2️⃣ للتحميل كفيديو (MP4)")
        return str(resp)

    # 2. التحقق من رد المستخدم (1 أو 2)
    elif sender in user_requests:
        url = user_requests[sender]
        
        if incoming_msg == '1':
            msg.body("جاري تحميل الصوت... 🎵\nقد يستغرق ذلك بضع ثوانٍ.")
            # هنا عملية التحميل (قد تأخذ وقتاً)
            # ملاحظة: واتساب لديه وقت استجابة قصير، للمعالجة الطويلة يفضل استخدام Background Tasks
            # ولكن للتبسيط سنقوم بها هنا
            file_link, title = download_media(url, 'audio')
            if file_link:
                msg = resp.message("")
                msg.media(file_link)
                msg.body(f"🎧 {title}")
            else:
                msg.body("عذراً، حدث خطأ أثناء التحميل.")
            
            del user_requests[sender] # مسح الحالة

        elif incoming_msg == '2':
            msg.body("جاري تحميل الفيديو... 🎬\nقد يستغرق ذلك بضع ثوانٍ.")
            file_link, title = download_media(url, 'video')
            if file_link:
                msg = resp.message("")
                msg.media(file_link)
                msg.body(f"🎬 {title}")
            else:
                msg.body("عذراً، حدث خطأ أثناء التحميل أو الفيديو كبير جداً.")
            
            del user_requests[sender]

        else:
            msg.body("الرجاء إرسال رقم 1 للصوت أو 2 للفيديو فقط.")
    
    # 3. رسالة ترحيبية أو خطأ
    else:
        msg.body("أهلاً بك! 👋\nأرسل لي رابط يوتيوب وسأقوم بتحميله لك.")

    return str(resp)

if __name__ == '__main__':
    # إنشاء مجلد static إذا لم يكن موجوداً
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host='0.0.0.0', port=5000)