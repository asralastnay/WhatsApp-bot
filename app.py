import os
import time
import requests
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
app = Flask(name)
مجلد التخزين المؤقت
DOWNLOAD_FOLDER = 'static'
if not os.path.exists(DOWNLOAD_FOLDER):
os.makedirs(DOWNLOAD_FOLDER)
user_requests = {}
def download_file_locally(url, filename):
"""
تقوم هذه الدالة بتنزيل الملف من الرابط المباشر وحفظه داخل السيرفر
لضمان إرساله كملف وليس كرابط
"""
try:
# إرسال طلب للحصول على الملف (stream)
with requests.get(url, stream=True) as r:
r.raise_for_status()
local_path = os.path.join(DOWNLOAD_FOLDER, filename)
Code
 
 
 
with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
        
        return local_path
except Exception as e:
    print(f"Error downloading locally: {e}")
    return None
def get_cobalt_url(youtube_url, is_audio=False):
"""الاتصال بخدمة Cobalt للحصول على رابط مباشر"""
api_url = "https://api.cobalt.tools/api/json"
headers = {"Accept": "application/json", "Content-Type": "application/json"}
Code
 
 
 
# نطلب جودة 480 فقط لأن واتساب لا يقبل الجودات العالية (حجم كبير)
payload = {
    "url": youtube_url,
    "vQuality": "480", 
    "isAudioOnly": is_audio,
    "aFormat": "mp3" if is_audio else None
}

try:
    response = requests.post(api_url, json=payload, headers=headers)
    data = response.json()
    
    if 'url' in data:
        return data['url']
    elif 'picker' in data:
        for item in data['picker']:
            if 'url' in item:
                return item['url']
    return None
except:
    return None
@app.route('/bot', methods=['POST'])
def bot():
incoming_msg = request.values.get('Body', '').strip()
sender = request.values.get('From', '')
Code
 
 
 
resp = MessagingResponse()
msg = resp.message()

# 1. استقبال الرابط
if "youtube.com" in incoming_msg or "youtu.be" in incoming_msg:
    user_requests[sender] = incoming_msg
    msg.body("✅ تم استلام الرابط!\n\nاختر:\n1️⃣ صوت (MP3)\n2️⃣ فيديو (MP4)\n\n⚠️ ملاحظة: واتساب لا يقبل الفيديوهات الطويلة (أكثر من 5 دقائق).")
    return str(resp)

# 2. معالجة الطلب
elif sender in user_requests:
    youtube_url = user_requests[sender]
    is_audio = (incoming_msg == '1')
    
    if incoming_msg not in ['1', '2']:
        msg.body("الرجاء إرسال 1 أو 2 فقط.")
        return str(resp)

    # رسالة انتظار لأن العملية ستأخذ وقتاً
    # ملاحظة: واتساب قد لا يظهر هذه الرسالة فوراً إذا تأخر السيرفر في المعالجة،
    # لكننا سنحاول المعالجة.
    
    # جلب الرابط المباشر
    direct_url = get_cobalt_url(youtube_url, is_audio)
    
    if not direct_url:
        msg.body("❌ فشل جلب الفيديو. قد يكون محمياً أو محظوراً.")
        del user_requests[sender]
        return str(resp)

    # تحديد اسم الملف
    ext = 'mp3' if is_audio else 'mp4'
    filename = f"{sender.replace('whatsapp:', '').replace('+', '')}_{int(time.time())}.{ext}"
    
    # تحميل الملف إلى سيرفر Render
    local_path = download_file_locally(direct_url, filename)
    
    if local_path:
        # التحقق من الحجم (واتساب يرفض أكثر من 16 ميجا بايت تقريباً في البوتات)
        file_size = os.path.getsize(local_path) / (1024 * 1024) # بالميجابايت
        
        if file_size > 19: # حددنا 19 للاحتياط
            msg.body(f"❌ عذراً، حجم الملف ({file_size:.1f}MB) أكبر من الحد المسموح به في واتساب (16MB).\nحاول تحميل مقطع أقصر.")
        else:
            # إعداد رابط الملف الموجود على سيرفرنا
            server_file_url = request.host_url + 'static/' + filename
            
            # إرسال الوسائط
            msg_media = resp.message("")
            msg_media.media(server_file_url)
            msg_media.body("تم التحميل! 📦")
    else:
        msg.body("❌ حدث خطأ أثناء تنزيل الملف للسيرفر.")
        
    del user_requests[sender]

else:
    msg.body("أرسل رابط يوتيوب للبدء.")

return str(resp)
هذا الجزء مهم جداً للسماح لواتساب بسحب الملف من سيرفرنا
@app.route('/static/path:filename')
def serve_static(filename):
return send_from_directory('static', filename)
if name == 'main':
app.run(host='0.0.0.0', port=5000)
