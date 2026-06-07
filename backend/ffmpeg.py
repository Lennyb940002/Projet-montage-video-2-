import os, subprocess
from backend.config import FFMPEG_BIN

FFMPEG = os.path.join(FFMPEG_BIN, "ffmpeg.exe")
FFPROBE = os.path.join(FFMPEG_BIN, "ffprobe.exe")

def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def probe_duration(path):
    r = run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise RuntimeError(f"Durée illisible pour {path}: {r.stderr[-300:]}")
