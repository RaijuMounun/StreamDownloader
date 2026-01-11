import customtkinter as ctk
import threading
import os
import requests
import re
import tkinter.messagebox as msgbox
from tkinter import filedialog
from src.gui.frames import UrlInputFrame, VideoInfoFrame, SubtitleSelectionFrame, DownloadControlFrame
from src.core.down_manager import DownloadManager
from src.core.dep_checker import DependencyManager
from src.utils.logger import log

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Stream Downloader v4.1")
        self.geometry("600x650") # Taller for subs
        
        # Managers
        self.down_manager = DownloadManager()
        self.dep_manager = DependencyManager()
        
        # UI Setup
        self._setup_ui()
        
        # Check dependencies after UI load
        self.after(100, self._check_dependencies)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # 1. URL Input
        self.input_frame = UrlInputFrame(self, on_analyze_callback=self.run_analysis)
        self.input_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)

        # 2. Video Info
        self.info_frame = VideoInfoFrame(self)
        self.info_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        
        # 3. Subtitle Selection (NEW)
        self.sub_frame = SubtitleSelectionFrame(self)
        self.sub_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)

        # 4. Download Controls
        self.download_frame = DownloadControlFrame(self, on_download_callback=self.run_download)
        self.download_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=20)
        
        # Status Bar
        self.status_bar = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_bar.grid(row=4, column=0, sticky="ew", pady=5)

    def _check_dependencies(self):
        """Runs in background to check/download FFmpeg."""
        if not self.dep_manager.check_ffmpeg():
            response = msgbox.askyesno("Missing Components", 
                                       "FFmpeg is required for high-quality downloads.\n"
                                       "Would you like to download it now? (~80MB)")
            if response:
                self.download_frame.start_progress()
                self.status_bar.configure(text="Downloading FFmpeg...", text_color="orange")
                t = threading.Thread(target=self._download_ffmpeg_thread)
                t.start()
            else:
                self.status_bar.configure(text="Warning: FFmpeg missing. Quality may be limited.", text_color="red")

    def _download_ffmpeg_thread(self):
        try:
            def update_ui(pct):
                self.download_frame.update_progress(pct, f"Downloading FFmpeg... {int(pct*100)}%")

            self.dep_manager.download_ffmpeg(progress_callback=update_ui)
            
            self.download_frame.finish_progress()
            self.status_bar.configure(text="Ready (FFmpeg Installed)", text_color="green")
            msgbox.showinfo("Success", "FFmpeg downloaded successfully!")
        except Exception as e:
            self.download_frame.error_progress("FFmpeg download failed.")
            self.status_bar.configure(text=f"Error: {e}", text_color="red")
            log.error(e)

    def run_analysis(self, url):
        self.input_frame.set_input_state("disabled")
        self.status_bar.configure(text="Analyzing... (This might take a moment)", text_color="yellow")
        
        t = threading.Thread(target=self._analysis_thread, args=(url,))
        t.start()

    def _analysis_thread(self, url):
        try:
            info = self.down_manager.analyze_url(url)
            
            # Formats
            formats = info.get('formats', [])
            clean_formats = []
            seen_res = set()
            formats.sort(key=lambda x: x.get('height') or 0, reverse=True)
            
            for f in formats:
                h = f.get('height')
                ext = f.get('ext')
                vcodec = f.get('vcodec')
                if h and vcodec != 'none': 
                    if h not in seen_res:
                        res_str = f.get('resolution') or f"{f.get('width')}x{h}"
                        clean_formats.append({
                            'id': f['format_id'],
                            'label': f"{h}p ({res_str}) - {ext}"
                        })
                        seen_res.add(h)
            
            if not clean_formats:
                clean_formats.append({'id': 'best', 'label': 'Best Available'})
                
            self.input_frame.set_input_state("normal")
            
            # --- Subtitles (External + Internal) ---
            subs_to_display = []
            
            # 1. Scraper found subs (List of URLs)
            ext_subs = info.get('_external_subs', [])
            import re
            for s in ext_subs:
                # Try to extract language from end of filename: ..._English.vtt
                lang_label = "External"
                m = re.search(r'_([a-zA-Z]+)\.(vtt|srt)$', s, re.IGNORECASE)
                if m:
                    lang_label = m.group(1).capitalize() # e.g. English
                
                subs_to_display.append({'lang': lang_label, 'url': s, 'ext': 'vtt/srt'})

            # 2. Internal subs (yt-dlp structure)
            # info['subtitles'] = {'en': [{'url': '...', 'ext': 'vtt'}], ...}
            internal_subs = info.get('subtitles', {})
            for lang, variants in internal_subs.items():
                for v in variants:
                    subs_to_display.append({
                        'lang': lang,
                        'url': v.get('url'),
                        'ext': v.get('ext', 'auto')
                    })
            
            # Update UI
            self.sub_frame.update_subs(subs_to_display)
            self.info_frame.update_info(info.get('title', 'Unknown Title'), clean_formats)
            
            self.current_dl_target = info.get('original_url', info.get('webpage_url', url))
            if info.get('url', '').endswith('.m3u8'):
                 self.current_dl_target = info['url']

            self.status_bar.configure(text="Analysis complete.", text_color="green")
            
        except Exception as e:
            self.input_frame.set_input_state("normal")
            self.status_bar.configure(text=f"Error: {str(e)[:50]}...", text_color="red")
            msgbox.showerror("Error", str(e))

    def run_download(self):
        if not hasattr(self, 'current_dl_target'):
            msgbox.showwarning("Warning", "Please analyze a link first.")
            return

        fmt_id = self.info_frame.get_selected_format_id()
        if fmt_id != 'best':
            final_fmt = f"{fmt_id}+bestaudio/best"
        else:
            final_fmt = "bestvideo+bestaudio/best"

        # Get Selected Subtitles
        selected_subs = self.sub_frame.get_selected_subs()

        save_path = filedialog.asksaveasfilename(defaultextension=".mp4", 
                                                 initialfile=self.info_frame.title_label.cget("text"),
                                                 filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")])
        if not save_path:
            return

        self.download_frame.start_progress()
        
        t = threading.Thread(target=self._download_thread, args=(self.current_dl_target, final_fmt, save_path, selected_subs))
        t.start()

    def _download_thread(self, url, fmt, path, sub_urls):
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    # 1. Clean ANSI codes from strings (yt-dlp can include colors)
                    def clean_ansi(s):
                        if not s: return ""
                        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                        return ansi_escape.sub('', str(s))

                    p_str = clean_ansi(d.get('_percent_str', ''))
                    eta_str = clean_ansi(d.get('_eta_str', 'Unknown'))
                    p_str = p_str.replace('%','')

                    # 2. Smart Percentage Calculation
                    # If percent string is empty, N/A, or 0.0 while we have bytes, try manual calc
                    p_val = 0.0
                    try:
                        p_val = float(p_str)
                    except:
                        pass
                        
                    if p_val == 0.0 or 'N/A' in p_str:
                        done = d.get('downloaded_bytes', 0)
                        total = d.get('total_bytes') or d.get('total_bytes_estimate')
                        if total and total > 0:
                            p_val = (done / total) * 100
                    
                    # 3. Format Output
                    pct_display = f"{p_val:.1f}%"
                    self.download_frame.update_progress(p_val/100, f"Downloading: {pct_display} | {eta_str} left")
                    
                except Exception as e:
                    # Fallback
                    self.download_frame.update_progress(0, "Downloading...")
                    # log.error(f"Progress Error: {e}") # Reduce log spam
            elif d['status'] == 'finished':
                self.download_frame.update_progress(1.0, "Merging / Finalizing...")

        try:
            self.down_manager.download_stream(url, fmt, path, progress_hook)
            
            # Download Selected Subtitles
            if sub_urls:
                self.download_frame.status_label.configure(text="Downloading Subtitles...")
                base_name = os.path.splitext(path)[0]
                for idx, sub_url in enumerate(sub_urls):
                    try:
                        # Determine extension
                        ext = 'vtt'
                        if 'srt' in sub_url: ext = 'srt'
                        
                        r = requests.get(sub_url)
                        out_name = f"{base_name}_sub_{idx}.{ext}"
                        with open(out_name, 'wb') as f:
                            f.write(r.content)
                        log.info(f"Saved subtitle: {out_name}")
                    except Exception as sx:
                        log.error(f"Failed to download sub {sub_url}: {sx}")

            self.download_frame.finish_progress()
            msgbox.showinfo("Success", "Download completed successfully!")
            self.status_bar.configure(text="Done.", text_color="green")
            
            # Open folder
            folder = os.path.dirname(path)
            try:
                os.startfile(folder)
            except: pass
            
        except Exception as e:
            self.download_frame.error_progress("Download failed.")
            self.status_bar.configure(text=f"Error: {e}", text_color="red")
            msgbox.showerror("Error", str(e))
