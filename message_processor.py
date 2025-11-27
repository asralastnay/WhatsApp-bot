import threading
from data_loader import QuranHandler
from whatsapp_client import GreenClient

quran = QuranHandler()
client = GreenClient()

# --- رسالة الترحيب (تصميم جديد وأنيق للجميع) ---
WELCOME_MESSAGE = (
    "🕌 *أهلاً بك في رفيق القرآن الكريم*\n\n"
    "يسرنا خدمتك لتلاوة وتدبر كتاب الله في أي وقت. البوت مصمم ليكون سهلاً وسريعاً للجميع.\n"
    "━━━━━━━━━━━━\n\n"
    "📌 *دليل الأوامر المختصر:*\n\n"
    "📖 *لقراءة السور:*\n"
    "أرسل حرف `س` واسم السورة.\n"
    "• مثال: `س الكهف`\n\n"
    "🧩 *لقراءة جزء كامل:*\n"
    "أرسل حرف `ج` ورقم الجزء.\n"
    "• مثال: `ج 30`\n\n"
    "📄 *لقراءة صفحة:* \n"
    "أرسل حرف `ص` ورقم الصفحة.\n"
    "• مثال: `ص 100`\n\n"
    "🔍 *للبحث عن آيات:*\n"
    "أرسل `آ` + اسم السورة + رقم الآية.\n"
    "• مثال: `آ البقرة 255`\n\n"
    "⚡ *الطريقة السريعة:* \n"
    "فقط أرسل *رقم السورة* (مثل `18`) وسأرسلها لك فوراً.\n\n"
    "🌸 *تقبل الله منا ومنكم صالح الأعمال*"
)

def process_message(chat_id, text):
    text = text.strip()
    clean_text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    print(f"📩 طلب جديد: {text}")

    # ---------------------------------------------------------
    # 1. أوامر السور (س [الاسم])
    # ---------------------------------------------------------
    if clean_text.startswith("س "):
        surah_name = text[2:].strip()
        surah = quran.get_surah_by_name(surah_name)
        if surah:
            client.send_text(chat_id, f"⏳ *جاري تحضير سورة {surah['name']['ar']}...*")
            send_surah_full(chat_id, surah)
        else:
            client.send_text(chat_id, "❌ *عذراً، لم يتم العثور على السورة.*\nتأكد من كتابة الاسم بشكل صحيح.")
        return

    # ---------------------------------------------------------
    # 2. أوامر الأجزاء (ج [الرقم])
    # ---------------------------------------------------------
    if clean_text.startswith("ج "):
        try:
            juz_num = int(text[2:].strip())
            if 1 <= juz_num <= 30:
                client.send_text(chat_id, f"⏳ *جاري تحضير الجزء {juz_num}...*")
                verses = quran.get_juz_verses(juz_num)
                if verses:
                    # تنسيق رأس الجزء
                    full_text = f"🕋 *الجزء {juz_num}* 🕋\n"
                    full_text += "━━━━━━━━━━━━\n\n"
                    full_text += " ".join(verses)
                    threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
                else:
                    client.send_text(chat_id, "⚠️ لا توجد بيانات لهذا الجزء.")
            else:
                client.send_text(chat_id, "❌ رقم الجزء يجب أن يكون من 1 إلى 30.")
        except ValueError:
            client.send_text(chat_id, "❌ صيغة خاطئة. مثال صحيح: `ج 29`")
        return

    # ---------------------------------------------------------
    # 3. أوامر الصفحات (ص [الرقم])
    # ---------------------------------------------------------
    if clean_text.startswith("ص "):
        try:
            p_num = int(text[2:].strip())
            verses = quran.get_page_verses(p_num)
            if verses:
                # تنسيق رأس الصفحة
                header = f"📄 *الصفحة رقم {p_num}*\n"
                header += "┄┄┄┄┄┄┄┄┄\n\n"
                msg = header + " ".join(verses)
                threading.Thread(target=client.send_text, args=(chat_id, msg)).start()
            else:
                client.send_text(chat_id, "❌ رقم الصفحة خارج النطاق (1-604).")
        except ValueError:
            client.send_text(chat_id, "❌ مثال صحيح: `ص 50`")
        return

    # ---------------------------------------------------------
    # 4. أوامر الآيات (آ [سورة] ...)
    # ---------------------------------------------------------
    if clean_text.startswith("ا ") or clean_text.startswith("آ ") or clean_text.startswith("اية "):
        content = text.split(' ', 1)[1]
        is_range = " الى " in content or " إلى " in content or "-" in content
        
        try:
            if is_range:
                # معالجة المجال
                content_clean = content.replace(" إلى ", "-").replace(" الى ", "-")
                parts = content_clean.split("-") 
                last_space_index = parts[0].rfind(" ")
                surah_name = parts[0][:last_space_index].strip()
                start_num = int(parts[0][last_space_index:].strip())
                end_num = int(parts[1].strip())
                
                surah, verses_objs = quran.get_ayah_range(surah_name, start_num, end_num)
                
                if surah and verses_objs:
                    header = f"🌿 *سورة {surah['name']['ar']}*\n"
                    header += f"🔢 الآيات من *{start_num}* إلى *{end_num}*\n\n"
                    verses_text = " ".join([f"{v['text']['ar']} ({v['number']})" for v in verses_objs])
                    client.send_text(chat_id, header + verses_text)
                else:
                    client.send_text(chat_id, "❌ لم يتم العثور على الآيات.")
            
            else:
                # آية واحدة
                parts = content.split()
                ayah_num = int(parts[-1])
                surah_name = " ".join(parts[:-1])
                
                ayah = quran.get_ayah(surah_name, ayah_num)
                if ayah:
                    # تنسيق الآية المنفردة
                    msg = f"🌿 *سورة {surah_name}* | الآية *{ayah_num}*\n\n"
                    msg += f"۞ {ayah['text']['ar']} ۞"
                    client.send_text(chat_id, msg)
                else:
                    client.send_text(chat_id, "❌ الآية غير موجودة.")

        except Exception as e:
            client.send_text(chat_id, "⚠️ لم أفهم الأمر. جرب: `آ البقرة 255`")
        return

    # ---------------------------------------------------------
    # 5. البحث بالرقم فقط (سريع)
    # ---------------------------------------------------------
    if clean_text.isdigit():
        num = int(clean_text)
        if 1 <= num <= 114:
            s = quran.get_surah_by_number(num)
            client.send_text(chat_id, f"⏳ *جاري تحضير سورة {s['name']['ar']}...*")
            send_surah_full(chat_id, s)
            return

    # ---------------------------------------------------------
    # 6. رسالة الترحيب الافتراضية
    # ---------------------------------------------------------
    client.send_text(chat_id, WELCOME_MESSAGE)


# --- دالة تجهيز السورة (تصميم جديد وجميل) ---
def send_surah_full(chat_id, surah):
    if not surah: return
    
    # 1. تجميع الآيات
    # أضفنا علامة السجدة ۩
    verses_str = " ".join([f"{a['text']['ar']} ({a['number']}){' ۩' if a.get('sajda') else ''}" for a in surah['verses']])
    
    # 2. تصميم الترويسة (Header) الجمالي
    # نستخدم خطوطاً عريضة وفواصل لترتيب المعلومات بصرياً
    header = f"╭━━━ 📖 *سورة {surah['name']['ar']}* ━━━╮\n"
    header += f"│ 🔢 الترتيب: {surah['number']}\n"
    header += f"│ 📍 النوع: {surah.get('revelation_place', {}).get('ar', '')}\n"
    header += f"│ 📝 عدد الآيات: {surah['verses_count']}\n"
    header += "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
    
    # البسملة (إذا لم تكن الفاتحة أو التوبة)
    if surah['number'] not in [1, 9]: 
        header += "      ﷽\n\n"
    
    full_text = header + verses_str
    
    threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
