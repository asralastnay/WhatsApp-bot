import json
import os
from config import USERS_FILE, DEFAULT_USER_SETTINGS

class UsersManager:
    def __init__(self):
        self.users = self._load_users()

    def _load_users(self):
        """تحميل المستخدمين من الملف عند تشغيل البوت"""
        if not os.path.exists(USERS_FILE):
            # إذا الملف غير موجود، نرجّع قاموس فارغ
            return {}
        
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ خطأ في تحميل ملف المستخدمين: {e}")
            return {}

    def _save_users(self):
        """حفظ التغييرات في الملف"""
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"❌ خطأ في حفظ ملف المستخدمين: {e}")

    def get_user_settings(self, chat_id):
        """جلب إعدادات مستخدم معين (وإنشاؤه إذا كان جديداً)"""
        if chat_id not in self.users:
            # مستخدم جديد! ننسخ الإعدادات الافتراضية له
            print(f"👤 مستخدم جديد: {chat_id}")
            self.users[chat_id] = DEFAULT_USER_SETTINGS.copy()
            self._save_users()
        
        return self.users[chat_id]

    def update_setting(self, chat_id, key, value):
        """تعديل إعداد معين (مثلاً إيقاف الصوت)"""
        if chat_id not in self.users:
            self.get_user_settings(chat_id) # تسجيله أولاً
            
        self.users[chat_id][key] = value
        self._save_users()
        print(f"⚙️ تم تحديث إعداد {key} للمستخدم {chat_id} إلى {value}")

    def get_user_reciter(self, chat_id):
        """دالة مختصرة لمعرفة رقم قارئ المستخدم"""
        settings = self.get_user_settings(chat_id)
        return settings.get("reciter_id", 1) # الافتراضي 1 إذا لم يوجد
