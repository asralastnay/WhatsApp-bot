# data_loader.py
import json
from config import JSON_FILE

class QuranHandler:
    def __init__(self):
        self.data = self._load_data()

    def _load_data(self):
        try:
            print("⏳ جاري تحميل قاعدة البيانات...")
            with open(JSON_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            print(f"❌ خطأ في تحميل الملف: {e}")
            return []

    # البحث بالاسم
    def get_surah_by_name(self, name):
        name = name.strip()
        # بحث دقيق
        res = next((s for s in self.data if s['name']['ar'] == name), None)
        if res: return res
        
        # بحث تقريبي (للمرونة)
        name_clean = name.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
        for s in self.data:
            s_clean = s['name']['ar'].replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
            if s_clean == name_clean:
                return s
        return None

    # البحث بالرقم
    def get_surah_by_number(self, number):
        return next((s for s in self.data if s['number'] == number), None)

    # جلب آية محددة
    def get_ayah(self, surah_name, ayah_num):
        surah = self.get_surah_by_name(surah_name)
        if surah:
            return next((a for a in surah['verses'] if a['number'] == ayah_num), None)
        return None

    # --- ميزة جديدة: جلب مجال من الآيات (من .. إلى) ---
    def get_ayah_range(self, surah_name, start_num, end_num):
        surah = self.get_surah_by_name(surah_name)
        if not surah: return None, None
        
        # التأكد من الحدود
        if start_num < 1: start_num = 1
        if end_num > len(surah['verses']): end_num = len(surah['verses'])
        if start_num > end_num: return surah, [] # مجال خاطئ

        # جلب الآيات (المصفوفة تبدأ من 0، ورقم الآية يبدأ من 1)
        # لذا نستخدم start_num - 1
        selected_verses = surah['verses'][start_num-1 : end_num]
        return surah, selected_verses

    # جلب صفحة
    def get_page_verses(self, page_num):
        return [f"{a['text']['ar']} ({a['number']})" for s in self.data for a in s['verses'] if a['page'] == page_num]

    # --- ميزة جديدة: جلب جزء كامل ---
    def get_juz_verses(self, juz_num):
        verses_list = []
        # نمر على كل السور، وكل الآيات، ونأخذ ما يطابق الجزء المطلوب
        for surah in self.data:
            for ayah in surah['verses']:
                if ayah.get('juz') == juz_num:
                    verses_list.append(f"{ayah['text']['ar']} ({ayah['number']})")
        return verses_list
