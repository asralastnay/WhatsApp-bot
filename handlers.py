import threading
import messages as msg  # ملف النصوص
import tasks            # ملف المهام الخلفية
from data_loader import QuranHandler
from whatsapp_client import GreenClient
from users_manager import UsersManager

# ==========================================
# 1. تهيئة الأدوات
# ==========================================
quran = QuranHandler()
client = GreenClient()
users_mgr = UsersManager()

# ==========================================
# 2. دوال مساعدة داخلية
# ==========================================
def format_reciters_list():
    """تجهيز قائمة القراء للعرض باستخدام البيانات من tasks والنصوص من messages"""
    reciters = tasks.get_reciters_data()
    text = msg.RECITERS_HEADER
    for r in reciters:
        quality = f"{r.get('bitrate', '?')}kbps"
        rtype = r.get('type', '')
        text += f"🆔 *{r['id']}* ➖ {r['name']}\n"
        text += f"   └ {r['rewaya']} | {rtype} | 🔊 {quality}\n"
    text += msg.RECITERS_FOOTER
    return text

# ==========================================
# 3. المعالج الرئيسي (The Router)
# ==========================================
def handle_incoming_message(chat_id, text):
    text = text.strip()
    # تنظيف النص (توحيد الهمزات والتاء المربوطة)
    clean_text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    # تحميل إعدادات المستخدم (أو إنشاء جديد)
    settings = users_mgr.get_user_settings(chat_id)
    
    # ضمان وجود إعداد التكرار (للمستخدمين القدامى)
    if 'repeat_count' not in settings:
        settings['repeat_count'] = 1
        users_mgr.update_setting(chat_id, 'repeat_count', 1)

    print(f"📩 Router: Received from {chat_id}: {text}")

    # ---------------------------------------------------
    # أ. قسم الإعدادات (Control Panel)
    # ---------------------------------------------------

    # 1. ضبط التكرار (ت [رقم])
    if clean_text.startswith("ت ") and clean_text.split()[1].isdigit():
        count = int(clean_text.split()[1])
        if 1 <= count <= 10:
            users_mgr.update_setting(chat_id, 'repeat_count', count)
            client.send_text(chat_id, msg.msg_repeat_set(count))
        else:
            client.send_text(chat_id, msg.ERR_INVALID_REPEAT)
        return

    # 2. تغيير القارئ (ق [رقم])
    if clean_text.startswith("ق ") and clean_text.split()[1].isdigit():
        new_id = int(clean_text.split()[1])
        # نتحقق هل الرقم موجود عبر ملف المهام
        reciter = tasks.get_reciter_details(new_id)
        if reciter and reciter['id'] == new_id:
            users_mgr.update_setting(chat_id, 'reciter_id', new_id)
            client.send_text(chat_id, msg.msg_reciter_selected(reciter['name'], reciter['rewaya']))
        else:
            client.send_text(chat_id, msg.ERR_RECITER_NOT_FOUND)
        return

    # 3. عرض قائمة القراء
    if clean_text in ['قراء', 'قرا', 'مشايخ']:
        client.send_text(chat_id, format_reciters_list())
        return

    # 4. عرض الإعدادات الحالية
    if clean_text in ['اعدادات', 'إعدادات', 'ضبط']:
        curr_reciter = tasks.get_reciter_details(settings['reciter_id'])
        response = msg.msg_settings_display(
            audio=settings['audio_enabled'],
            text=settings['text_enabled'],
            repeat=settings.get('repeat_count', 1),
            reciter_name=curr_reciter['name']
        )
        client.send_text(chat_id, response)
        return

    # 5. التبديل السريع (صوت/نص)
    if clean_text == 'صوت':
        new_val = not settings['audio_enabled']
        users_mgr.update_setting(chat_id, 'audio_enabled', new_val)
        client.send_text(chat_id, msg.msg_toggle_status("الصوت", new_val))
        return
    if clean_text == 'نص':
        new_val = not settings['text_enabled']
        users_mgr.update_setting(chat_id, 'text_enabled', new_val)
        client.send_text(chat_id, msg.msg_toggle_status("النص", new_val))
        return

    # ---------------------------------------------------
    # ب. قسم البحث القرآني (Quran Search)
    # ---------------------------------------------------
    verses_to_send = []
    header_info = ""

    # سورة
    if clean_text.startswith("س "):
        query = text[2:].strip()
        if query.isdigit():
             verses_to_send = quran.get_surah(int(query))
        else:
             verses_to_send = quran.get_surah(query)
        
        if verses_to_send:
            header_info = f"سورة {verses_to_send[0]['sura_name']}"

    # جزء
    elif clean_text.startswith("ج "):
        try:
            verses_to_send = quran.get_juz(int(text[2:]))
            header_info = f"الجزء {text[2:]}"
        except: pass

    # صفحة
    elif clean_text.startswith("ص "):
        try:
            verses_to_send = quran.get_page(int(text[2:]))
            header_info = f"الصفحة {text[2:]}"
        except: pass
        
    # حزب
    elif clean_text.startswith("ح "):
        try:
            val = int(text[2:]) # قص أول حرفين
            verses_to_send = quran.get_hizb(val)
            header_info = f"الحزب {val}"
        except: pass
            
    elif clean_text.startswith("ر "):
        try:
            val = int(text[2:]) # قص أول حرفين
            verses_to_send = quran.get_hizb_quarter(val)
            header_info = f"الربع {val}"
        except: pass

    # آيات (نطاق أو مفرد)
    elif clean_text.startswith("ا ") or clean_text.startswith("آ "):
        content = text.split(' ', 1)[1]
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
            parts = content.split()
            ayah_num = int(parts[-1])
            sura_name = " ".join(parts[:-1])
            v = quran.get_ayah(sura_name, ayah_num)
            if v:
                verses_to_send = [v]
                header_info = f"آية {ayah_num} من {sura_name}"

    # ---------------------------------------------------
    # ج. قسم التنفيذ (Execution Dispatcher)
    # ---------------------------------------------------
    if verses_to_send:
        # 1. إطلاق مهمة النص (في الخلفية)
        if settings['text_enabled']:
            threading.Thread(
                target=tasks.process_text_request,
                args=(chat_id, verses_to_send, header_info)
            ).start()

        # 2. إطلاق مهمة الصوت (في الخلفية)
        if settings['audio_enabled']:
            repeat = settings.get('repeat_count', 1)
            threading.Thread(
                target=tasks.process_audio_request,
                args=(chat_id, verses_to_send, settings, repeat)
            ).start()
        
        return

    # ---------------------------------------------------
    # د. الرسالة الافتراضية (Fallback)
    # ---------------------------------------------------
    # إذا وصل لهنا، يعني أن الرسالة ليست أمراً معروفاً
    client.send_text(chat_id, msg.WELCOME_TEXT)
