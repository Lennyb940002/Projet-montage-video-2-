"""Moteur du format 'selection_rafale' (style LMDLS) — beat-synced.

Intro : photo streetwear (push-in) + hook qui pop chunk par chunk PILE sur le beat.
Rafale : clips produit coupés sur le beat + label (modèle / prix) qui pop.
Master : 1080x1920, 30 fps, audio loudnorm -16 LUFS.

Rendu 100% ffmpeg (drawtext avec fontfile TTF explicite -> pas besoin de fontconfig).
Chaque segment est encodé en intermédiaire identique puis concaténé (fiable > filtergraph géant).
"""
import os
import subprocess
import tempfile

W, H, FPS = 1080, 1920, 30
YELLOW = "#FFD400"
WHITE = "#FFFFFF"
RED = "#E0102B"
INK = "#141414"


def _resolve_ff():
    cands = [
        r"C:\Users\zbull\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin",
        r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin",
    ]
    for d in cands:
        ff = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(ff):
            return ff, os.path.join(d, "ffprobe.exe")
    return "ffmpeg", "ffprobe"


FF, FP = _resolve_ff()
FONT = os.environ.get("RAFALE_FONT", r"C:\Windows\Fonts\ariblk.ttf")
# fontfile pour filtergraph : forward slashes + échappement du ':' du lecteur
FONT_FF = FONT.replace("\\", "/").replace(":", "\\:")

_X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-video_track_timescale", "30000"]


def run(args):
    subprocess.run(args, check=True, capture_output=True,
                   encoding="utf-8", errors="replace")


def probe_dur(path):
    out = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out)


def _esc(expr):
    """Échappe les virgules des expressions ffmpeg (séparateur d'options)."""
    return expr.replace(",", "\\,")


def _fit_size(text, cap, ratio=0.92, adv=0.60):
    """Taille de police pour que le mot remplisse ~ratio de la largeur (Arial Black)."""
    if not text:
        return cap
    est = int((W * ratio) / (max(1, len(text)) * adv))
    return max(46, min(cap, est))


def _drawtext(textfile, y, size, color, appear, borderw=9, border_color="black@0.95"):
    """Un chunk de texte centré, qui apparaît INSTANTANÉMENT pile sur le beat (t=appear)."""
    tf = textfile.replace("\\", "/").replace(":", "\\:")
    alpha = f"gte(t,{appear})"      # 0 avant le beat, 1 dès le beat -> snap net
    opts = [
        f"fontfile='{FONT_FF}'",
        f"textfile='{tf}'",
        f"fontcolor={color}",
        f"fontsize={size}",
        f"borderw={borderw}", f"bordercolor={border_color}",
        "shadowx=0", "shadowy=5", "shadowcolor=black@0.35",
        "x=(w-text_w)/2",
        f"y={y}",
        f"alpha='{_esc(alpha)}'",
    ]
    return "drawtext=" + ":".join(opts)


def render_photo(img, seg, name, price, out, workdir, idx, price_lead=0.7):
    """Photo produit FOND BLANC : canvas blanc, contain + léger push-in, texte NOIR.
    Le prix (rouge) apparaît 'price_lead' s avant la fin = juste avant la montre suivante."""
    frames = int(round(seg * FPS))
    dt = []
    yb = int(H * 0.80)
    if name:
        p = os.path.join(workdir, f"pn_{idx:02d}.txt"); open(p, "w", encoding="utf-8").write(name)
        dt.append(_drawtext(p, yb, 66, INK, 0.15, borderw=5, border_color="white@0.85"))
    if price:
        p = os.path.join(workdir, f"pp_{idx:02d}.txt"); open(p, "w", encoding="utf-8").write(price)
        ap = round(max(0.2, seg - price_lead), 3)
        dt.append(_drawtext(p, yb + 92, 84, RED, ap, borderw=6, border_color="white@0.9"))
    # FIXE : aucun zoom, aucun tremblement (pas de zoompan).
    vf = ("scale=1000:1780:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1,"
          + (",".join(dt) + "," if dt else "") + "format=yuv420p")
    run([FF, "-y", "-loop", "1", "-t", f"{seg}", "-i", img,
         "-vf", vf, "-frames:v", str(frames), *_X264, "-an", out])


def _write_textfiles(chunks, workdir):
    files = []
    for i, ch in enumerate(chunks):
        p = os.path.join(workdir, f"txt_{i:02d}.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(ch["text"])
        files.append(p)
    return files


def render_intro(photo, chunks, out, dur, workdir):
    """chunks: [{text, color:'white'|'yellow', size(=cap), appear(sec)}].
    Photo FIXE (aucun filtre, aucun zoom). Mots énormes (remplissent la largeur),
    apparition instantanée sur le beat."""
    files = _write_textfiles(chunks, workdir)
    sizes = [_fit_size(c["text"], c.get("size", 150)) for c in chunks]
    heights = [int(s * 1.12) for s in sizes]
    total = sum(heights)
    y = int((H - total) / 2)               # bloc centré verticalement, plein cadre
    dt = []
    for i, ch in enumerate(chunks):
        color = YELLOW if ch["color"] == "yellow" else WHITE
        bw = max(6, int(sizes[i] * 0.055))
        dt.append(_drawtext(files[i], y, sizes[i], color, ch["appear"], bw))
        y += heights[i]
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
          + ",".join(dt) + ",format=yuv420p")
    frames = int(round(dur * FPS))
    run([FF, "-y", "-loop", "1", "-t", f"{dur}", "-i", photo,
         "-vf", vf, "-frames:v", str(frames), *_X264, "-an", out])


def render_clip(src, start, seg, label_top, label_price, out, workdir, idx, zoom=True):
    """Un plan produit (seg sec depuis start), cover 1080x1920 + label.
    zoom=True : push-in léger (plans fixes). zoom=False : cover statique (préserve
    le mouvement de la prise, ex. vidéo main qui tourne)."""
    frames = int(round(seg * FPS))
    dt = ""
    if label_top or label_price:
        parts = []
        yb = int(H * 0.82) if label_price else int(H * 0.85)
        if label_top:
            p = os.path.join(workdir, f"lbl_{idx:02d}_t.txt")
            open(p, "w", encoding="utf-8").write(label_top)
            parts.append(_drawtext(p, yb, 70, WHITE, 0.12))
        if label_price:
            p = os.path.join(workdir, f"lbl_{idx:02d}_p.txt")
            open(p, "w", encoding="utf-8").write(label_price)
            parts.append(_drawtext(p, yb + 86, 74, YELLOW, 0.20))
        dt = "," + ",".join(parts)
    if zoom:
        base = ("scale=1188:2112:force_original_aspect_ratio=increase,crop=1188:2112,"
                f"crop=w='1188-108*min(1,n/{frames})':h='2112-192*min(1,n/{frames})':"
                "x='(in_w-ow)/2':y='(in_h-oh)/2',scale=1080:1920,setsar=1")
    else:
        base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    vf = base + dt + ",format=yuv420p"
    run([FF, "-y", "-ss", f"{start}", "-t", f"{seg}", "-i", src,
         "-vf", vf, "-frames:v", str(frames), *_X264, "-an", out])


def concat(parts, out, workdir):
    lst = os.path.join(workdir, "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{p.replace(chr(92), '/')}'\n")
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])


def add_music(visual, music, mstart, vdur, out):
    """Colle la musique (depuis mstart), loudnorm -16 LUFS, fade out fin, coupe à vdur."""
    fade_out = max(0.0, vdur - 0.6)
    af = (f"atrim=0:{vdur},afade=t=out:st={fade_out:.2f}:d=0.6,"
          "loudnorm=I=-16:TP=-1.5:LRA=11")
    run([FF, "-y", "-i", visual, "-ss", f"{mstart}", "-i", music,
         "-filter:a", af, "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", "-shortest", out])


def plan_intro(hook, beats, drop=None):
    """Remplit 'appear' de chaque chunk et renvoie (hook, intro_dur).
    Si drop fourni : les mots se répartissent sur les beats AVANT le drop, et
    l'intro se termine PILE sur le drop (1re montre sur le drop).
    Sinon : 1 mot/beat, puis 1er temps fort ~1,2 s après le dernier mot."""
    b0 = beats[0]
    hook = [dict(c) for c in hook]
    n = len(hook)
    if drop:
        intro_dur = round(float(drop), 3)
        bb = [round(b - b0, 3) for b in beats if (b - b0) < intro_dur - 0.15]
        if len(bb) >= n and n > 1:
            for i, ch in enumerate(hook):
                ch["appear"] = bb[round(i * (len(bb) - 1) / (n - 1))]
        elif bb:
            for i, ch in enumerate(hook):
                ch["appear"] = bb[min(i, len(bb) - 1)]
        else:
            for i, ch in enumerate(hook):
                ch["appear"] = round(i * 0.4, 3)
    else:
        for i, ch in enumerate(hook):
            ch["appear"] = round(beats[min(i, len(beats) - 1)] - b0, 3)
        lo = hook[-1]["appear"] + 1.2
        bi = next((i for i in range(len(beats)) if i % 2 == 0 and beats[i] - b0 >= lo), None)
        if bi is None:
            bi = next((i for i in range(len(beats)) if beats[i] - b0 >= lo), len(beats) - 1)
        intro_dur = round(beats[bi] - b0, 3)
    return hook, intro_dur


def build_video(recipe, out):
    """recipe = {
        photo, hook_chunks:[{text,color,size,appear}], intro_dur,
        clips:[{src,start,seg,top,price}], music, music_start
    }"""
    workdir = tempfile.mkdtemp(prefix="rafale_")
    parts = []
    intro = os.path.join(workdir, "seg_00_intro.mp4")
    render_intro(recipe["photo"], recipe["hook_chunks"], intro, recipe["intro_dur"], workdir)
    parts.append(intro)
    for i, c in enumerate(recipe["clips"], 1):
        seg_out = os.path.join(workdir, f"seg_{i:02d}.mp4")
        render_clip(c["src"], c["start"], c["seg"], c.get("top", ""), c.get("price", ""),
                    seg_out, workdir, i)
        parts.append(seg_out)
    visual = os.path.join(workdir, "visual.mp4")
    concat(parts, visual, workdir)
    vdur = probe_dur(visual)
    add_music(visual, recipe["music"], recipe.get("music_start", 0.0), vdur, out)
    return out, vdur
