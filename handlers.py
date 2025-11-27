import threading
import json
import os
from config import RECITERS_FILE, MAX_VERSES_TO_MERGE
from data_loader import QuranHandler
from whatsapp_client import GreenClient
from users_manager import UsersManager
from audio_mixer import AudioMixer

# تهيئة الكلاسات مرة واحدة هنا
quran = QuranHandler()
client = GreenClient()
users_mgr = UsersManager()
mixer = AudioMixer()

# تحميل بيانات القراء
with open(RECITERS_FILE, 'r', encoding='utf-8') as f:
    RECITERS_DATA = json.load(f)

# --- دوال مساعدة للقراء ---
def get_reciter_details(r_id):
    """جلب بيانات القارئ كاملة"""
    for r in RECITERS_DATA:
        if r['id'] == r_id:
            return r
    return RECITERS_DATA[0]

def get_formatted_reciters_list():
    """تجهيز قائمة القراء مع التفاصيل (الدقة والنوع)"""
    msg = "🎙️ *قائمة القراء المتاحين:*\n━━━━━━━━━━━━\n"
    for r in RECITERS_DATA:
        # إضافة تفاصيل لتمييز المكرر
        quality = f"{r.get('bitrate', '?')}kbps"
        rtype = r.get('type', '')
        msg += f"🆔 *{r['id']}* ➖ {r['name']}\n"
        msg += f"   └ {r['rewaya']} | {rtype} | 🔊 {quality}\n"
    
    msg += "\n📝 *للاختيار السريع:*\nأرسل حرف `ق` ورقم القارئ.\nمثال: `ق 2`"
    return msg

# --- المعالج الرئيسي (Router) ---
def handle_incoming_message(chat_id, text):
    text = text.strip()
    # توحيد النص (إزالة همزات)
    clean_text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    # جلب إعدادات المستخدم
    settings = users_mgr.get_user_settings(chat_id)
    print(f"📩 طلب من {chat_id}: {text}")

    # ==========================================
    # 1. أوامر الإعدادات والقراء (ق، إعدادات)
    # ==========================================
    
    # تغيير القارئ (ق [رقم])
    if clean_text.startswith("ق ") and clean_text.split()[1].isdigit():
        new_id = int(clean_text.split()[1])
        # هل الرقم موجود؟
        if any(r['id'] == new_id for r in RECITERS_DATA):
            users_mgr.update_setting(chat_id, 'reciter_id', new_id)
            r_info = get_reciter_details(new_id)
            client.send_text(chat_id, f"✅ تم اختيار القارئ:\n*{r_info['name']}*\n({r_info['rewaya']} - {r_info['bitrate']}kbps)")
        else:
            client.send_text(chat_id, "❌ رقم القارئ غير صحيح. أرسل `قراء` لعرض القائمة.")
        return

    # عرض القراء
    if clean_text in ['قراء', 'قرا', 'مشايخ']:
        client.send_text(chat_id, get_formatted_reciters_list())
        return

    # الإعدادات العامة
    if clean_text in ['اعدادات', 'إعدادات', 'ضبط']:
        curr_reciter = get_reciter_details(settings['reciter_id'])
        msg = f"⚙️ *إعداداتك:*\n\n"
        msg += f"🔊 الصوت: {'✅' if settings['audio_enabled'] else '❌'}\n"
        msg += f"📖 النص: {'✅' if settings['text_enabled'] else '❌'}\n"
        msg += f"👤 القارئ: {curr_reciter['name']} ({curr_reciter['bitrate']}k)\n\n"
        msg += "للتعديل أرسل: `صوت` أو `نص`"
        client.send_text(chat_id, msg)
        return

    # تبديل الصوت/النص
    if clean_text == 'صوت':
        new_val = not settings['audio_enabled']
        users_mgr.update_setting(chat_id, 'audio_enabled', new_val)
        client.send_text(chat_id, f"تم {'تفعيل ✅' if new_val else 'إيقاف ❌'} الصوت.")
        return
    if clean_text == 'نص':
        new_val = not settings['text_enabled']
        users_mgr.update_setting(chat_id, 'text_enabled', new_val)
        client.send_text(chat_id, f"تم {'تفعيل ✅' if new_val else 'إيقاف ❌'} النص.")
        return

    # ==========================================
    # 2. أوامر القرآن (س، ج، ص، آ)
    # ==========================================
    verses_to_send = []
    header_info = ""

    # أمر السورة (س [اسم] أو س [رقم])
    if clean_text.startswith("س "):
        query = text[2:].strip()
        # هل هو رقم؟ (س 18)
        if query.isdigit():
             verses_to_send = quran.get_surah(int(query))
        else:
             # هل هو اسم؟ (س الكهف)
             verses_to_send = quran.get_surah(query)
        
        if verses_to_send:
            header_info = f"سورة {verses_to_send[0]['sura_name']}"

    # أمر الجزء (ج [رقم])
    elif clean_text.startswith("ج "):
        try:
            verses_to_send = quran.get_juz(int(text[2:]))
            header_info = f"الجزء {text[2:]}"
        except: pass

    # أمر الصفحة (ص [رقم])
    elif clean_text.startswith("ص "):
        try:
            verses_to_send = quran.get_page(int(text[2:]))
            header_info = f"الصفحة {text[2:]}"
        except: pass
        
    # أمر الحزب (حزب [رقم])
    elif clean_text.startswith("حزب "):
        try:
            verses_to_send = quran.get_hizb(int(text[4:]))
            header_info = f"الحزب {text[4:]}"
        except: pass

    # أمر الآيات والمجالات (آ ...)
    elif clean_text.startswith("ا ") or clean_text.startswith("آ "):
        content = text.split(' ', 1)[1] # حذف حرف الأمر
        # التحقق من وجود مجال (إلى، -)
        if "-" in content or " الى " in content or " إلى " in content:
            # تنظيف الفواصل
            content = content.replace(" الى ", "-").replace(" إلى ", "-")
            parts = content.split("-")
            # الجزء الأول يحتوي الاسم وبداية الآية (مثال: البقرة 50)
            first_part = parts[0].strip()
            # الجزء الثاني هو النهاية (مثال: 90)
            end_num = int(parts[1].strip())
            
            # فصل اسم السورة عن رقم البداية
            last_space = first_part.rfind(" ")
            sura_name = first_part[:last_space].strip()
            start_num = int(first_part[last_space:].strip())
            
            verses_to_send = quran.get_ayah_range(sura_name, start_num, end_num)
            header_info = f"آيات من {sura_name}"
        else:
            # آية مفردة (آ البقرة 50)
            parts = content.split()
            ayah_num = int(parts[-1])
            sura_name = " ".join(parts[:-1])
            v = quran.get_ayah(sura_name, ayah_num)
            if v:
                verses_to_send = [v]
                header_info = f"آية {ayah_num} من {sura_name}"

    # ==========================================
    # 3. التنفيذ
    # ==========================================
    if verses_to_send:
        # إرسال النص
        if settings['text_enabled']:
            if len(verses_to_send) > 50:
                 client.send_text(chat_id, f"⏳ جاري تحضير النص: {header_info}...")
            
            full_text = format_text_msg(verses_to_send, header_info)
            threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()

        # إرسال الصوت (مونتاج)
        if settings['audio_enabled']:
            threading.Thread(target=process_audio_request, args=(chat_id, verses_to_send, settings)).start()
        
        return

    # إذا لم يكن أمراً معروفاً (ولا رقم مباشر)
    # نرسل الترحيب فقط
    client.send_text(chat_id, get_welcome_text())

# --- دوال المعالجة الخلفية ---
def format_text_msg(verses, title):
    msg = f"🕌 *{title}* 🕌\n━━━━━━━━━━━━\n\n"
    # بسملة
    if verses[0]['numberInSurah'] == 1 and verses[0]['sura_nu
