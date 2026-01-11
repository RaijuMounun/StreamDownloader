import os
import sys

# Application Metadata
APP_NAME = "StreamDownloader"
VERSION = "4.0.0"

# Main Data Directory (in %LOCALAPPDATA%)
# We use this path to store huge binaries (ffmpeg) to avoid polluting the app directory or desktop.
if os.name == 'nt':
    DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), APP_NAME)
else:
    # Linux/Mac fallback (mostly for dev environment if needed)
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

BIN_DIR = os.path.join(DATA_DIR, "bin")

# FFmpeg Paths
FFMPEG_EXE = os.path.join(BIN_DIR, "ffmpeg.exe")
FFPROBE_EXE = os.path.join(BIN_DIR, "ffprobe.exe")

# URL for FFmpeg (Windows 64-bit Essentials Build from gyan.dev)
# This is a static 'release' link ensuring we get a consistent structure.
FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def ensure_dires():
    """Creates the necessary directories if they don't exist."""
    if not os.path.exists(BIN_DIR):
        os.makedirs(BIN_DIR, exist_ok=True)
