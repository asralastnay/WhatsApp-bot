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
        
        # نبحث في أول آية من كل سورة (لأن القاعدة مسطحة)
        # لتسريع البحث، نمر على البيانات ونفحص الآيات رقم 1 فقط
        for ayah in self.data:
            if ayah['numberInSurah'] == 1:
                # اسم السورة في القاعدة يكون "سورة الفاتحة"
                db_name = self._clean_text(ayah['sura_name']) # سوره الفاتحه
                
                # هل الاسم المدخل جزء من اسم القاعدة؟ (مثلاً "فاتحة" موجودة في "سورة الفاتحة")
                if clean_id in db_name:
                    return ayah['sura_number']
        return None

    # --- جلب سورة كاملة ---
    def get_surah(self, identifier):
        sura_num = self._get_surah_number(identifier)
        if not sura_num: return None

        # تصفية الآيات التابعة لهذه السورة
        verses = [a for a in self.data if a['sura_number'] == sura_num]
        return verses

    # --- جلب آية محددة ---
    def get_ayah(self, identifier, ayah_num):
        sura_num = self._get_surah_number(identifier)
        if not sura_num: return None

        # البحث عن الآية (رقم السورة + رقم الآية داخل السورة)
        for ayah in self.data:
            if ayah['sura_number'] == sura_num and ayah['numberInSurah'] == ayah_num:
                return ayah
        return None

    # --- جلب مجال آيات (للمونتاج الصوتي) ---
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

    # --- جلب حزب (الميزة الجديدة) ---
    def get_hizb(self, hizb_num):
        return [a for a in self.data if a['hizb'] == hizb_num]
        # 

    def get_hizb_quarter(self, quarter_number):
        """جلب آيات الربع المحدد (hizbQuarter)"""
        verses = []
        for sura in self.quran_data:
            for ayah in sura['verses']:
                # التأكد من وجود المفتاح ومطابقته للرقم المطلوب
                if ayah.get('hizbQuarter') == quarter_number:
                    # ننسخ الآية لنضيف لها اسم السورة ورقمها (مهم للعرض)
                    ayah_copy = ayah.copy()
                    ayah_copy['sura_name'] = sura['name']
                    ayah_copy['sura_number'] = sura['id']
                    verses.append(ayah_copy)
        return verses

    
    # --- دالة مساعدة لجلب اسم السورة من رقمها (للعرض) ---
    def get_surah_name_by_number(self, surah_num):
        for ayah in self.data:
            if ayah['sura_number'] == surah_num:
                return ayah['sura_name']
        return "غير معروف"
