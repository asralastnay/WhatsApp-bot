# message_processor.py
import threading
from data_loader import QuranHandler
from whatsapp_client import GreenClient

# تهيئة الأدوات
quran = QuranHandler()
client = GreenClient()

def process_message(chat_id, text):
    text = text.strip()
    print(f"📩 معالجة الأمر: {text}")

    # --- 1. التعامل مع اختيارات القائمة (تحويل الزر إلى نص) ---
    # عندما يضغط المستخدم زر سورة، نحوله فوراً إلى أمر "س [الاسم]"
    if text.startswith("CMD_SURAH_"):
        try:
            surah_num = int(text.split("_")[2])
            surah = quran.get_surah_by_number(surah_num)
            if surah:
                # هنا التوحيد الذي طلبته: نحولها لأمر نصي ونعيد معالجته
                surah_name = surah['name']['ar']
                new_command = f"س {surah_name}"
                process_message(chat_id, new_command) # إعادة استدعاء الدالة
                return
        except:
            pass

    # --- 2. عرض القوائم (التنقل بين الصفحات) ---
    if text.lower() in ['قائمة', 'menu', 'start', 'مرحبا', 'هلا'] or text.startswith("LIST_PAGE_"):
        page = 0
        if text.startswith("LIST_PAGE_"):
            try: page = int(text.split("_")[2])
            except: pass
        
        surahs, has_next = quran.get_surahs_paginated(page)
        
        rows = []
        # إنشاء أزرار السور
        for s in surahs:
            rows.append({
                "title": f"{s['number']}. {s['name']['ar']}", # مثال: 2. البقرة
                "description": f"آياتها: {len(s['verses'])} | {s['type']['ar']}",
                "rowId": f"CMD_SURAH_{s['number']}" # الأمر المخفي
            })
        
        # أزرار التنقل
        if has_next:
            rows.append({"title": "⬅️ التالي", "description": "المزيد من السور", "rowId": f"LIST_PAGE_{page+1}"})
        if page > 0:
            rows.append({"title": "➡️ السابق", "description": "العودة للخلف", "rowId": f"LIST_PAGE_{page-1}"})
            
        client.send_list(chat_id, "📖 قائمة سور القرآن", "فتح القائمة", rows, "اختر السورة أو انتقل للصفحات التالية:")
        return

    # --- 3. الأوامر النصية (س، آ، ص) ---
    
    # أمر السورة (س)
    if text.startswith("س "):
        surah_name = text[2:].strip()
        surah = quran.get_surah_by_name(surah_name)
        if surah:
            # تجهيز النص
            verses = " ".join([f"{a['text']['ar']} ({a['number']})" for a in surah['verses']])
            header = f"✨ *سورة {surah['name']['ar']}* ✨\n\n"
            if surah['number'] not in [1, 9]: # الفاتحة والتوبة
                header += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
            
            full_text = header + verses
            
            # إرسال في الخلفية (Threading)
            threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
        else:
            client.send_text(chat_id, "❌ لم أجد السورة، تأكد من الاسم.")
        return

    # أمر الآية (آ)
    if text.startswith("آ "):
        try:
            parts = text[2:].split()
            ayah = quran.get_ayah(parts[0], int(parts[1]))
            if ayah:
                msg = f"🔹 *{parts[0]} ({parts[1]})*\n\n{ayah['text']['ar']}"
                client.send_text(chat_id, msg)
            else:
                client.send_text(chat_id, "❌ الآية غير موجودة.")
        except:
            client.send_text(chat_id, "⚠️ صيغة خاطئة. مثال: `آ البقرة 5`")
        return

    # أمر الصفحة (ص)
    if text.startswith("ص "):
        try:
            p_num = int(text[2:].strip())
            verses = quran.get_page_verses(p_num)
            if verses:
                msg = f"📄 *الصفحة {p_num}*\n\n" + " ".join(verses)
                threading.Thread(target=client.send_text, args=(chat_id, msg)).start()
            else:
                client.send_text(chat_id, "❌ رقم الصفحة خطأ.")
        except:
            pass
        return

    # إذا لم يكن أمراً معروفاً -> نرسل القائمة
    process_message(chat_id, "قائمة")
