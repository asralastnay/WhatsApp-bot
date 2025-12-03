import threading
import json
import os
import time
from config import RECITERS_FILE, MAX_VERSES_TO_MERGE
from data_loader import QuranHandler
from whatsapp_client import GreenClient
from users_manager import UsersManager
from audio_mixer import AudioMixer

# ---------------------------------------------------------
# 1. تهيئة الكلاسات والبيانات
# ---------------------------------------------------------
quran = QuranHandler()
client = GreenClient()
users_mgr = UsersManager()
mixer = AudioMixer()

# تحميل بيانات القراء
with open(RECITERS_FILE, 'r', encoding='utf-8') as f:
    RECITERS_DATA = json.load(f)

# ---------------------------------------------------------
# 2. دوال مساعدة (Helpers)
# ---------------------------------------------------------
def get_reciter_details(r_id):
    """جلب بيانات القارئ حسب الرقم"""
    for r in RECITERS_DATA:
        if r['id'] == r_id:
            return r
    return RECITERS_DATA[0]

def get_formatted_reciters_list():
    """تجهيز قائمة القراء للعرض"""
    msg = "🎙️ *قائمة القراء المتاحين:*\n━━━━━━━━━━━━\n"
    for r in RECITERS_DATA:
        quality = f"{r.get('bitrate', '?')}kbps"
        rtype = r.get('type', '')
        msg += f"🆔 *{r['id']}* ➖ {r['name']}\n"
        msg += f"   └ {r['rewaya']} | {rtype} | 🔊 {quality}\n"
    
    msg += "\n📝 *للاختيار السريع:*\nأرسل حرف `ق` ورقم القارئ.\nمثال: `ق 2`"
    return msg

def schedule_delete(file_path, delay=300):
    """
    حذف الملف من السيرفر بعد مدة معينة (لتوفير المساحة)
    delay: المدة بالثواني (300 ثانية = 5 دقائق)
    """
    def _delete():
        try:
            time.sleep(delay)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Auto-deleted file: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting file: {e}")
            
    # تشغيل الحذف في الخلفية
    threading.Thread(target=_delete, daemon=True).start()

# ---------------------------------------------------------
# 3. المعالج الرئيسي (Main Handler)
# ---------------------------------------------------------
def handle_incoming_message(chat_id, text):
    text = text.strip()
    # تنظيف النص من الهمزات لتسهيل البحث
    clean_text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    # جلب إعدادات المستخدم
    settings = users_mgr.get_user_settings(chat_id)
    
    # التأكد من وجود إعداد التكرار (للمستخدمين القدامى)
    if 'repeat_count' not in settings:
        settings['repeat_count'] = 1
        users_mgr.update_setting(chat_id, 'repeat_count', 1)

    print(f"📩 طلب من {chat_id}: {text}")

    # ==========================================
    # أ. أوامر الإعدادات (التكرار، القارئ، الضبط)
    # ==========================================

    # 1. أمر التكرار (ت [رقم])
    if clean_text.startswith("ت ") and clean_text.split()[1].isdigit():
        count = int(clean_text.split()[1])
        # حد أقصى 10 مرات تكرار
        if 1 <= count <= 10:
            users_mgr.update_setting(chat_id, 'repeat_count', count)
            client.send_text(chat_id, f"✅ تم ضبط التكرار على: *{count} مرات* لكل آية.")
        else:
            client.send_text(chat_id, "⚠️ الرجاء اختيار تكرار بين 1 و 10.")
        return

    # 2. أمر تغيير القارئ (ق [رقم])
    if clean_text.startswith("ق ") and clean_text.split()[1].isdigit():
        new_id = int(clean_text.split()[1])
        if any(r['id'] == new_id for r in RECITERS_DATA):
            users_mgr.update_setting(chat_id, 'reciter_id', new_id)
            r_info = get_reciter_details(new_id)
            client.send_text(chat_id, f"✅ تم اختيار القارئ:\n*{r_info['name']}*\n({r_info['rewaya']})")
        else:
            client.send_text(chat_id, "❌ رقم القارئ غير صحيح. أرسل `قراء` للقائمة.")
        return

    # 3. عرض القراء
    if clean_text in ['قراء', 'قرا', 'مشايخ']:
        client.send_text(chat_id, get_formatted_reciters_list())
        return

    # 4. عرض الإعدادات
    if clean_text in ['اعدادات', 'إعدادات', 'ضبط']:
        curr_reciter = get_reciter_details(settings['reciter_id'])
        msg = f"⚙️ *إعداداتك الحالية:*\n\n"
        msg += f"🔊 الصوت: {'✅' if settings['audio_enabled'] else '❌'}\n"
        msg += f"📖 النص: {'✅' if settings['text_enabled'] else '❌'}\n"
        msg += f"🔁 التكرار: *{settings.get('repeat_count', 1)} مرات*\n"
        msg += f"👤 القارئ: {curr_reciter['name']}\n\n"
        msg += "للتعديل أرسل:\n"
        msg += "• `صوت` أو `نص`\n"
        msg += "• `ت 3` (للتكرار)\n"
        msg += "• `ق 2` (لتغيير القارئ)"
        client.send_text(chat_id, msg)
        return

    # 5. تبديل الصوت والنص
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
    # ب. أوامر طلب القرآن
    # ==========================================
    verses_to_send = []
    header_info = ""

    # سورة (س الكهف / س 18)
    if clean_text.startswith("س "):
        query = text[2:].strip()
        if query.isdigit():
             verses_to_send = quran.get_surah(int(query))
        else:
             verses_to_send = quran.get_surah(query)
        
        if verses_to_send:
            header_info = f"سورة {verses_to_send[0]['sura_name']}"

    # جزء (ج 30)
    elif clean_text.startswith("ج "):
        try:
            verses_to_send = quran.get_juz(int(text[2:]))
            header_info = f"الجزء {text[2:]}"
        except: pass

    # صفحة (ص 500)
    elif clean_text.startswith("ص "):
        try:
            verses_to_send = quran.get_page(int(text[2:]))
            header_info = f"الصفحة {text[2:]}"
        except: pass
        
    # حزب (حزب 60)
    elif clean_text.startswith("حزب "):
        try:
            verses_to_send = quran.get_hizb(int(text[4:]))
            header_info = f"الحزب {text[4:]}"
        except: pass

    # آيات (آ البقرة 255 / آ البقرة 1 إلى 5)
    elif clean_text.startswith("ا ") or clean_text.startswith("آ "):
        content = text.split(' ', 1)[1]
        # التحقق من وجود نطاق (إلى / -)
        if "-" in content or " الى " in content or " إلى " in content:
            content = content.replace(" الى ", "-").replace(" إلى ", "-")
            parts = content.split("-")
            first_part = parts[0].strip()
            end_num = int(parts[1].strip())
            
            last_space = first_part.rfind(" ")
            sura_name = first_part[:last_space].strip()
            start_num = int(first_part[last_space:].strip())
            
            verses_to_send = quran.get_ayah_range(sura_name, start_num, end_num)
            header_info = f"آيات من {sura_name}"
        else:
            # آية مفردة
            parts = content.split()
            ayah_num = int(parts[-1])
            sura_name = " ".join(parts[:-1])
            v = quran.get_ayah(sura_name, ayah_num)
            if v:
                verses_to_send = [v]
                header_info = f"آية {ayah_num} من {sura_name}"

    # ==========================================
    # ج. التنفيذ
    # ==========================================
    if verses_to_send:
        # 1. إرسال النص
        if settings['text_enabled']:
            if len(verses_to_send) > 50:
                 client.send_text(chat_id, f"⏳ جاري تحضير النص: {header_info}...")
            
            full_text = format_text_msg(verses_to_send, header_info)
            threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()

        # 2. إرسال الصوت (المونتاج)
        if settings['audio_enabled']:
            repeat = settings.get('repeat_count', 1)
            threading.Thread(target=process_audio_request, args=(chat_id, verses_to_send, settings, repeat)).start()
        
        return

    # إذا لم يكن الأمر معروفاً، نرسل الترحيب
    client.send_text(chat_id, get_welcome_text())

# ---------------------------------------------------------
# 4. دوال المعالجة الخلفية (Threads)
# ---------------------------------------------------------
def format_text_msg(verses, title):
    msg = f"🕌 *{title}* 🕌\n━━━━━━━━━━━━\n\n"
    # إضافة البسملة في بداية السورة (ما عدا التوبة والفاتحة لأنها آية 1)
    if verses[0]['numberInSurah'] == 1 and verses[0]['sura_number'] not in [1, 9]:
        msg += "﷽\n\n"
        
    for v in verses:
        sajda = " ۩" if v['sajda'] else ""
        msg += f"{v['text']}{sajda} ({v['numberInSurah']}) "
    return msg

def process_audio_request(chat_id, verses, settings, repeat_count):
    """معالجة طلب الصوت مع التكرار وحذف الملفات"""
    
    # 1. التحقق من الحد الأقصى
    # إذا كان التكرار مفعلاً، نخفض عدد الآيات المسموح بها لتجنب الملفات الضخمة
    effective_limit = MAX_VERSES_TO_MERGE
    if repeat_count > 1:
        effective_limit = 20 # حد مخفض عند التكرار
    
    if len(verses) > effective_limit:
        client.send_text(chat_id, f"⚠️ *عدد الآيات كبير جداً مع التكرار.*\nالحد الأقصى عند تفعيل التكرار هو {effective_limit} آية.")
        return

    msg_wait = "🎧 *جاري تحضير التلاوة...*"
    if repeat_count > 1:
        msg_wait += f"\n(تكرار: {repeat_count} مرات)"
    client.send_text(chat_id, msg_wait)
    
    # 2. تجهيز البيانات
    reciter_id = settings['reciter_id']
    reciter = get_reciter_details(reciter_id)
    reciter_url = reciter['url']
    
    verses_data = [{'sura': v['sura_number'], 'ayah': v['numberInSurah']} for v in verses]
    
    # 3. الدمج
    try:
        # نستدعي الميكسر مع المعاملات الجديدة (ID + Repeat)
        file_path = mixer.merge_verses(verses_data, reciter_url, reciter_id, repeat_count)
        
        if file_path:
            caption = f"🎤 {reciter['name']}"
            if repeat_count > 1:
                caption += f" | 🔁 تكرار: {repeat_count}"
            
            # إرسال الملف
            client.send_file(chat_id, file_path, caption=caption)
            
            # ✅ حذف الملف بعد 5 دقائق (300 ثانية)
            schedule_delete(file_path, delay=300)
        else:
            client.send_text(chat_id, "❌ عذراً، لم يتم العثور على التلاوة المطلوبة.")
    except Exception as e:
        print(f"Audio Error: {e}")
        client.send_text(chat_id, "❌ حدث خطأ غير متوقع أثناء المعالجة.")

def get_welcome_text():
    return (
        "👋 *أهلاً بك في رفيق القرآن*\n\n"
        "📜 *أوامر التلاوة:*\n"
        "• `س الكهف` أو `س 18`\n"
        "• `ج 30` (جزء)\n"
        "• `ص 100` (صفحة)\n"
        "• `آ البقرة 255` (آية)\n"
        "• `آ البقرة 1 إلى 5` (مجموعة)\n\n"
        "🔁 *ميزة التحفيظ (التكرار):*\n"
        "• `ت 3` لتكرار الآية 3 مرات\n"
        "• `ت 1` لإلغاء التكرار\n\n"
        "⚙️ *الإعدادات:*\n"
        "• `قراء` لعرض المشايخ\n"
        "• `ق 2` لتغيير القارئ\n"
        "• `إعدادات` لعرض حالتك"
    )
