# message_processor.py
import threading
from data_loader import QuranHandler
from whatsapp_client import GreenClient

quran = QuranHandler()
client = GreenClient()

def process_message(chat_id, text):
    # تنظيف النص: إزالة المسافات الزائدة والهمزات لتسهيل البحث
    clean_text = text.strip().replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    print(f"📩 معالجة: {text}")

    # --- 1. البحث بالرقم (الأسرع والأدق) ---
    if clean_text.isdigit():
        surah_num = int(clean_text)
        if 1 <= surah_num <= 114:
            send_surah_by_obj(chat_id, quran.get_surah_by_number(surah_num))
            return
        else:
            client.send_text(chat_id, "❌ القرآن 114 سورة فقط. أرسل رقماً بين 1 و 114.")
            return

    # --- 2. البحث الذكي بالاسم (بدون أوامر) ---
    # نحاول معرفة هل النص يحتوي على اسم سورة؟
    # مثلاً: "البقرة", "سورة البقره", "اريد سوره الكهف"
    
    # قائمة بأسماء السور للمقارنة
    # (هنا نبحث في قاعدة البيانات هل توجد سورة تطابق كلام المستخدم؟)
    found_surah = None
    
    # أولاً: بحث دقيق (هل الكلمة هي اسم سورة بالضبط؟)
    found_surah = quran.get_surah_by_name(text.strip())
    
    # ثانياً: إذا لم نجد، نبحث هل اسم السورة "جزء" من كلام المستخدم؟
    if not found_surah:
        for s in quran.data:
            s_name = s['name']['ar'].replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
            # إذا كان اسم السورة موجود داخل النص المرسل (مثال: النص "هات الكهف" -> "الكهف" موجودة)
            if s_name in clean_text:
                found_surah = s
                break
    
    # إذا وجدنا سورة، نرسلها فوراً
    if found_surah:
        client.send_text(chat_id, f"✅ فهمت أنك تريد سورة *{found_surah['name']['ar']}*.. جاري الإرسال..")
        send_surah_by_obj(chat_id, found_surah)
        return

    # --- 3. الأوامر المحددة (آية، صفحة) ---
    if text.startswith("آ ") or text.startswith("اية "):
        try:
            parts = text.split()
            # نتوقع: آ البقرة 5
            # نحاول تخطي الرمز الأول وأخذ الباقي
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
            # نستخرج الرقم من النص (مثال: ص 50 -> 50)
            p_num = int(''.join(filter(str.isdigit, text)))
            verses = quran.get_page_verses(p_num)
            if verses:
                msg = f"📄 *الصفحة {p_num}*\n\n" + " ".join(verses)
                threading.Thread(target=client.send_text, args=(chat_id, msg)).start()
                return
        except:
            pass

    # --- 4. رسالة الترحيب الذكية (إذا فشل كل شيء) ---
    welcome_msg = (
        "👋 *حياك الله في بوت القرآن الكريم*\n\n"
        "أنا تطورت وصرت أفهمك بشكل أفضل! 🤖✨\n\n"
        "📜 *كيف تستخدمني؟*\n"
        "فقط اكتب اسم السورة أو رقمها، وسأرسلها لك.\n\n"
        "جرب الآن:\n"
        "• اكتب: `البقرة`\n"
        "• أو اكتب رقم: `2`\n"
        "• أو اكتب: `سورة الكهف`\n"
        "• للصفحات اكتب: `ص 50`"
    )
    client.send_text(chat_id, welcome_msg)

# دالة مساعدة لتجهيز نص السورة وإرساله
def send_surah_by_obj(chat_id, surah):
    if not surah: return
    
    # تجميع الآيات
    verses = " ".join([f"{a['text']['ar']} ({a['number']})" for a in surah['verses']])
    
    # الترويسة الجميلة
    header = f"✨ *سورة {surah['name']['ar']}* ✨\n"
    header += f"🔢 ترتيبها: {surah['number']} | 📍 {surah['type']['ar']} | 📝 آياتها: {len(surah['verses'])}\n"
    header += "─" * 20 + "\n\n"
    
    if surah['number'] not in [1, 9]: 
        header += "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ\n"
    
    full_text = header + verses
    
    # الإرسال في الخلفية
    threading.Thread(target=client.send_text, args=(chat_id, full_text)).start()
