import os
import subprocess
import requests
from config import AUDIO_CACHE_DIR

class AudioMixer:
    def __init__(self):
        if not os.path.exists(AUDIO_CACHE_DIR):
            os.makedirs(AUDIO_CACHE_DIR)
        
        self.silence_path = os.path.join(AUDIO_CACHE_DIR, "silence.mp3")
        if not os.path.exists(self.silence_path):
            self._create_silence_file()

    def _create_silence_file(self):
        """إنشاء ملف صمت 0.3 ثانية"""
        try:
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
        
        # 1. تحميل الملفات
        for v in verses_list:
            file_name = f"{reciter_id}_{str(v['sura']).zfill(3)}{str(v['ayah']).zfill(3)}.mp3"
            full_url = f"{reciter_url}{str(v['sura']).zfill(3)}{str(v['ayah']).zfill(3)}.mp3"
            local_path = os.path.join(AUDIO_CACHE_DIR, file_name)
            abs_path = os.path.abspath(local_path)
            
            if self._download_file(full_url, abs_path):
                downloaded_files.append(abs_path)
            else:
                print(f"⚠️ فشل تحميل: {full_url}")

        if not downloaded_files:
            return None

        # اسم الملف الناتج (m4a)
        first = verses_list[0]
        last = verses_list[-1]
        output_filename = f"merged_{reciter_id}_rep{repeat_count}_{first['sura']}_{first['ayah']}_to_{last['ayah']}.m4a"
        output_path = os.path.join(AUDIO_CACHE_DIR, output_filename)
        abs_output_path = os.path.abspath(output_path)

        if os.path.exists(abs_output_path):
            return output_path

        # 2. إنشاء القائمة
        list_txt_path = os.path.join(AUDIO_CACHE_DIR, f"list_{reciter_id}_{first['sura']}_{first['ayah']}.txt")
        
        try:
            with open(list_txt_path, 'w', encoding='utf-8') as f:
                silence_abs = os.path.abspath(self.silence_path)
                
                for file_path in downloaded_files:
                    for _ in range(repeat_count):
                        safe_path = file_path.replace('\\', '/')
                        f.write(f"file '{safe_path}'\n")
                        if os.path.exists(silence_abs):
                            safe_silence = silence_abs.replace('\\', '/')
                            f.write(f"file '{safe_silence}'\n")

            # 3. تشغيل FFmpeg مع إصلاح الخطأ (-vn)
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_txt_path,
                '-vn',               # ✅ هام جداً: تجاهل الصور (Album Art) لمنع الخطأ
                '-c:a', 'aac',       # ترميز AAC للآيفون
                '-b:a', '128k',
                '-ac', '2',          # ستيريو
                '-ar', '44100',
                '-strict', '-2',     # توافق إضافي
                '-movflags', '+faststart',
                abs_output_path
            ]
            
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            return output_path

        except subprocess.CalledProcessError as e:
            # طباعة الخطأ كاملاً لمعرفته في السجلات
            print(f"❌ FFmpeg Error Output: {e.stderr.decode() if e.stderr else 'No Details'}")
            return None
        except Exception as e:
            print(f"❌ General Error: {e}")
            return None
        finally:
            if os.path.exists(list_txt_path):
                try: os.remove(list_txt_path)
                except: pass

    def clear_cache(self):
        for f in os.listdir(AUDIO_CACHE_DIR):
            try:
                if "silence" not in f:
                    os.remove(os.path.join(AUDIO_CACHE_DIR, f))
            except: pass
