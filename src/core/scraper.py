import requests
import re
import base64
import codecs
from urllib.parse import urljoin
from src.utils.logger import log

class SmartScraper:
    """
    Attempts to find .m3u8 and subtitle links in the HTML source using Regex.
    Includes recursive iframe scanning.
    """
    
    M3U8_PATTERNS = [
        r'["\']((?:https?:)?(?://|\\/\\/)[^"\']+\.m3u8[^"\']*)["\']',
        r'source\s*:\s*["\']((?:https?:)?(?://|\\/\\/)[^"\']+\.m3u8[^"\']*)["\']',
        r'file\s*:\s*["\']((?:https?:)?(?://|\\/\\/)[^"\']+\.m3u8[^"\']*)["\']',
    ]

    SUB_PATTERNS = [
        r'["\']((?:https?:)?(?://|\\/\\/)[^"\']+\.(?:vtt|srt)[^"\']*)["\']',
        r'kind\s*:\s*["\']captions["\'].*?src\s*:\s*["\']([^"\']+)["\']', 
    ]
    
    IFRAME_PATTERN = r'<iframe[^>]+(?:src|data-src)=["\']([^"\']+)["\']'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://google.com/'
        })

    def deep_scan(self, url, depth=0, referer=None):
        """
        Fetches URL, scans for media. If iframes found, scans them too (recursion limit 2).
        """
        if depth > 1: return {'video_url': None, 'subs': []}
        
        log.info(f"Deep Scanning (Depth {depth}): {url}")
        try:
            # Set Referer if provided
            if referer:
                self.session.headers.update({'Referer': referer})
                log.info(f"Set Referer to: {referer}")

                
            res = self.session.get(url, timeout=10)
            res.raise_for_status()
            html = res.text
            
            found_m3u8 = None
            found_subs = []

            # 1. Search M3U8 in current page
            found_m3u8 = self._find_m3u8(html, url)
            
            # 2. Search Subs in current page
            found_subs = self._find_subs(html, url)

            # 2.5 Fallback: Infer video from subtitles (Photostack specific)
            if not found_m3u8:
                for sub in found_subs:
                    m = re.search(r'photostack\.net/v/([^/]+)/', sub)
                    if m:
                        vid_id = m.group(1)
                        # Infer master.m3u8 link. Use split to get https://p2.photostack.net
                        base_host = sub.split('/v/')[0]
                        inferred = f"{base_host}/v/{vid_id}/master.m3u8"
                        log.info(f"Inferred video from subtitles: {inferred}")
                        found_m3u8 = inferred
                        break

            
            # 3. If no video, check Iframes
            # 3. If no video, check Iframes AND JS variables
            if not found_m3u8:
                # Standard Iframes
                iframes = re.findall(self.IFRAME_PATTERN, html)
                
                # Hidden JS Links (hdfilmizle/vidrame support)
                js_links = self._extract_from_js(html)
                
                all_candidates = iframes + js_links
                
                for src in all_candidates:
                    if not src: continue
                    src = src.replace(r'\/', '/') # Clean escaped slashes
                    
                    if not src.startswith('http'):
                        src = urljoin(url, src)
                    
                    # Avoid re-scanning parent or same url to prevent cycles (basic check)
                    if src == url: continue
                    
                    log.info(f"Checking embedded source: {src}")
                    sub_result = self.deep_scan(src, depth=depth+1, referer=url)
                    
                    if sub_result['video_url']:
                        found_m3u8 = sub_result['video_url']
                        found_subs.extend(sub_result['subs'])
                        break # Found it, stop scanning
            
            return {
                'video_url': found_m3u8,
                'subs': found_subs
            }

        except Exception as e:
            log.error(f"Deep scan failed at {url}: {e}")
            return {'video_url': None, 'subs': []}

    def _find_m3u8(self, html, base_url):
        for pattern in self.M3U8_PATTERNS:
            match = re.search(pattern, html)
            if match:
                m3u8 = match.group(1)
                if not m3u8.startswith('http'):
                    m3u8 = urljoin(base_url, m3u8)
                return m3u8.replace(r'\/', '/')
        return None

    def _find_subs(self, html, base_url):
        subs = []
        for pattern in self.SUB_PATTERNS:
            matches = re.findall(pattern, html)
            for sub in matches:
                if not sub.startswith('http'):
                    sub = urljoin(base_url, sub)
                sub = sub.replace(r'\/', '/')
                if sub not in subs:
                    subs.append(sub)
        return subs

    def _extract_from_js(self, html):
        """
        Extracts links hidden in JS variables (e.g. 'parts' JSON or 'configs' object).
        """
        links = []
        
        # 1. hdfilmizle.to 'parts' variable
        # let parts = [{"id":..., "data":"<iframe src=\"...\" ... >"}]
        parts_match = re.search(r'let\s+parts\s*=\s*(\[\{.*?\}\]);', html, re.DOTALL | re.IGNORECASE)
        if parts_match:
            # Extract src="..." inside the JSON string
            srcs = re.findall(r'src=\\"(https?:[^"\\]+)\\"', parts_match.group(1))
            links.extend(srcs)

        # 2. vidrame.pro 'configs' or file: "..."
        # Pattern A: file: EE.dd("...")
        ee_matches = re.findall(r'EE\.dd\(\s*["\']([^"\']+)["\']\s*\)', html)
        for enc_str in ee_matches:
            try:
                decrypted = self._decode_vidrame(enc_str)
                if decrypted and ('.m3u8' in decrypted or '.mp4' in decrypted):
                    links.append(decrypted)
            except Exception as e:
                log.error(f"Failed to decrypt Vidrame string: {e}")

        # Pattern B: file: "https://..."
        # We look for file: "http..." or source: "http..."
        # Pattern: file\s*:\s*["'](https?://[^"']+)["']
        file_matches = re.findall(r'(?:file|source)\s*:\s*["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
        links.extend(file_matches)
        
        return links

    def _decode_vidrame(self, encoded_str):
        """
        Decodes the Vidrame/Player obfuscation.
        Logic: Reverse(ROT13(Base64Decode(str.replace('d', '/'))))
        """
        # 1. Custom replacement
        # The JS replacement was .replace(/d/g, '/')
        # But wait, Base64 output can contain 'd'. 
        # The obfuscator probably replaced '/' with 'd' AFTER encoding.
        # So we reverse it here.
        s = encoded_str.replace('-', '+').replace('d', '/')
        
        # 2. Padding
        padding = 4 - (len(s) % 4)
        if padding != 4:
            s += '=' * padding
            
        try:
            # 3. Base64 Decode
            decoded_bytes = base64.b64decode(s)
            decoded_str = decoded_bytes.decode('latin1')
            
            # 4. ROT13
            rot13_str = codecs.decode(decoded_str, 'rot_13')
            
            # 5. Reverse
            final_url = rot13_str[::-1]
            return final_url
        except Exception as e:
            # log.warning(f"Decoding failed for {encoded_str}: {e}")
            return None


