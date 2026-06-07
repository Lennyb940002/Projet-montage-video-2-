import os

FFMPEG_BIN = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

# Banque de clips muets par défaut (modifiable depuis l'UI plus tard)
DEFAULT_CLIPS_DIR = r"C:\Users\User\Downloads\Voix off\Clips\Muet"

WHISPER_MODEL = "small"

VIDEO = dict(width=1080, height=1920, fps=30, zoom=1.30)
SILENCE = dict(keep=0.10, threshold="-35dB")
SUBS = dict(font="Arial Black", size=84, maxwords=3,
            yellow="&H0000FFFF&", white="&H00FFFFFF&")

WORKDIR = os.path.join(os.path.expanduser("~"), ".automontage", "work")
os.makedirs(WORKDIR, exist_ok=True)
