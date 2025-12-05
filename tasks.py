import threading
import time
import os
import json
from config import RECITERS_FILE, MAX_VERSES_TO_MERGE
from audio_mixer import AudioMixer
from whatsapp_client import GreenClient
import messages as msg  # استيراد ملف الرسائل الجديد

# تهيئة الأدوات
mixer = AudioMixer()
client = GreenClient()

# تحميل بيانات القراء مرة واحدة عند تشغيل الملف
try:
    with open(RECITERS_FILE, 'r', encoding='utf-8') as f:
        RECITERS_DATA = json.load(f)
except Exception as e:
    print(f"❌ Error loading reciters: {e}")
    RECITERS_DATA = []

# ==========================================
# 1. دوال مساعدة (Helpers)
# ==========================================
def get_reciter_details(r_id):
    """جلب بيانات القارئ من القائمة المحملة"""
    for r in RECITERS_DATA:
        if r['id'] == r_id:
            return r
    # إرجاع القارئ الأول كاحتياطي إذا لم يتم العثور على الرقم
    return RECITERS_DATA[0] if RECITERS_DATA else {}

def get_reciters_data():
    """إرجاع بيانات القراء لاستخدامها في ملفات أخرى"""
    return RECITERS_DATA

def schedule_delete(file_path, delay=300):
    """
    مهمة خلفية لحذف الملفات المؤقتة بعد فترة محددة
    """
    def _delete():
        try:
            time.sleep(delay)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Task: Deleted cached file {file_path}")
        except Exception as e:
            print(f"❌ Task Error (Delete): {e}")
            
    # تشغيل الحذف في خيط منفصل (Daemon Thread)
    threading.Thread(target=_delete, daemon=True).start()

# ==========================================
# 2. المهمة الرئيسية: معالجة الصوت (Audio Task)
# ==========================================
def process_audio_request(chat_id, verses, settings, repeat_count):
    """
    تقوم هذه الدالة بـ:
    1. التحقق من الحدود المسموحة.
    2. إرسال رسالة انتظار.
    3. دمج الصوت (مع التكرار).
    4. إرسال الملف الناتج.
    5. جدولة حذف الملف.
    """
    
    # 1. التحقق من الحد الأقصى للآيات
    # إذا كان التكرار مفعلاً، نخفض الحد المسموح به إلى 20 آية لتجنب الملفات الضخمة
    effective_limit = MAX_VERSES_TO_MERGE
    if repeat_count > 1:
        effective_limit = 20 
    
    if len(verses) > effective_limit:
        client.send_text(chat_id, msg.err_too_many_verses(effective_limit))
        return

    # 2. إرسال رسالة "جاري التحضير"
    client.send_text(chat_id, msg.msg_preparing_audio(repeat_count))
    
    # 3. تجهيز البيانات للدمج
    reciter_id = settings.get('reciter_id', 1)
    reciter = get_reciter_details(reciter_id)
    
    if not reciter:
        client.send_text(chat_id, msg.ERR_GENERAL)
        return

    reciter_url = reciter['url']
    verses_data = [{'sura': v['sura_number'], 'ayah': v['numberInSurah']} for v in verses]
    
    try:
        # استدعاء الميكسر (عملية ثقيلة قد تستغرق وقتاً)
        file_path = mixer.merge_verses(verses_data, reciter_url, reciter_id, repeat_count)
        
        if file_path:
            # تجهيز العنوان (Caption)
            caption = msg.caption_audio(reciter['name'], repeat_count)
            
            # 4. إرسال الملف
            client.send_file(chat_id, file_path, caption=caption)
            
            # 5. جدولة الحذف التلقائي
            schedule_delete(file_path, delay=300) # 5 دقائق
        else:
            client.send_text(chat_id, msg.ERR_AUDIO_NOT_FOUND)
            
    except Exception as e:
        print(f"❌ Audio Processing Error: {e}")
        client.send_text(chat_id, msg.ERR_GENERAL)

# ==========================================
# 3. مهمة معالجة النص (Text Task)
# ==========================================
def process_text_request(chat_id, verses, header_info):
    """
    تجهيز النص وإرساله (في خيط منفصل لتجنب تعليق البوت إذا كان النص طويلاً)
    """
    try:
        # إذا كان العدد كبيراً، نرسل تنبيهاً
        if len(verses) > 50:
             client.send_text(chat_id, msg.msg_preparing_text(header_info))
        
        # استخدام دالة التنسيق من ملف messages.py
        full_text = msg.format_quran_text(verses, header_info)
        
        client.send_text(chat_id, full_text)
        
    except Exception as e:
        print(f"❌ Text Processing Error: {e}")
