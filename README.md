# Stream Downloader v4

<div align="center">
  <h3>Modern, Robust, and Smart Video Downloader</h3>
  <p>A powerful GUI application built with Python and CustomTkinter that combines the power of <b>yt-dlp</b> with custom scraping logic to handle complex streaming sites.</p>
</div>

---

## Features

*   **Modern UI:** Built with `CustomTkinter` for a sleek, dark-mode native experience.
*   **Smart Scraper Engine:**
    *   **Advanced Obfuscation Bypass:** Specifically engineered to handle complex sites like `hdfilmizle.to` and `vidrame.pro`. (Tested only on this sites.)
    *   **Auto-Decryption:** Solves custom obfuscation (Base64 + ROT13 + Reversal) automatically.
    *   **Fallback Inference:** If direct extraction fails, intelligent logic infers video URLs from subtitle data.
    *   **Robust Network Handling:** Sets correct Headers (Referer/User-Agent) to mimic a real browser.
*   **Powerful Downloading:**
    *   **Native FFmpeg Integration:** Uses `ffmpeg` for HLS (m3u8) streams for maximum stability and speed.
    *   **Infinite Retries:** Automatically resumes downloads if the network drops, without user intervention.
    *   **Quality Selection:** Choose exact video resolutions (e.g., 1080p, 720p).
    *   **Subtitle Support:** Auto-detects and downloads external subtitles (`.vtt`/`.srt`) with proper language tagging.
*   **Zero-Config Dependency Management:**
    *   Automatically checks for `ffmpeg`.
    *   Downloads and installs `ffmpeg` (80MB+) to a local user folder (`%LOCALAPPDATA%`) only if missing.
    *   Keeps your system clean.

## Installation

### Prerequisites
*   Python 3.10+
*   Windows (Tested on Windows 11/10)

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/StartledTurtle/StreamDownloader.git
    cd StreamDownloader
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application:**
    ```bash
    python src/main.py
    ```

## 📦 Building Standalone EXE

You can build a single-file `.exe` that works on any Windows machine (even without Python installed).

1.  **Run the Build Script:**
    ```bash
    python build_app.py
    ```
    *(This script automatically handles cleanup and triggers PyInstaller with the correct hidden imports for `customtkinter` and `yt_dlp`)*

2.  **Locate Output:**
    The final executable will be in the `dist/` folder.

3.  Or you can use the releases tab and download the latest release.

## Technical Details

*   **Core Library:** `yt_dlp` (Embedded as a library, not a separate exe).
*   **GUI Framework:** `customtkinter`.
*   **Scraping Logic:** Custom implementation in `src/core/scraper.py` using `requests` and `regex` for high-performance extraction without the overhead of Selenium.

## License

This project is open-source. Feel free to modify and distribute.
