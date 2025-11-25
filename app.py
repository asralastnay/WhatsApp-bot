import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import yt_dlp

app = Flask(__name__)

user_requests = {}

def download_media(url, type_choice):
    # تحديد المسار
    output_path = 'static/%(id)s.%(ext)s'
    
    # إعدادات التحميل المتقدمة لتخطي الحظر
    ydl_opts = {
        'outtmpl': output_path,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        
        # هذه الإعدادات الجديدة المهمة جداً:
        # نستخدم عميل أندرويد لتخطي مشكلة "Sign in to confirm"
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['dash', 'hls'],
            }
        },
        # إضافة معلومات متصفح وهمية
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    if type_choice == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        # نختار جودة 480 أو 360 لتجنب الحجم الكبير الذي يرفضه واتساب
        ydl_opts['format'] = 'best[ext=mp4][height<=480]/best[ext=mp4][height<=360]'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # تصحيح اسم الملف لضمان توافقه مع الرابط
            filename = os.path.basename(filename)
            
            base_url = request.host_url
            # تأكد من أن الرابط يشير لمجلد static بشكل صحيح
            if not base_url.endswith('/'):
                base_url += '/'
            
            file_url = base_url + 'static/' + filename
            return file_url, info.get('title', 'Media')
            
    except Exception as e:
        print(f"Error downloading: {e}")
        return None, None

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    resp = MessagingResponse()
    msg = resp.message()

    # استقبال الرابط
    if "youtube.com" in incoming_msg or "youtu.be" in incoming_msg:
        user_requests[sender] = incoming_msg
        msg.body("تم استلام الرابط! 📥\nاختر الصيغة:\n1️⃣ صوت (MP3)\n2️⃣ فيديو (MP4)")
        return str(resp)

    # استقبال الخيار
    elif sender in user_requests:
        url = user_requests[sender]
        
        if incoming_msg == '1':
            msg.body("⏳ جاري تحميل الصوت... (قد يستغرق دقيقة)")
            file_link, title = download_media(url, 'audio')
            if file_link:
                # نرسل رسالة جديدة بالرابط لأن التحميل قد يأخذ وقتاً
                # ملاحظة: Twilio يسمح برد واحد مباشر، لذا سنضع الرابط في الرد
                msg = resp.message("") # نعيد تهيئة الرسالة
                msg.media(file_link)
                msg.body(f"🎧 {title}")
            else:
                msg.body("❌ فشل التحميل. قد يكون الفيديو طويلاً جداً أو مقيداً.")
            
            del user_requests[sender]

        elif incoming_msg == '2':
            msg.body("⏳ جاري تحميل الفيديو... (قد يستغرق دقيقة)")
            file_link, title = download_media(url, 'video')
            if file_link:
                msg = resp.message("")
                msg.media(file_link)
                msg.body(f"🎬 {title}")
            else:
                msg.body("❌ فشل التحميل. حاول اختيار فيديو أقصر.")
            
            del user_requests[sender]

        else:
            msg.body("الرجاء إرسال 1 أو 2 فقط.")
    
    else:
        msg.body("أرسل رابط يوتيوب للبدء. 🎥")

    return str(resp)

# لضمان تقديم الملفات من مجلد static
from flask import send_from_directory

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host='0.0.0.0', port=5000)
