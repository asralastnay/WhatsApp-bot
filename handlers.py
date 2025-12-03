import threading
import json
import os
import time
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
        quality = f"{r.get('bitrate', '?')}kbps"
        rtype = r.get('type', '')
        msg += f"🆔 *{r['id']}* ➖ {r['name']}\n"
        msg += f"   └ {r['rewaya']} | {rtype} | 🔊 {quality}\n"
    
    msg += "\n📝 *للاختيار السريع:*\nأرسل حرف `ق` ورقم القارئ.\nمثال: `ق 2`"
    return msg

# --- دالة الحذف المؤجل (لحذف الملف بعد 5 دقائق) ---
def schedule_delete(file_path, delay=300):
    """تحذف الملف بعد مدة محددة (بالثواني)"""
    def _delete():
        try:
            time.sleep(delay)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Deleted cached file: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting file: {e}")
            
    # تشغيل الحذف في خيط منفصل حتى لا يعطل البرنامج
    threading.Thread(target=_delete, daemon=True).start()

# --- المعالج الرئيسي (Router) ---
def handle_incoming_message(chat_id, text):
    text = text.strip()
    # توحيد النص (إزالة همزات)
    clean_text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    # جلب إعدادات المستخدم
    settings = users_mgr.get_user_settings(chat_id)
    print(f"📩 طلب من {chat_id}: {text}")

    # ==========================================
    # 1. أوامر الإعدادات والقراء
    # ==========================================
    
    if clean_text.startswith("ق ") and clean_text.split()[1].isdigit():
        new_id = int(clean_text.split()[1])
        if any(r['id'] == new_id for r in RECITERS_DATA):
            users_mgr.update_setting(chat_id, 'reciter_id', new_id)
            r_info = get_reciter_details(new_id)
            client.send_text(chat_id, f"✅ تم اختيار القارئ:\n*{r_info['name']}*\n({r_info['rewaya']} - {r_info['bitrate']}kbps)")
        else:
            client.send_text(chat_id, "❌ رقم القارئ غير صحيح. أرسل `قراء` لعرض القائمة.")
        return

    if clean_text in ['قراء', 'قرا', 'مشايخ']:
        client.send_text(chat_id, get_formatted_reciters_list())
        return

    if clean_text in ['اعدادات', 'إعدادات', 'ضبط']:
        curr_reciter = get_reciter_details(settings['reciter_id'])
        msg = f"⚙️ *إعداداتك:*\n\n"
        msg += f"🔊 الصوت: {'✅' if settings['audio_enabled'] else '❌'}\n"
        msg += f"📖 النص: {'✅' if settings['text_enabled'] else '❌'}\n"
        msg += f"👤 القارئ: {curr_reciter['name']} ({curr_reciter['bitrate']}k)\n\n"
        msg += "للتعديل أرسل: `صوت` أو `نص`"
        client.send_text(chat_id, msg)
        return

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
    # 2. أوامر القرآن
    # ==========================================
    verses_to_send = []
    header_info = ""

    if clean_text.startswith("س "):
        query = text[2:].strip()
        if query.isdigit():
             verses_to_send = quran.get_surah(int(query))
        else:
             verses_to_send = quran.get_surah(query)
        
        if verses_to_send:
            header_info = f"سورة {verses_to_send[0]['sura_name']}"

    elif clean_text.startswith("ج "):
        try:
            verses_to_send = quran.get_juz(int(text[2:]))
            header_info = f"الجزء {text[2:]}"
        except: pass

    elif clean_text.startswith("ص "):
        try:
            verses_to_send = quran.get_page(int(text[2:]))
            header_info = f"الصفحة {text[2:]}"
        except: pass
        
    elif clean_text.startswith("حزب "):
        try:
            verses_to_send = quran.get_hizb(int(text[4:]))
            header_info = f"الحزب {text[4:]}"
        except: pass

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

    # ==========================================
    # 3. التنفيذ
    # ==========================================
    if verses_to_send:
        if settings['text_enabled']:
            if len(verses_to_send) > 50:
                 client.send_text(chat_id, f"⏳ جاري تحضير النص: {header_info}...")
            
            full_text = format_text_msg(verses_to_send, header_info)
            threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()

        if settings['audio_enabled']:
            threading.Thread(target=process_audio_request, args=(chat_id, verses_to_send, settings)).start()
        
        return

    client.send_text(chat_id, get_welcome_text())

# --- دوال المعالجة الخلفية ---
def format_text_msg(verses, title):
    msg = f"🕌 *{title}* 🕌\n━━━━━━━━━━━━\n\n"
    if verses[0]['numberInSurah'] == 1 and verses[0]['sura_number'] not in [1, 9]:
        msg += "﷽\n\n"
        
    for v in verses:
        sajda = " ۩" if v['sajda'] else ""
        msg += f"{v['text']}{sajda} ({v['numberInSurah']}) "
    return msg

def process_audio_request(chat_id, verses, settings):
    if len(verses) > MAX_VERSES_TO_MERGE:
        client.send_text(chat_id, "⚠️ *عدد الآيات كبير جداً للدمج الصوتي.* سيتم الاكتفاء بالنص.")
        return

    client.send_text(chat_id, "🎧 *جاري تحضير التلاوة...*")
    
    # 1. جلب رقم القارئ والرابط
    reciter_id = settings['reciter_id']
    reciter = get_reciter_details(reciter_id)
    reciter_url = reciter['url']
    
    verses_data = [{'sura': v['sura_number'], 'ayah': v['numberInSurah']} for v in verses]
    
    try:
        # ✅ التعديل الأهم: تمرير reciter_id لدالة الدمج
        file_path = mixer.merge_verses(verses_data, reciter_url, reciter_id)
        
        if file_path:
            caption = f"🎤 القارئ: {reciter['name']}"
            client.send_file(chat_id, file_path, caption=caption)
            
            # ✅ تفعيل الحذف التلقائي بعد 5 دقائق (300 ثانية)
            schedule_delete(file_path, delay=300)
        else:
            client.send_text(chat_id, "❌ لم يتم العثور على الملف الصوتي.")
    except Exception as e:
        print(f"Audio Error: {e}")

def get_welcome_text():
    return (
        "👋 *أهلاً بك في رفيق القرآن*\n\n"
        "📜 *الأوامر المتاحة:*\n"
        "• `س الكهف` أو `س 18`\n"
        "• `ج 30` (للأجزاء)\n"
        "• `ص 100` (للصفحات)\n"
        "• `آ البقرة 50`\n"
        "• `آ البقرة 1 إلى 5`\n\n"
        "⚙️ *الإعدادات:*\n"
        "• `قراء` لعرض القائمة\n"
        "• `ق 2` لتغيير القارئ\n"
        "• `صوت` أو `نص` للتبديل"
    )
