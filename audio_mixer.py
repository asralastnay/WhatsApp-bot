import os
import requests
from pydub import AudioSegment
# تأكد من أن config.py يحتوي على AUDIO_CACHE_DIR
from config import AUDIO_CACHE_DIR

class AudioMixer:
    def __init__(self):
        if not os.path.exists(AUDIO_CACHE_DIR):
            os.makedirs(AUDIO_CACHE_DIR)

    def _download_file(self, url, filepath):
        if os.path.exists(filepath):
            return True
        try:
            headers = {'User-Agent': 'Mozilla/5.0'} # إضافة User-Agent لتجنب الحظر
            response = requests.get(url, stream=True, headers=headers)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
        return False

    def merge_verses(self, verses_list, reciter_url):
        combined_audio = AudioSegment.empty()
        downloaded_files = []
        
        print(f"🎧 جاري دمج {len(verses_list)} آية...")

        for v in verses_list:
            file_name = f"{str(v['sura']).zfill(3)}{str(v['ayah']).zfill(3)}.mp3"
            full_url = f"{reciter_url}{file_name}"
            local_path = os.path.join(AUDIO_CACHE_DIR, file_name)
            
            if self._download_file(full_url, local_path):
                try:
                    audio_segment = AudioSegment.from_mp3(local_path)
                    combined_audio += audio_segment
                    downloaded_files.append(local_path)
                except Exception as e:
                    print(f"❌ خطأ في معالجة ملف الصوت {file_name}: {e}")
            else:
                print(f"⚠️ فشل تحميل الملف: {full_url}")

        if len(downloaded_files) == 0:
            return None

        first = verses_list[0]
        last = verses_list[-1]
        
        # التغيير 1: الامتداد أصبح .ogg (الأفضل للواتساب والآيفون)
        output_filename = f"merged_{first['sura']}_{first['ayah']}_to_{last['ayah']}.ogg"
        output_path = os.path.join(AUDIO_CACHE_DIR, output_filename)

        print("💾 جاري تصدير الملف بصيغة OGG (Opus)...")
        
        # التغيير 2: التصدير بصيغة opus وبجودة 128k
        # ملاحظة: pydub يحتاج ffmpeg مثبتاً على السيرفر (Render يوفره عادة)
        try:
            combined_audio.export(
                output_path, 
                format="ogg", 
                codec="libopus", 
                bitrate="128k" # جودة عالية كما طلبت
            )
            return output_path
        except Exception as e:
            print(f"❌ خطأ في التصدير (تأكد من وجود ffmpeg): {e}")
            # في حالة الفشل نعود للـ mp3 كاحتياطي
            output_filename = output_filename.replace(".ogg", ".mp3")
            output_path = os.path.join(AUDIO_CACHE_DIR, output_filename)
            combined_audio.export(output_path, format="mp3")
            return output_path

    def clear_cache(self):
        for f in os.listdir(AUDIO_CACHE_DIR):
            try:
                os.remove(os.path.join(AUDIO_CACHE_DIR, f))
            except: pass
