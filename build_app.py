import PyInstaller.__main__
import os
import shutil

# Clean previous builds
if os.path.exists("dist"):
    shutil.rmtree("dist")
if os.path.exists("build"):
    shutil.rmtree("build")

print("Starting Build Process...")

PyInstaller.__main__.run([
    'src/main.py',
    '--name=StreamDownloader',
    '--onefile',
    '--noconsole',
    '--collect-all=customtkinter',
    '--collect-all=yt_dlp',
    '--icon=NONE', # Can add icon later
    '--clean',
])

print("Build Complete! check '/dist' folder.")
