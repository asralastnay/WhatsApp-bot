# message_processor.py
import threading
import re
from data_loader import QuranHandler
from whatsapp_client import GreenClient

quran = QuranHandler()
client = GreenClient()

# --- رسالة الترحيب والتعليمات (عدلها كما تحب) ---
WELCOME_MESSAGE = (
    "👋 *حياك الله في بوت القرآن الكريم*\n\n"
    "بوت مخصص لخدمة المكفوفين ومحبي القرآن. تم تصميم الأوامر لتكون سهلة وسريعة.\n\n"
    "📌 *دليل الأوامر:*\n\n"
    "1️⃣ *السور:* أرسل حرف `س` واسم السورة.\n"
    "• مثال: `س البقرة` أو `س الكهف`\n\n"
    "2️⃣ *الأجزاء:* أرسل حرف `ج` ورقم الجزء.\n"
    "• مثال: `ج 30` أو `ج 1`\n\n"
    "3️⃣ *الصفحات:* أرسل حرف `ص` ورقم الصفحة.\n"
    "• مثال: `ص 50`\n\n"
    "4️⃣ *الآيات:* أرسل حرف `آ` واسم السورة ورقم الآية.\n"
    "• آية واحدة: `آ البقرة 255`\n"
    "• مجموعة آيات: `آ البقرة 1 إلى 5`\n\n"
    "🔢 *طريقة سريعة:* أرسل رقم السورة فقط (مثلاً `18`) لإرسالها فوراً.\n\n"
    "🌹 تقبل الله منا ومنكم صالح الأعمال."
)

def process_message(chat_id, text):
    text = text.strip()
    # تنظيف بسيط للهمزات
    clean_text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    
    print(f"📩 أمر جديد: {text}")

    # ---------------------------------------------------------
    # 1. أوامر السور (س [الاسم]) - صارمة
    # ---------------------------------------------------------
    if clean_text.startswith("س "):
        surah_name = text[2:].strip() # نأخذ الاسم الأصلي
        surah = quran.get_surah_by_name(surah_name)
        if surah:
            client.send_text(chat_id, f"✅ جاري إرسال سورة *{surah['name']['ar']}*...")
            send_surah_full(chat_id, surah)
        else:
            client.send_text(chat_id, "❌ لم أجد السورة. تأكد من الاسم (مثال: س مريم).")
        return

    # ---------------------------------------------------------
    # 2. أوامر الأجزاء (ج [الرقم]) - صارمة
    # ---------------------------------------------------------
    if clean_text.startswith("ج "):
        try:
            # استخراج الرقم (ج 30 -> 30)
            juz_num = int(text[2:].strip())
            if 1 <= juz_num <= 30:
                client.send_text(chat_id, f"✅ جاري إرسال الجزء *{juz_num}*...")
                verses = quran.get_juz_verses(juz_num)
                if verses:
                    full_text = f"✨ *الجزء {juz_num}* ✨\n\n" + " ".join(verses)
                    threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
                else:
                    client.send_text(chat_id, "⚠️ لم يتم العثور على بيانات لهذا الجزء.")
            else:
                client.send_text(chat_id, "❌ رقم الجزء خطأ. (من 1 إلى 30).")
        except ValueError:
            client.send_text(chat_id, "❌ الرجاء كتابة رقم الجزء بشكل صحيح. مثال: ج 30")
        return

    # ---------------------------------------------------------
    # 3. أوامر الصفحات (ص [الرقم]) - صارمة
    # ---------------------------------------------------------
    if clean_text.startswith("ص "):
        try:
            p_num = int(text[2:].strip())
            verses = quran.get_page_verses(p_num)
            if verses:
                msg = f"📄 *الصفحة {p_num}*\n\n" + " ".join(verses)
                threading.Thread(target=client.send_text, args=(chat_id, msg)).start()
            else:
                client.send_text(chat_id, "❌ رقم الصفحة خطأ (من 1 إلى 604).")
        except ValueError:
            client.send_text(chat_id, "❌ مثال صحيح: ص 100")
        return

    # ---------------------------------------------------------
    # 4. أوامر الآيات (آ [سورة] [رقم] (إلى [رقم]))
    # ---------------------------------------------------------
    if clean_text.startswith("ا ") or clean_text.startswith("آ ") or clean_text.startswith("اية "):
        # إزالة حرف الأمر للتعامل مع الباقي
        content = text.split(' ', 1)[1] # "البقرة 1 إلى 5"
        
        # هل هو طلب مجال (إلى، -)؟
        is_range = " الى " in content or " إلى " in content or "-" in content
        
        try:
            if is_range:
                # معالجة المجال: آ البقرة 1 إلى 10
                # تقسيم النص باستخدام تعبيرات نمطية لفصل الاسم عن الأرقام
                # نبحث عن آخر رقمين في النص
                # طريقة بسيطة: نفترض الصيغة: [اسم السورة] [رقم1] [فاصل] [رقم2]
                
                # استبدال الفواصل برمز موحد
                content_clean = content.replace(" إلى ", "-").replace(" الى ", "-")
                parts = content_clean.split("-") 
                # parts[0] = "البقرة 1" , parts[1] = "10"
                
                last_space_index = parts[0].rfind(" ")
                surah_name = parts[0][:last_space_index].strip()
                start_num = int(parts[0][last_space_index:].strip())
                end_num = int(parts[1].strip())
                
                surah, verses_objs = quran.get_ayah_range(surah_name, start_num, end_num)
                
                if surah and verses_objs:
                    header = f"🔹 *{surah['name']['ar']}* (من {start_num} إلى {end_num})\n\n"
                    verses_text = " ".join([f"{v['text']['ar']} ({v['number']})" for v in verses_objs])
                    client.send_text(chat_id, header + verses_text)
                else:
                    client.send_text(chat_id, "❌ لم أجد السورة أو الآيات المطلوبة.")
            
            else:
                # آية واحدة: آ البقرة 255
                parts = content.split()
                # الرقم هو آخر جزء، والاسم هو ما قبله
                ayah_num = int(parts[-1])
                surah_name = " ".join(parts[:-1])
                
                ayah = quran.get_ayah(surah_name, ayah_num)
                if ayah:
                    msg = f"🔹 *{surah['name']['ar']} ({ayah_num})*\n\n{ayah['text']['ar']}"
                    client.send_text(chat_id, msg)
                else:
                    client.send_text(chat_id, "❌ الآية غير موجودة.")

        except Exception as e:
            client.send_text(chat_id, "⚠️ صيغة الأمر غير واضحة.\nجرب: `آ البقرة 5` أو `آ البقرة 1 إلى 5`")
            print(f"Error parsing Ayah: {e}")
        return

    # ---------------------------------------------------------
    # 5. البحث برقم السورة فقط (سريع)
    # ---------------------------------------------------------
    if clean_text.isdigit():
        num = int(clean_text)
        if 1 <= num <= 114:
            s = quran.get_surah_by_number(num)
            client.send_text(chat_id, f"✅ جاري إرسال سورة *{s['name']['ar']}*...")
            send_surah_full(chat_id, s)
            return

    # ---------------------------------------------------------
    # 6. إذا لم ينطبق أي شيء -> إرسال رسالة الترحيب
    # ---------------------------------------------------------
    client.send_text(chat_id, WELCOME_MESSAGE)


# --- دالة مساعدة لتنسيق السورة كاملة ---
def send_surah_full(chat_id, surah):
    if not surah: return
    
    # تجميع الآيات
    verses_str = " ".join([f"{a['text']['ar']} ({a['number']}){' ۩' if a.get('sajda') else ''}" for a in surah['verses']])
    
    # الترويسة
    header = f"✨ *سورة {surah['name']['ar']}* ✨\n"
    header += f"🔢 رقمها: {surah['number']} | 📍 {surah.get('revelation_place', {}).get('ar', '')} | 📝 آياتها: {surah['verses_count']}\n"
    header += "─" * 20 + "\n\n"
    
    if surah['number'] not in [1, 9]: 
        header += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
    
    full_text = header + verses_str
    
    threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
