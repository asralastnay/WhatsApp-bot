import json
import os
from config import USERS_FILE, DEFAULT_USER_SETTINGS

class UsersManager:
    def __init__(self):
        self.users = {}
        self._load_users()

    def _load_users(self):
        """تحميل المستخدمين مع حماية ضد الأخطاء"""
        if not os.path.exists(USERS_FILE):
            print("⚠️ ملف المستخدمين غير موجود، سيتم إنشاء واحد جديد.")
            self.users = {}
            return
        
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content: # إذا الملف فارغ
                    self.users = {}
                else:
                    self.users = json.loads(content)
            print(f"✅ تم تحميل {len(self.users)} مستخدم.")
        except Exception as e:
            print(f"❌ ملف المستخدمين تالف ({e})! سيتم إعادة ضبطه لتجنب توقف البوت.")
            self.users = {} # إعادة ضبط لتجنب الكراش
            self._save_users() # حفظ النسخة النظيفة

    def _save_users(self):
        """حفظ التغييرات"""
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"❌ فشل حفظ المستخدمين: {e}")

    def get_user_settings(self, chat_id):
        """جلب الإعدادات بأمان تام"""
        # تحويل الرقم لنص لضمان التوافق
        str_chat_id = str(chat_id)
        
        if str_chat_id not in self.users:
            print(f"👤 تسجيل مستخدم جديد: {str_chat_id}")
            # نسخ الإعدادات الافتراضية
            self.users[str_chat_id] = DEFAULT_USER_SETTINGS.copy()
            self._save_users()
        
        return self.users[str_chat_id]

    def update_setting(self, chat_id, key, value):
        str_chat_id = str(chat_id)
        if str_chat_id not in self.users:
            self.get_user_settings(str_chat_id)
            
        self.users[str_chat_id][key] = value
        self._save_users()
        print(f"⚙️ تحديث {key} لـ {str_chat_id}")
