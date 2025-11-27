import threading
from data_loader import QuranHandler
from whatsapp_client import GreenClient

# تهيئة الأدوات
quran = QuranHandler()
client = GreenClient()

def process_message(chat_id, text):
    text = text.strip()
    print(f"📩 معالجة الأمر: {text}")

    # --- 1. النظام الرقمي الذكي (الحل السحري لـ TalkBack) ---
    # إذا أرسل المستخدم رقماً فقط (مثلاً: 18)
    if text.isdigit():
        surah_num = int(text)
        # نتأكد أن الرقم بين 1 و 114
        if 1 <= surah_num <= 114:
            surah = quran.get_surah_by_number(surah_num)
            if surah:
                # إرسال رسالة تأكيد صوتية (نصية يقرأها TalkBack)
                client.send_text(chat_id, f"جاري إحضار سورة {surah['name']['ar']}...")
                
                # تجهيز السورة
                verses = " ".join([f"{a['text']['ar']} ({a['number']})" for a in surah['verses']])
                header = f"✨ *سورة {surah['name']['ar']}* (رقم {surah['number']}) ✨\n\n"
                if surah['number'] not in [1, 9]: 
                    header += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
                
                full_text = header + verses
                threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
            return
        else:
            client.send_text(chat_id, "❌ رقم السورة غير صحيح. القرآن 114 سورة فقط.")
            return

    # --- 2. طلب القائمة (عرض نصي بسيط) ---
    if text.lower() in ['قائمة', 'menu', 'start', 'مرحبا', 'هلا', 'اهلا', 'help']:
        msg = (
            "👋 *أهلاً بك في بوت القرآن الكريم*\n\n"
            "لقد صممنا هذا البوت ليكون سهلاً جداً. لا داعي للكتابة الطويلة.\n\n"
            "🔢 *طريقة الاستخدام السريعة:*\n"
            "فقط أرسل *رقم السورة* وسيتم إرسالها لك فوراً.\n\n"
            "أمثلة:\n"
            "• أرسل `1` -> لسورة الفاتحة\n"
            "• أرسل `2` -> لسورة البقرة\n"
            "• أرسل `18` -> لسورة الكهف\n"
            "• أرسل `114` -> لسورة الناس\n\n"
            "📄 *للبحث عن صفحة:*\n"
            "اكتب ص ثم رقم الصفحة. مثال: `ص 50`\n"
        )
        client.send_text(chat_id, msg)
        return

    # --- 3. الأوامر القديمة (س، آ، ص) - ما زالت تعمل ---
    
    # أمر السورة (س)
    if text.startswith("س "):
        surah_name = text[2:].strip()
        surah = quran.get_surah_by_name(surah_name)
        if surah:
            verses = " ".join([f"{a['text']['ar']} ({a['number']})" for a in surah['verses']])
            header = f"✨ *سورة {surah['name']['ar']}* ✨\n\n"
            if surah['number'] not in [1, 9]: 
                header += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
            full_text = header + verses
            threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
        else:
            client.send_text(chat_id, "❌ لم أجد السورة. جرب إرسال رقمها بدلاً من اسمها.")
        return

    # أمر الآية (آ)
    if text.startswith("آ "):
        try:
            parts = text[2:].split()
            if len(parts) >= 2:
                ayah = quran.get_ayah(parts[0], int(parts[1]))
                if ayah:
                    msg = f"🔹 *{parts[0]} ({parts[1]})*\n\n{ayah['text']['ar']}"
                    client.send_text(chat_id, msg)
                else:
                    client.send_text(chat_id, "❌ الآية غير موجودة.")
        except:
            pass
        return

    # أمر الصفحة (ص)
    if text.startswith("ص "):
        try:
            p_num = int(text[2:].strip())
            verses = quran.get_page_verses(p_num)
            if verses:
                msg = f"📄 *الصفحة {p_num}*\n\n" + " ".join(verses)
                threading.Thread(target=client.send_text, args=(chat_id, msg)).start()
        except:
            pass
        return

    # إذا أرسل كلاماً غير مفهوم
    client.send_text(chat_id, "مرحباً 👋\nفقط أرسل *رقم السورة* (مثلاً 18) وسأرسلها لك.")
