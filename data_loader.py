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

    # جلب سور لصفحة القائمة (مثلاً من 1 إلى 10)
    def get_surahs_paginated(self, page_index, limit=10):
        start = page_index * limit
        end = start + limit
        surahs = self.data[start:end]
        has_next = end < len(self.data)
        return surahs, has_next

    # البحث بالاسم (للأمر الكتابي)
    def get_surah_by_name(self, name):
        name = name.strip()
        # بحث دقيق
        return next((s for s in self.data if s['name']['ar'] == name), None)

    # البحث بالرقم (للأزرار) - يرجع السورة كاملة
    def get_surah_by_number(self, number):
        return next((s for s in self.data if s['number'] == number), None)

    # جلب آية
    def get_ayah(self, surah_name, ayah_num):
        surah = self.get_surah_by_name(surah_name)
        if surah:
            return next((a for a in surah['verses'] if a['number'] == ayah_num), None)
        return None

    # جلب صفحة
    def get_page_verses(self, page_num):
        return [f"{a['text']['ar']} ({a['number']})" for s in self.data for a in s['verses'] if a['page'] == page_num]
