import os
import json
import requests
import threading
from config import DEFAULT_USER_SETTINGS

class UsersManager:
    def __init__(self):
        # جلب رابط قاعدة البيانات من متغيرات البيئة في Render
        self.db_url = os.environ.get("FIREBASE_DB_URL")
        
        # التأكد من صحة الرابط
        if self.db_url and not self.db_url.endswith("/"):
            self.db_url += "/"

        self.users = {}
        
        # تحميل المستخدمين فور التشغيل
        self._load_users_from_firebase()

    def _load_users_from_firebase(self):
        """تحميل كل المستخدمين من فايربيس عند بدء التشغيل"""
        if not self.db_url:
            print("⚠️ تحذير: لم يتم وضع FIREBASE_DB_URL في Render! العمل سيكون محلياً ومؤقتاً.")
            return

        print("☁️ جاري تحميل بيانات المستخدمين من Firebase...")
        try:
            # نضيف users.json لنهاية الرابط لقراءة جدول المستخدمين
            response = requests.get(f"{self.db_url}users.json")
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    self.users = data
                    print(f"✅ تم تحميل {len(self.users)} مستخدم من السحابة.")
                else:
                    print("ℹ️ قاعدة البيانات فارغة، سيتم البدء من الصفر.")
                    self.users = {}
            else:
                print(f"❌ فشل الاتصال بفايربيس: {response.status_code} - {response.text}")
                self.users = {}
        except Exception as e:
            print(f"❌ خطأ في الاتصال بفايربيس: {e}")
            self.users = {}

    def _save_user_to_firebase(self, chat_id, user_data):
        """حفظ مستخدم واحد فقط في فايربيس (توفير للبيانات)"""
        if not self.db_url: return

        def _push():
            try:
                # نستخدم PATCH لتعديل هذا المستخدم فقط دون مسح البقية
                # الرابط يكون: https://.../users/CHAT_ID.json
                url = f"{self.db_url}users/{chat_id}.json"
                requests.patch(url, json=user_data)
                # print(f"☁️ Saved {chat_id} to cloud.") # تفعيل للديق فقط
            except Exception as e:
                print(f"❌ فشل حفظ المستخدم في السحابة: {e}")

        # نستخدم Thread لكي لا يتوقف البوت بانتظار رد السيرفر
        threading.Thread(target=_push, daemon=True).start()

    def get_user_settings(self, chat_id):
        """جلب الإعدادات (من الذاكرة لسرعة الرد)"""
        str_chat_id = str(chat_id)
        
        # إذا المستخدم غير موجود في الذاكرة
        if str_chat_id not in self.users:
            print(f"👤 مستخدم جديد: {str_chat_id}")
            # إنشاء إعدادات افتراضية
            new_settings = DEFAULT_USER_SETTINGS.copy()
            self.users[str_chat_id] = new_settings
            
            # حفظه في فايربيس فوراً
            self._save_user_to_firebase(str_chat_id, new_settings)
        
        return self.users[str_chat_id]

    def update_setting(self, chat_id, key, value):
        """تحديث إعداد وحفظه في السحابة"""
        str_chat_id = str(chat_id)
        
        # التأكد أن المستخدم موجود
        if str_chat_id not in self.users:
            self.get_user_settings(str_chat_id)
            
        # تحديث الذاكرة المحلية
        self.users[str_chat_id][key] = value
        
        # تحديث السحابة (Firebase)
        self._save_user_to_firebase(str_chat_id, self.users[str_chat_id])
        print(f"⚙️ تم تحديث {key} لـ {str_chat_id}")
