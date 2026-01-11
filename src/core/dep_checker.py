import os
import sys
import shutil
import zipfile
import requests
import threading
from src.utils.config import BIN_DIR, FFMPEG_EXE, FFPROBE_EXE, FFMPEG_ZIP_URL, ensure_dires
from src.utils.logger import log

class DependencyManager:
    """
    Manages external dependencies like FFmpeg.
    Ensures they exist in the local app data so the user doesn't need to install them manually.
    """

    def check_ffmpeg(self) -> bool:
        """Video conversion requires FFmpeg. Checks if it exists."""
        return os.path.exists(FFMPEG_EXE) and os.path.exists(FFPROBE_EXE)

    def download_ffmpeg(self, progress_callback=None):
        """
        Downloads FFmpeg extract only the binaries, and cleans up.
        This runs in a blocking manner, usually called from a background thread.
        
        Args:
            progress_callback (function): Optional callback(float) for progress 0.0 to 1.0
        """
        ensure_dires()
        
        zip_path = os.path.join(BIN_DIR, "ffmpeg_temp.zip")
        
        log.info(f"Downloading FFmpeg from {FFMPEG_ZIP_URL}...")
        
        try:
            # 1. Download Content
            with requests.get(FFMPEG_ZIP_URL, stream=True) as r:
                r.raise_for_status()
                total_length = r.headers.get('content-length')
                
                with open(zip_path, 'wb') as f:
                    if total_length is None: # No content length header
                        f.write(r.content)
                        if progress_callback: progress_callback(0.5)
                    else:
                        dl = 0
                        total_length = int(total_length)
                        for data in r.iter_content(chunk_size=4096):
                            dl += len(data)
                            f.write(data)
                            if progress_callback:
                                # Mapping download to 0.0 - 0.8 range of total process
                                percent = (dl / total_length) * 0.8
                                progress_callback(percent)
            
            log.info("Download complete. Extracting...")
            
            # 2. Extract specific files
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # The zip structure is usually ffmpeg-version-essentials/bin/ffmpeg.exe
                # We need to find the paths inside the zip dynamically
                ffmpeg_src = None
                ffprobe_src = None
                
                for name in zf.namelist():
                    if name.endswith("bin/ffmpeg.exe"):
                        ffmpeg_src = name
                    elif name.endswith("bin/ffprobe.exe"):
                        ffprobe_src = name
                
                if not ffmpeg_src or not ffprobe_src:
                    raise Exception("Could not find ffmpeg.exe or ffprobe.exe in the downloaded zip!")

                # Extract specifically to target
                with zf.open(ffmpeg_src) as src, open(FFMPEG_EXE, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                
                with zf.open(ffprobe_src) as src, open(FFPROBE_EXE, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
            
            if progress_callback: progress_callback(0.9)

            # 3. Cleanup
            log.info("Cleaning up zip file...")
            if os.path.exists(zip_path):
                os.remove(zip_path)
            
            if progress_callback: progress_callback(1.0)
            log.info("FFmpeg setup complete.")

        except Exception as e:
            log.error(f"Failed to setup FFmpeg: {e}")
            # Cleanup on failure
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise e

    def get_ffmpeg_path(self):
        """Returns the path to the ffmpeg executable."""
        return FFMPEG_EXE
