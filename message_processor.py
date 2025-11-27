import threading
import os
import json
from config import RECITERS_FILE, MAX_VERSES_TO_MERGE
from data_loader import QuranHandler
from whatsapp_client import GreenClient
from users_manager import UsersManager
from audio_mixer import AudioMixer

# --- تهيئة الكلاسات ---
quran = QuranHandler()
client = GreenClient()
users_mgr = UsersManager()
mixer = AudioMixer()

# تحميل بيانات القراء
with open(RECITERS_FILE, 'r', encoding='utf-8') as f:
    RECITERS_DATA = json.load(f)

# --- دوال مساعدة ---
def get_reciter_url(reciter_id):
    """جلب رابط القارئ بناء على الـ ID"""
    for r in RECITERS_DATA:
        if r['id'] == reciter_id:
            return r['url']
    return RECITERS_DATA[0]['url'] # الافتراضي

def get_reciter_name(reciter_id):
    for r in RECITERS_DATA:
        if r['id'] == reciter_id:
            return r['name']
    return "غير معروف"

# --- المعالج الرئيسي للرسائل ---
def process_message(chat_id, text):
    text = text.strip()
    clean_text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    # 1. جلب إعدادات المستخدم
    settings = users_mgr.get_user_settings(chat_id)
    
    print(f"📩 طلب من {chat_id}: {text} | الإعدادات: {settings}")

    # =========================================================
    # قسم الإعدادات (Settings)
    # =========================================================
    if clean_text in ['اعدادات', 'إعدادات', 'ضبط', 'settings']:
        msg = f"⚙️ *إعداداتك الحالية:*\n\n"
        msg += f"🔊 *الصوت:* {'✅ مفعل' if settings['audio_enabled'] else '❌ متوقف'}\n"
        msg += f"📖 *النص:* {'✅ مفعل' if settings['text_enabled'] else '❌ متوقف'}\n"
        msg += f"👤 *القارئ:* {get_reciter_name(settings['reciter_id'])}\n\n"
        msg += "👇 *للتعديل أرسل:*\n"
        msg += "• `صوت` (لتبديل حالة الصوت)\n"
        msg += "• `نص` (لتبديل حالة النص)\n"
        msg += "• `قارئ` (لتغيير الشيخ)"
        client.send_text(chat_id, msg)
        return

    if clean_text == 'صوت':
        new_val = not settings['audio_enabled']
        users_mgr.update_setting(chat_id, 'audio_enabled', new_val)
        client.send_text(chat_id, f"تم {'تفعيل ✅' if new_val else 'إيقاف ❌'} الرسائل الصوتية.")
        return

    if clean_text == 'نص':
        new_val = not settings['text_enabled']
        users_mgr.update_setting(chat_id, 'text_enabled', new_val)
        client.send_text(chat_id, f"تم {'تفعيل ✅' if new_val else 'إيقاف ❌'} الرسائل النصية.")
        return

    if clean_text == 'قارئ':
        msg = "🎙️ *قائمة القراء المتاحين:*\n\n"
        for r in RECITERS_DATA:
            msg += f"{r['id']}. {r['name']} ({r['rewaya']})\n"
        msg += "\nللاختيار أرسل كلمة `قارئ` ثم الرقم.\nمثال: `قارئ 2`"
        client.send_text(chat_id, msg)
        return

    if clean_text.startswith('قارئ ') and clean_text.split()[1].isdigit():
        new_id = int(clean_text.split()[1])
        # التحقق من وجود القارئ
        if any(r['id'] == new_id for r in RECITERS_DATA):
            users_mgr.update_setting(chat_id, 'reciter_id', new_id)
            client.send_text(chat_id, f"✅ تم تغيير القارئ إلى: *{get_reciter_name(new_id)}*")
        else:
            client.send_text(chat_id, "❌ رقم القارئ غير صحيح.")
        return

    # =========================================================
    # قسم معالجة القرآن (بحث وتنفيذ)
    # =========================================================
    verses_to_send = []
    header_info = ""

    # 1. البحث بالرقم (سورة)
    if clean_text.isdigit():
        sura_num = int(clean_text)
        if 1 <= sura_num <= 114:
            verses_to_send = quran.get_surah(sura_num)
            s_name = quran.get_surah_name_by_number(sura_num)
            header_info = f"سورة {s_name}"

    # 2. أوامر السور (س ...)
    elif clean_text.startswith("س "):
        verses_to_send = quran.get_surah(text[2:])
        if verses_to_send:
            header_info = f"سورة {verses_to_send[0]['sura_name']}"

    # 3. أوامر الأجزاء (ج ...)
    elif clean_text.startswith("ج "):
        try:
            juz_num = int(text[2:])
            verses_to_send = quran.get_juz(juz_num)
            header_info = f"الجزء {juz_num}"
        except: pass

    # 4. أوامر الصفحات (ص ...)
    elif clean_text.startswith("ص "):
        try:
            page_num = int(text[2:])
            verses_to_send = quran.get_page(page_num)
            header_info = f"الصفحة {page_num}"
        except: pass
        
    # 5. أوامر الأحزاب (حزب ...)
    elif clean_text.startswith("حزب "):
        try:
            hizb_num = int(text[4:])
            verses_to_send = quran.get_hizb(hizb_num)
            header_info = f"الحزب {hizb_num}"
        except: pass

    # 6. أوامر الآيات (آ ...)
    elif clean_text.startswith("ا ") or clean_text.startswith("آ "):
        # منطق الآيات والمجالات (نفس السابق)
        try:
            content = text.split(' ', 1)[1]
            if "-" in content or " الى " in content:
                # معالجة المجال
                content = content.replace(" الى ", "-").replace(" إلى ", "-")
                parts = content.split("-")
                last_space = parts[0].rfind(" ")
                name = parts[0][:last_space].strip()
                start = int(parts[0][last_space:].strip())
                end = int(parts[1].strip())
                verses_to_send = quran.get_ayah_range(name, start, end)
                header_info = f"آيات من سورة {name}"
            else:
                # آية مفردة
                parts = content.split()
                ayah_num = int(parts[-1])
                name = " ".join(parts[:-1])
                v = quran.get_ayah(name, ayah_num)
                if v: 
                    verses_to_send = [v]
                    header_info = f"آية {ayah_num} من {name}"
        except: pass

    # --- التنفيذ (إرسال النتائج) ---
    if verses_to_send:
        # 1. إرسال النص (إذا كان مفعلاً)
        if settings['text_enabled']:
            # إرسال رسالة انتظار إذا كانت الكمية كبيرة
            if len(verses_to_send) > 50:
                client.send_text(chat_id, f"⏳ جاري تحضير النص لـ {header_info}...")
            
            # تنسيق النص وإرساله
            formatted_text = format_verses_text(verses_to_send, header_info)
            threading.Thread(target=client.send_text, args=(chat_id, formatted_text)).start()

        # 2. إرسال الصوت (إذا كان مفعلاً)
        if settings['audio_enabled']:
            threading.Thread(target=handle_audio_sending, args=(chat_id, verses_to_send, settings)).start()
        
        return # تم التنفيذ

    # إذا لم نفهم الرسالة، نرسل الترحيب
    client.send_text(chat_id, get_welcome_message())

# --- دوال المعالجة الخلفية ---

def format_verses_text(verses, title):
    """تنسيق النص بشكل جميل"""
    text = f"🕋 *{title}* 🕋\n━━━━━━━━━━━━\n\n"
    
    # البسملة إذا كانت بداية سورة (وليست الفاتحة أو التوبة)
    first_v = verses[0]
    if first_v['numberInSurah'] == 1 and first_v['sura_number'] not in [1, 9]:
        text += "﷽\n\n"

    for v in verses:
        # إضافة علامة السجدة
        sajda = " ۩" if v['sajda'] else ""
        text += f"{v['text']}{sajda} ({v['numberInSurah']}) "
    
    return text

def handle_audio_sending(chat_id, verses, settings):
    """إدارة عملية المونتاج والإرسال"""
    
    # التحقق من الكمية
    if len(verses) > MAX_VERSES_TO_MERGE:
        client.send_text(chat_id, "⚠️ *تنبيه:* عدد الآيات كبير جداً للدمج الصوتي. سيتم إرسال النص فقط حالياً.")
        return

    client.send_text(chat_id, "🎧 *جاري تحضير الملف الصوتي (المونتاج)... يرجى الانتظار*")
    
    # 1. جلب رابط القارئ المفضل
    reciter_url = get_reciter_url(settings['reciter_id'])
    
    # 2. تجهيز القائمة للمونتاج
    # AudioMixer يحتاج format: [{'sura': 1, 'ayah': 1}]
    verses_for_mixer = []
    for v in verses:
        verses_for_mixer.append({
            'sura': v['sura_number'],
            'ayah': v['numberInSurah']
        })
    
    # 3. استدعاء المونتاج
    try:
        merged_file_path = mixer.merge_verses(verses_for_mixer, reciter_url)
        
        if merged_file_path and os.path.exists(merged_file_path):
            print(f"✅ تم الدمج بنجاح: {merged_file_path}")
            # إرسال الملف
            client.send_file(chat_id, merged_file_path)
            
            # تنظيف (حذف الملف بعد الإرسال لتوفير المساحة)
            # ننتظر قليلاً لضمان رفعه
            # (في التطبيق الحقيقي يفضل عمل cron job للتنظيف، لكن هنا نحذفه مباشرة)
            # os.remove(merged_file_path) # فعل هذا السطر إذا أردت الحذف الفوري
        else:
            client.send_text(chat_id, "❌ حدث خطأ أثناء دمج الصوت.")
            
    except Exception as e:
        print(f"Audio Error: {e}")
        client.send_text(chat_id, "❌ فشل في معالجة الصوت.")

def get_welcome_message():
    return (
        "🕌 *أهلاً بك في بوت القرآن الذكي*\n\n"
        "أرسل رقم السورة أو اسمها للاستماع والقراءة.\n\n"
        "⚙️ *للتحكم:* أرسل كلمة `إعدادات` لتغيير القارئ أو إيقاف الصوت/النص.\n\n"
        "👇 *جرب الآن:*\n"
        "• `18` (سورة الكهف)\n"
        "• `ج 30` (جزء عم)\n"
        "• `آ الكرسي` (لآية الكرسي)" # ملاحظة: يحتاج برمجة خاصة لآية الكرسي، لكن الأمثلة العامة تعمل
    )
