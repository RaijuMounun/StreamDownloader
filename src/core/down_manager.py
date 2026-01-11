import yt_dlp
import os
import threading
from src.utils.config import BIN_DIR
from src.utils.logger import log

class DownloadManager:
    """
    Wrapper around yt_dlp to handle operations programmatically.
    """
    def __init__(self):
        self._cancel_requested = False

    def get_ffmpeg_path(self):
        # We assume dep_checker has run and ffmpeg is in BIN_DIR
        return os.path.join(BIN_DIR, "ffmpeg.exe")

    def analyze_url(self, url):
        """
        Fetches metadata for the given URL without downloading.
        Returns a dictionary or raises Exception.
        """
        log.info(f"Analyzing URL: {url}")
        
        # Options for extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            # We don't need ffmpeg for analysis effectively, but good to have env clear
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                
                # Check for failure conditions where yt-dlp returns "success" but gives garbage
                extractor = info.get('extractor', '')
                url_res = info.get('url', '')
                
                is_generic = (extractor == 'generic')
                is_html5 = (extractor == 'html5')
                has_broken_url = ('${' in url_res) # Detect JS template strings like ${moneyVids...}
                has_no_content = (not info.get('entries') and not url_res)
                
                if (is_generic and has_no_content) or (is_html5 and has_broken_url) or (is_html5 and has_no_content):
                    log.warning(f"yt-dlp returned generic/broken info (Extractor: {extractor}, URL: {url_res}). Triggering fallback.")
                    raise ValueError("Generic/HTML5 extractor found no valid video content.")
                    
                return info
        except Exception as e:
            log.warning(f"Standard analysis failed in yt-dlp: {e}")
            log.info("Attempting Smart Scraper fallback...")
            
            # Fallback: Try to find the m3u8 link directly
            from src.core.scraper import SmartScraper
            scraper = SmartScraper()
            scan_result = scraper.deep_scan(url)
            
            if scan_result['video_url']:
                log.info(f"Found direct stream link: {scan_result['video_url']}")
                # Recursive call with the found m3u8
                # We merge found subs into the result if possible, 
                # but yt-dlp might not see them if we just give it the m3u8. 
                # We'll need to handle subs separately or inject them?
                # For now, let's just analyze the m3u8.
                # Need headers for the m3u8 request usually (Referer/User-Agent)
                # We can inject them into yt-dlp options
                m3u8_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://vidrame.pro/', # Best guess for m3u8 protection
                    'Origin': 'https://vidrame.pro'
                }
                
                # Create a new options dict with headers
                fallback_opts = ydl_opts.copy()
                fallback_opts['http_headers'] = m3u8_headers
                
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    info = ydl.extract_info(scan_result['video_url'], download=False)
                    # Hack: set the title to the original page title if possible? 
                    # info['title'] usually comes generic from m3u8.
                    
                    # Store found external subs in a custom field to return to UI
                    info['_external_subs'] = scan_result['subs']
                    return info
            else:
                log.error("Smart Scraper could not find media links.")
                raise e

    def download_stream(self, url, format_id, output_path, progress_hook=None):
        """
        Downloads the specified format. 
        Runs blocking (should be called in a thread).
        
        Args:
            url (str): The video URL
            format_id (str): The specific format string (e.g. "137+140")
            output_path (str): Full path for the output file (without extension if using merge)
                             OR with extension. yt-dlp handles templates.
            progress_hook (func): Callback for progress dict.
        """
        ffmpeg_location = self.get_ffmpeg_path()
        log.info(f"Starting download: {url} | Format: {format_id} | FFmpeg: {ffmpeg_location}")

        # Ensure output directory exists
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,  # Output template
            'ffmpeg_location': ffmpeg_location,
            'noplaylist': True,
            'merge_output_format': 'mp4', # Force merge to mp4 if video+audio
            'quiet': True,
            # Network Robustness
            'retries': float('inf'),
            'fragment_retries': float('inf'),
            'file_access_retries': 10,
            # HLS Optimization
            'hls_use_mpegts': True,
            'downloader': {
                'http_dash_segments': 'ffmpeg',
                'hls': 'ffmpeg',
            },
            # Progress hooks
            'progress_hooks': [progress_hook] if progress_hook else [],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            log.info("Download finished successfully.")
        except Exception as e:
            log.error(f"Download failed: {e}")
            raise e
