import os

MY_BOT_URL = "https://whatsapp-bot-jh7d.onrender.com"
# ---------------------------------------------------------
# 1. إعدادات اتصال WAHA (سيرفرك الجديد)
# ---------------------------------------------------------
# رابط سيرفر الواتساب الخاص بك
WAHA_BASE_URL = "https://surver-for-whatsapp.onrender.com"
# المفتاح الذي وضعته
WAHA_API_KEY = "12345"

# ---------------------------------------------------------
# 2. مسارات الملفات
# ---------------------------------------------------------
QURAN_FILE = "mainDataQuran.json"
RECITERS_FILE = "reciters.json"
USERS_FILE = "users.json"
AUDIO_CACHE_DIR = "audio_temp"

# ---------------------------------------------------------
# 3. إعدادات الأداء
# ---------------------------------------------------------
# WAHA يتحمل رسائل أطول، لكن نبقيها آمنة
MAX_MESSAGE_LENGTH = 35000 
DELAY_BETWEEN_PARTS = 3

# ---------------------------------------------------------
# 4. إعدادات المونتاج
# ---------------------------------------------------------
MAX_VERSES_TO_MERGE = 100

# ---------------------------------------------------------
# 5. الإعدادات الافتراضية
# ---------------------------------------------------------
DEFAULT_USER_SETTINGS = {
    "text_enabled": True,
    "audio_enabled": True,
    "reciter_id": 1,
    "merge_audio": True
}

if not os.path.exists(AUDIO_CACHE_DIR):
    os.makedirs(AUDIO_CACHE_DIR)
