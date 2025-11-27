import os
import requests
from pydub import AudioSegment
from config import AUDIO_CACHE_DIR

class AudioMixer:
    def __init__(self):
        # التأكد من وجود مجلد الكاش
        if not os.path.exists(AUDIO_CACHE_DIR):
            os.makedirs(AUDIO_CACHE_DIR)

    def _download_file(self, url, filepath):
        """دالة مساعدة لتحميل الملف إذا لم يكن موجوداً"""
        if os.path.exists(filepath):
            return True # الملف موجود مسبقاً، لا داعي للتحميل
            
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
        return False

    def merge_verses(self, verses_list, reciter_url):
        """
        تقوم بدمج الآيات في ملف واحد.
        verses_list: قائمة تحتوي على قواميس [{'sura': 1, 'ayah': 1}, ...]
        reciter_url: رابط القارئ الأساسي
        """
        combined_audio = AudioSegment.empty()
        downloaded_files = []
        
        print(f"🎧 جاري دمج {len(verses_list)} آية...")

        for v in verses_list:
            # تنسيق اسم الملف (مثال: 002055.mp3)
            # zfill(3) تعني أضف أصفاراً لليسار حتى يصبح الرقم 3 خانات
            file_name = f"{str(v['sura']).zfill(3)}{str(v['ayah']).zfill(3)}.mp3"
            
            # الرابط الكامل ومسار الحفظ
            full_url = f"{reciter_url}{file_name}"
            local_path = os.path.join(AUDIO_CACHE_DIR, file_name)
            
            # تحميل الملف
            if self._download_file(full_url, local_path):
                try:
                    # إضافة الصوت للمونتاج
                    audio_segment = AudioSegment.from_mp3(local_path)
                    combined_audio += audio_segment
                    downloaded_files.append(local_path)
                except Exception as e:
                    print(f"❌ خطأ في معالجة ملف الصوت {file_name}: {e}")
            else:
                print(f"⚠️ فشل تحميل الملف: {full_url}")

        if len(downloaded_files) == 0:
            return None

        # اسم الملف النهائي (عشوائي أو بناء على الطلب لتجنب التكرار)
        # هنا سنسميه بناء على أول آية وآخر آية
        first = verses_list[0]
        last = verses_list[-1]
        output_filename = f"merged_{first['sura']}_{first['ayah']}_to_{last['ayah']}.mp3"
        output_path = os.path.join(AUDIO_CACHE_DIR, output_filename)

        # تصدير الملف النهائي
        print("💾 جاري تصدير الملف النهائي...")
        combined_audio.export(output_path, format="mp3")
        
        return output_path

    def clear_cache(self):
        """دالة تنظيف (اختيارية) لحذف الملفات القديمة"""
        for f in os.listdir(AUDIO_CACHE_DIR):
            os.remove(os.path.join(AUDIO_CACHE_DIR, f))
