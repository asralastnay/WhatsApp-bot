import os
import requests
from pydub import AudioSegment
from config import AUDIO_CACHE_DIR

class AudioMixer:
    def __init__(self):
        if not os.path.exists(AUDIO_CACHE_DIR):
            os.makedirs(AUDIO_CACHE_DIR)

    def _download_file(self, url, filepath):
        if os.path.exists(filepath):
            return True
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, stream=True, headers=headers)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
        return False

    # ✅ التعديل: استقبال repeat_count
    def merge_verses(self, verses_list, reciter_url, reciter_id, repeat_count=1):
        combined_audio = AudioSegment.empty()
        
        # إنشاء مقطع صمت مدته 300 ملي ثانية (أقل من ثانية بقليل) للفصل بين التكرارات
        silence = AudioSegment.silent(duration=300) 

        downloaded_files = []

        for v in verses_list:
            file_name = f"{reciter_id}_{str(v['sura']).zfill(3)}{str(v['ayah']).zfill(3)}.mp3"
            full_url = f"{reciter_url}{str(v['sura']).zfill(3)}{str(v['ayah']).zfill(3)}.mp3"
            local_path = os.path.join(AUDIO_CACHE_DIR, file_name)
            
            if self._download_file(full_url, local_path):
                try:
                    # تحميل الآية
                    ayah_segment = AudioSegment.from_mp3(local_path)
                    
                    # ✅ منطق التكرار:
                    # نكرر الآية + الصمت (عدد مرات التكرار)
                    # مثال: (الآية + صمت) + (الآية + صمت) ...
                    repeated_segment = (ayah_segment + silence) * repeat_count
                    
                    combined_audio += repeated_segment
                    downloaded_files.append(local_path)
                except Exception as e:
                    print(f"❌ خطأ دمج: {e}")
            else:
                print(f"⚠️ فشل تحميل: {full_url}")

        if len(downloaded_files) == 0:
            return None

        first = verses_list[0]
        last = verses_list[-1]
        
        # ✅ التعديل في اسم الملف: إضافة _rep{repeat_count}
        # مثال: merged_1_rep3_002_001_to_005.ogg
        output_filename = f"merged_{reciter_id}_rep{repeat_count}_{first['sura']}_{first['ayah']}_to_{last['ayah']}.ogg"
        output_path = os.path.join(AUDIO_CACHE_DIR, output_filename)

        if os.path.exists(output_path):
            return output_path

        try:
            combined_audio.export(output_path, format="ogg", codec="libopus", bitrate="128k")
            return output_path
        except Exception as e:
            print(f"Export Error: {e}")
            # Fallback
            output_filename = output_filename.replace(".ogg", ".mp3")
            output_path = os.path.join(AUDIO_CACHE_DIR, output_filename)
            combined_audio.export(output_path, format="mp3")
            return output_path

    def clear_cache(self):
        for f in os.listdir(AUDIO_CACHE_DIR):
            try: os.remove(os.path.join(AUDIO_CACHE_DIR, f))
            except: pass
