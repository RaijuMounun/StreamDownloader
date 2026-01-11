import customtkinter as ctk
from tkinter import filedialog
import threading

class UrlInputFrame(ctk.CTkFrame):
    def __init__(self, master, on_analyze_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.on_analyze = on_analyze_callback

        self.label = ctk.CTkLabel(self, text="Video / Page URL:")
        self.label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))

        self.entry = ctk.CTkEntry(self, placeholder_text="Paste link (YouTube, Site URL, or direct m3u8)...")
        self.entry.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 10))

        self.btn_analyze = ctk.CTkButton(self, text="Analyze", command=self.on_analyze_click)
        self.btn_analyze.grid(row=1, column=1, padx=10, pady=(5, 10))

    def on_analyze_click(self):
        url = self.entry.get()
        if url:
            self.on_analyze(url)

    def set_input_state(self, state):
        self.entry.configure(state=state)
        self.btn_analyze.configure(state=state)

class VideoInfoFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        # Title
        self.title_label = ctk.CTkLabel(self, text="No Video Selected", font=("Arial", 16, "bold"), wraplength=400)
        self.title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        # Quality Selection
        self.quality_label = ctk.CTkLabel(self, text="Quality:")
        self.quality_label.grid(row=1, column=0, sticky="w", padx=10)
        
        self.quality_combo = ctk.CTkComboBox(self, values=["Best"])
        self.quality_combo.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

    def update_info(self, title, formats):
        self.title_label.configure(text=title)
        self.formats_data = formats 
        display_values = [f['label'] for f in formats]
        self.quality_combo.configure(values=display_values)
        if display_values:
            self.quality_combo.set(display_values[0])
    
    def get_selected_format_id(self):
        if not hasattr(self, 'formats_data') or not self.formats_data:
            return None
        selected_label = self.quality_combo.get()
        for f in self.formats_data:
            if f['label'] == selected_label:
                return f['id']
        return "best"

class SubtitleSelectionFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, label_text="Subtitles", orientation="vertical", height=150, **kwargs)
        self.checkboxes = []

    def update_subs(self, sub_list):
        """
        sub_list: list of dicts/strings. 
        If strings: just urls. 
        If dicts: {'lang': 'en', 'url': '...', 'ext': 'vtt'}
        """
        # Clear existing
        for cb in self.checkboxes:
            cb.destroy()
        self.checkboxes = []

        if not sub_list:
            lbl = ctk.CTkLabel(self, text="No subtitles found.")
            lbl.pack(anchor="w", padx=5)
            self.checkboxes.append(lbl)
            return

        for i, sub in enumerate(sub_list):
            # Try to get a display name
            if isinstance(sub, dict):
                text = f"{sub.get('lang', 'Unknown')} ({sub.get('ext', 'sub')})"
                val = sub.get('url')
            else:
                # Assuming string url
                filename = sub.split('/')[-1].split('?')[0]
                text = f"Subtitle {i+1} ({filename})"
                val = sub
            
            cb = ctk.CTkCheckBox(self, text=text)
            cb.pack(anchor="w", padx=5, pady=2)
            # Store the value in the checkbox object dynamically
            cb.sub_url = val 
            self.checkboxes.append(cb)

    def get_selected_subs(self):
        selected = []
        for cb in self.checkboxes:
            if isinstance(cb, ctk.CTkCheckBox) and cb.get() == 1:
                selected.append(cb.sub_url)
        return selected

class DownloadControlFrame(ctk.CTkFrame):
    def __init__(self, master, on_download_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.on_download = on_download_callback

        self.btn_download = ctk.CTkButton(self, text="Download", command=self.on_download_click, fg_color="green", hover_color="darkgreen")
        self.btn_download.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.progress_bar.grid_remove() 

        self.status_label = ctk.CTkLabel(self, text="Ready")
        self.status_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)

    def on_download_click(self):
        self.on_download()

    def start_progress(self):
        self.btn_download.configure(state="disabled")
        self.progress_bar.grid()
        self.progress_bar.set(0)
        self.status_label.configure(text="Initializing...")

    def update_progress(self, percentage, status_text):
        self.progress_bar.set(percentage)
        self.status_label.configure(text=status_text)

    def finish_progress(self):
        self.btn_download.configure(state="normal")
        self.progress_bar.grid_remove()
        self.status_label.configure(text="Download Complete!")
    
    def error_progress(self, msg):
        self.btn_download.configure(state="normal")
        self.progress_bar.grid_remove()
        self.status_label.configure(text=f"Error: {msg}", text_color="red")
