import os
import subprocess
import requests
from config import AUDIO_CACHE_DIR

class AudioMixer:
    def __init__(self):
        # التأكد من وجود مجلد الكاش
        if not os.path.exists(AUDIO_CACHE_DIR):
            os.makedirs(AUDIO_CACHE_DIR)
        
        # إنشاء ملف صمت قياسي (0.3 ثانية)
        self.silence_path = os.path.join(AUDIO_CACHE_DIR, "silence.mp3")
        if not os.path.exists(self.silence_path):
            self._create_silence_file()

    def _create_silence_file(self):
        """إنشاء ملف صمت مدته 0.3 ثانية بتردد 44100"""
        try:
            # -t 0.3 تعني 300 جزء من الثانية
            cmd = [
                'ffmpeg', '-y', '-f', 'lavfi', 
                '-i', 'anullsrc=r=44100:cl=stereo', 
                '-t', '0.3', 
                '-q:a', '2', 
                self.silence_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"⚠️ تحذير: فشل إنشاء ملف الصمت: {e}")

    def _download_file(self, url, filepath):
        if os.path.exists(filepath):
            return True
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, stream=True, headers=headers, timeout=15)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(4096):
                        f.write(chunk)
                return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
        return False

    def merge_verses(self, verses_list, reciter_url, reciter_id, repeat_count=1):
        downloaded_files = []
        
        # 1. تحميل ملفات الآيات (MP3)
        for v in verses_list:
            file_name = f"{reciter_id}_{str(v['sura']).zfill(3)}{str(v['ayah']).zfill(3)}.mp3"
            full_url = f"{reciter_url}{str(v['sura']).zfill(3)}{str(v['ayah']).zfill(3)}.mp3"
            local_path = os.path.join(AUDIO_CACHE_DIR, file_name)
            
            # نستخدم المسار المطلق لتجنب مشاكل FFmpeg
            abs_path = os.path.abspath(local_path)
            
            if self._download_file(full_url, abs_path):
                downloaded_files.append(abs_path)
            else:
                print(f"⚠️ فشل تحميل: {full_url}")

        if not downloaded_files:
            return None

        # اسم الملف الناتج (لاحظ الامتداد .m4a)
        first = verses_list[0]
        last = verses_list[-1]
        output_filename = f"merged_{reciter_id}_rep{repeat_count}_{first['sura']}_{first['ayah']}_to_{last['ayah']}.m4a"
        output_path = os.path.join(AUDIO_CACHE_DIR, output_filename)
        abs_output_path = os.path.abspath(output_path)

        # إذا الملف موجود مسبقاً، نرجعه فوراً
        if os.path.exists(abs_output_path):
            return output_path

        # 2. إنشاء قائمة الدمج (Concat List)
        list_txt_path = os.path.join(AUDIO_CACHE_DIR, f"list_{reciter_id}_{first['sura']}_{first['ayah']}.txt")
        
        try:
            with open(list_txt_path, 'w', encoding='utf-8') as f:
                silence_abs = os.path.abspath(self.silence_path)
                
                for file_path in downloaded_files:
                    # تكرار الآية + الصمت حسب العدد المطلوب
                    for _ in range(repeat_count):
                        # كتابة مسار الآية
                        safe_path = file_path.replace('\\', '/')
                        f.write(f"file '{safe_path}'\n")
                        
                        # كتابة مسار الصمت بعدها (إذا وجد)
                        if os.path.exists(silence_abs):
                            safe_silence = silence_abs.replace('\\', '/')
                            f.write(f"file '{safe_silence}'\n")

            # 3. تشغيل FFmpeg للدمج والتحويل إلى M4A (AAC)
            # هذا الأمر هو الحل السحري للآيفون:
            # -c:a aac : يحول الترميز إلى AAC (صديق آبل)
            # -movflags +faststart : يجعل الملف جاهزاً للتشغيل الفوري
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_txt_path,
                '-c:a', 'aac',       # ✅ التحويل إلى AAC
                '-b:a', '128k',      # جودة عالية
                '-ac', '2',          # Stereo
                '-ar', '44100',      # التردد القياسي
                '-movflags', '+faststart', # تحسين التوافق
                abs_output_path
            ]
            
            # تشغيل الأمر
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg Error: {e}")
            return None
        except Exception as e:
            print(f"❌ General Error: {e}")
            return None
        finally:
            # تنظيف ملف القائمة النصية
            if os.path.exists(list_txt_path):
                try: os.remove(list_txt_path)
                except: pass

    def clear_cache(self):
        """تنظيف الكاش"""
        for f in os.listdir(AUDIO_CACHE_DIR):
            try:
                if "silence" not in f:
                    os.remove(os.path.join(AUDIO_CACHE_DIR, f))
            except: pass
