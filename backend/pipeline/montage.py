import os, glob, random
from backend import ffmpeg
from backend.config import VIDEO, DEFAULT_CLIPS_DIR

def list_clips(clips_dir=DEFAULT_CLIPS_DIR):
    """Clips .mp4 dédoublonnés par taille de fichier."""
    seen = {}; clips = []
    for c in sorted(glob.glob(os.path.join(clips_dir, "*.mp4"))):
        sz = os.path.getsize(c)
        if sz in seen: continue
        seen[sz] = c; clips.append(c)
    return clips

def sentence_ranges(tokens, n_sent, duration):
    starts = []
    for si in range(n_sent):
        ws = [t for t in tokens if t["sent"] == si]
        starts.append(ws[0]["start"] if ws else (starts[-1] if starts else 0.0))
    if starts: starts[0] = 0.0
    ranges = []
    for si in range(n_sent):
        s = starts[si]; e = starts[si + 1] if si + 1 < n_sent else duration
        ranges.append((s, max(e, s + 0.3)))
    return ranges or [(0.0, duration)]

def _pick_clips(ranges, clips):
    durs = {c: ffmpeg.probe_duration(c) for c in clips}
    avail = clips[:]; random.shuffle(avail); chosen = []
    for (s, e) in ranges:
        L = e - s; pick = None
        for n, c in enumerate(avail):
            if durs[c] >= L + 0.15:
                pick = avail.pop(n); break
        if pick is not None:
            off = random.uniform(0, max(0.0, durs[pick] - L))
            chosen.append((pick, off, L, False))
        elif avail:
            c = max(avail, key=lambda x: durs[x]); avail.remove(c)
            chosen.append((c, 0.0, L, True))
        else:
            avail = clips[:]; random.shuffle(avail); c = avail.pop(0)
            chosen.append((c, 0.0, L, durs[c] < L + 0.15))
    return chosen

def render(audio_path, ass_path, ranges, out_path, clips_dir=DEFAULT_CLIPS_DIR):
    clips = list_clips(clips_dir)
    if not clips:
        raise RuntimeError(f"Aucun clip dans {clips_dir}")
    chosen = _pick_clips(ranges, clips)
    W, H, FPS, ZOOM = VIDEO["width"], VIDEO["height"], VIDEO["fps"], VIDEO["zoom"]
    zw, zh = int(W * ZOOM), int(H * ZOOM)
    cmd = [ffmpeg.FFMPEG, "-y"]
    for (c, off, L, loop) in chosen:
        if loop: cmd += ["-stream_loop", "-1", "-t", f"{L:.3f}", "-i", c]
        else: cmd += ["-ss", f"{off:.3f}", "-t", f"{L:.3f}", "-i", c]
    cmd += ["-i", audio_path]
    N = len(chosen); fc = []
    for k in range(N):
        fc.append(f"[{k}:v]scale={zw}:{zh}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H},setsar=1,fps={FPS},format=yuv420p[v{k}]")
    fc.append("".join(f"[v{k}]" for k in range(N)) + f"concat=n={N}:v=1:a=0[cv]")
    # chemin .ass relatif (exécution depuis son dossier) pour éviter l'échappement Windows
    ass_dir = os.path.dirname(os.path.abspath(ass_path))
    ass_name = os.path.basename(ass_path)
    fc.append(f"[cv]ass={ass_name}[vout]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{N}:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-r", str(FPS), "-shortest",
            "-movflags", "+faststart", "-map_metadata", "-1", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=ass_dir)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"Rendu échoué: {r.stderr[-400:]}")
    return out_path
