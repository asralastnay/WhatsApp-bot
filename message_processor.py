import threading
from data_loader import QuranHandler
from whatsapp_client import GreenClient

quran = QuranHandler()
client = GreenClient()

def process_message(chat_id, text):
    # تنظيف النص لزيادة دقة البحث
    clean_text = text.strip().replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    print(f"📩 معالجة: {text}")

    # --- 1. البحث بالرقم ---
    if clean_text.isdigit():
        surah_num = int(clean_text)
        if 1 <= surah_num <= 114:
            send_surah_by_obj(chat_id, quran.get_surah_by_number(surah_num))
            return
        else:
            client.send_text(chat_id, "❌ رقم غير صحيح. أرسل رقماً بين 1 و 114.")
            return

    # --- 2. البحث الذكي بالاسم ---
    found_surah = quran.get_surah_by_name(text.strip())
    
    if not found_surah:
        # بحث تقريبي داخل الأسماء
        for s in quran.data:
            s_name = s['name']['ar'].replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
            if s_name in clean_text: # هل اسم السورة جزء من الرسالة؟
                found_surah = s
                break
    
    if found_surah:
        client.send_text(chat_id, f"✅ جاري إرسال سورة *{found_surah['name']['ar']}*...")
        send_surah_by_obj(chat_id, found_surah)
        return

    # --- 3. الأوامر المحددة (آية، صفحة) ---
    if text.startswith("آ ") or text.startswith("اية "):
        try:
            parts = text.split()
            surah_part = parts[1]
            ayah_part = int(parts[2])
            ayah = quran.get_ayah(surah_part, ayah_part)
            if ayah:
                msg = f"🔹 *{surah_part} ({ayah_part})*\n\n{ayah['text']['ar']}"
                client.send_text(chat_id, msg)
                return
        except:
            pass

    if text.startswith("ص ") or text.startswith("صفحة "):
        try:
            p_num = int(''.join(filter(str.isdigit, text)))
            verses = quran.get_page_verses(p_num)
            if verses:
                msg = f"📄 *الصفحة {p_num}*\n\n" + " ".join(verses)
                threading.Thread(target=client.send_text, args=(chat_id, msg)).start()
                return
        except:
            pass

    # رسالة المساعدة
    welcome_msg = (
        "👋 *أهلاً بك في بوت القرآن الكريم*\n\n"
        "اكتب اسم السورة أو رقمها فقط وسأرسلها لك.\n\n"
        "أمثلة:\n"
        "• `البقرة` أو `2`\n"
        "• `الكهف` أو `18`\n"
        "• `ص 100` (للصفحات)"
    )
    client.send_text(chat_id, welcome_msg)

# --- دالة تجهيز السورة (تم تعديلها لتناسب بياناتك) ---
def send_surah_by_obj(chat_id, surah):
    if not surah: return
    
    # 1. تجميع الآيات مع إضافة علامة السجدة
    verses_list = []
    for ayah in surah['verses']:
        ayah_text = ayah['text']['ar']
        ayah_num = ayah['number']
        
        # إضافة علامة السجدة إذا وجدت في البيانات
        sajda_mark = " ۩" if ayah.get('sajda') is True else ""
        
        verses_list.append(f"{ayah_text} ({ayah_num}){sajda_mark}")

    verses_str = " ".join(verses_list)
    
    # 2. استخراج البيانات الصحيحة من ملفك
    s_name = surah['name']['ar']
    s_num = surah['number']
    s_place = surah['revelation_place']['ar'] # (مكية/مدنية) تم الإصلاح هنا
    s_count = surah['verses_count']
    
    # 3. بناء الترويسة
    header = f"✨ *سورة {s_name}* ✨\n"
    header += f"🔢 رقمها: {s_num} | 📍 {s_place} | 📝 آياتها: {s_count}\n"
    header += "─" * 20 + "\n\n"
    
    if s_num not in [1, 9]: 
        header += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
    
    full_text = header + verses_str
    
    # 4. الإرسال
    threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
