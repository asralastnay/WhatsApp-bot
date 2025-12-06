import json
from config import QURAN_FILE

class QuranHandler:
    def __init__(self):
        self.data = self._load_data()

    def _load_data(self):
        try:
            print("⏳ جاري تحميل قاعدة البيانات الجديدة...")
            with open(QURAN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ خطأ كارثي: فشل تحميل {QURAN_FILE}: {e}")
            return []

    # --- دالة مساعدة لتنظيف النصوص (للبحث الذكي) ---
    def _clean_text(self, text):
        if not isinstance(text, str): return str(text)
        return text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه').strip()

    # --- الدالة الأهم: تحويل الاسم إلى رقم السورة ---
    def _get_surah_number(self, identifier):
        """
        تأخذ اسم السورة (نص) أو رقمها (نص/رقم) وترجع رقم السورة الصحيح (int)
        """
        # 1. إذا كان المدخل رقماً
        if str(identifier).isdigit():
            return int(identifier)
        
        # 2. إذا كان اسماً (بحث ذكي)
        clean_id = self._clean_text(identifier)
        
        # نبحث في أول آية من كل سورة (لتسريع البحث)
        for ayah in self.data:
            if ayah['numberInSurah'] == 1:
                db_name = self._clean_text(ayah['sura_name'])
                if clean_id in db_name:
                    return ayah['sura_number']
        return None

    # --- جلب سورة كاملة ---
    def get_surah(self, identifier):
        sura_num = self._get_surah_number(identifier)
        if not sura_num: return None
        return [a for a in self.data if a['sura_number'] == sura_num]

    # --- جلب آية محددة ---
    def get_ayah(self, identifier, ayah_num):
        sura_num = self._get_surah_number(identifier)
        if not sura_num: return None

        for ayah in self.data:
            if ayah['sura_number'] == sura_num and ayah['numberInSurah'] == ayah_num:
                return ayah
        return None

    # --- جلب مجال آيات ---
    def get_ayah_range(self, identifier, start, end):
        sura_num = self._get_surah_number(identifier)
        if not sura_num: return None

        verses = []
        for ayah in self.data:
            if ayah['sura_number'] == sura_num:
                if start <= ayah['numberInSurah'] <= end:
                    verses.append(ayah)
        return verses

    # --- جلب صفحة ---
    def get_page(self, page_num):
        return [a for a in self.data if a['page'] == page_num]

    # --- جلب جزء ---
    def get_juz(self, juz_num):
        return [a for a in self.data if a['juz'] == juz_num]

    # --- جلب حزب ---
    def get_hizb(self, hizb_num):
        return [a for a in self.data if a['hizb'] == hizb_num]

    # --- ✅ جلب ربع حزب (تم التصحيح) ---
    def get_hizb_quarter(self, quarter_number):
        # البحث المباشر في القائمة المسطحة باستخدام المفتاح hizbQuarter
        # نستخدم .get() لتجنب الخطأ إذا كان المفتاح غير موجود في بعض السجلات
        return [a for a in self.data if a.get('hizbQuarter') == quarter_number]
    
    # --- دالة مساعدة لجلب اسم السورة من رقمها ---
    def get_surah_name_by_number(self, surah_num):
        for ayah in self.data:
            if ayah['sura_number'] == surah_num:
                return ayah['sura_name']
        return "غير معروف"
