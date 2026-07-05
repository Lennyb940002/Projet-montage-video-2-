"""Rendus des formats spéciaux (hors moteur policy split_2/3) : séquences d'écrans
(image/vidéo/texte) et grille 2x2 sur fond vidéo. ffmpeg direct, réutilisable par
les générateurs de lot. Aucune décision ici (banques/anti-répétition = générateur)."""
import os
from backend import ffmpeg
from backend.config import SILENT

W, H, FPS = SILENT["width"], SILENT["height"], SILENT["fps"]
FONT = SILENT["fonts"][0]
_IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")

_ASS_HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Big,{FONT},104,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,5,2,5,60,60,60,1
Style: Huge,{FONT},150,&H0000FFFF&,&H0000FFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,6,3,5,60,60,60,1
Style: Box,{FONT},60,&H00FFFFFF&,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,1,0,0,0,100,100,0,0,3,20,0,5,40,40,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _t(sec):
    cs = int(round(max(0, sec) * 100)); h = cs // 360000; cs %= 360000
    m = cs // 6000; cs %= 6000; s = cs // 100; c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _ass(path, events):
    body = []
    for text, style, tags, s0, s1 in events:
        body.append(f"Dialogue: 0,{_t(s0)},{_t(s1)},{style},,0,0,0,,"
                    f"{{{tags}}}{text.replace(chr(10), chr(92) + 'N')}")
    open(path, "w", encoding="utf-8").write(_ASS_HEAD + "\n".join(body) + "\n")


def _run(cmd, cwd):
    r = ffmpeg.run(cmd, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])


def _delogo(w, h):
    cfg = SILENT.get("dewatermark") or {}
    if not cfg.get("enabled"):
        return ""
    fx, fy, fw, fh = cfg.get("box", (0.68, 0.88, 0.30, 0.11))
    x, y = int(w * fx), int(h * fy)
    bw = max(1, min(int(w * fw), w - x - 2))
    bh = max(1, min(int(h * fh), h - y - 2))
    return f"delogo=x={x}:y={y}:w={bw}:h={bh},"


def _dims(path):
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", path])
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def _is_image(path):
    return os.path.splitext(path)[1].lower() in _IMG_EXT


def _seg_visual(path, events, dur, out):
    """1 segment : image (fit sur fond noir) ou vidéo (crop plein cadre + delogo)
    + textes ASS. `events` = [(text, style, tags)] (timing 0..dur ajouté ici)."""
    ass = out + ".ass"
    _ass(ass, [(t, s, tg, 0, dur) for (t, s, tg) in events])
    base = os.path.basename(ass)
    if _is_image(path):
        inp = ["-loop", "1", "-t", f"{dur}", "-i", os.path.abspath(path)]
        fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={FPS},"
              f"format=yuv420p,ass={base}[v]")
    else:
        w, h = _dims(path)
        inp = ["-stream_loop", "-1", "-t", f"{dur}", "-i", os.path.abspath(path)]
        fc = (f"[0:v]{_delogo(w, h)}scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},setsar=1,fps={FPS},format=yuv420p,ass={base}[v]")
    _run([ffmpeg.FFMPEG, "-y"] + inp + ["-filter_complex", fc, "-map", "[v]",
          "-t", f"{dur}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
          "-pix_fmt", "yuv420p", "-r", str(FPS), os.path.abspath(out)],
         os.path.dirname(os.path.abspath(ass)))


def _seg_text(events, dur, out, bg="0x0b0b0d"):
    ass = out + ".ass"
    _ass(ass, [(t, s, tg, 0, dur) for (t, s, tg) in events])
    fc = f"[0:v]fps={FPS},format=yuv420p,ass={os.path.basename(ass)}[v]"
    _run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-t", f"{dur}",
          "-i", f"color=c={bg}:s={W}x{H}:r={FPS}", "-filter_complex", fc,
          "-map", "[v]", "-t", f"{dur}", "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "23", "-pix_fmt", "yuv420p", "-r", str(FPS), os.path.abspath(out)],
         os.path.dirname(os.path.abspath(ass)))


def _concat(segs, out):
    lst = out + ".txt"
    with open(lst, "w", encoding="utf-8") as f:
        for s in segs:
            f.write(f"file '{os.path.abspath(s)}'\n")
    _run([ffmpeg.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", os.path.abspath(lst),
          "-c", "copy", os.path.abspath(out)], os.path.dirname(os.path.abspath(out)))
    os.remove(lst)


def render_sequence(screens, out):
    """screens = [{'kind':'visual'|'text', 'path'?, 'events':[(text,style,tags)], 'dur'}].
    'visual' = image ou vidéo (auto). Concatène en un seul MP4."""
    tmp = []
    for i, sc in enumerate(screens):
        seg = out + f".seg{i}.mp4"
        if sc["kind"] == "visual":
            _seg_visual(sc["path"], sc["events"], sc["dur"], seg)
        else:
            _seg_text(sc["events"], sc["dur"], seg)
        tmp.append(seg)
    _concat(tmp, out)
    for s in tmp:
        for p in (s, s + ".ass"):
            if os.path.exists(p):
                os.remove(p)


def render_grid_2x2(tiles, bg_video, hook, actions, out, dur=5.5):
    """4 tuiles en grille 2x2 sur fond vidéo assombri + hook haut + 4 cartouches
    d'action colorés sous les tuiles. `actions` = 4 libellés (ex 'LIKE = 1')."""
    ass = out + ".ass"
    tile = 420
    xs, ys = [110, 550], [430, 980]
    pos = [(xs[0], ys[0]), (xs[1], ys[0]), (xs[0], ys[1]), (xs[1], ys[1])]
    pal = ("&H0000FFFF&", "&H0000FF00&", "&H009314FF&", "&H00DC503C&")
    ev = [(hook, "Big", f"\\an5\\pos({W // 2},200)\\fs84", 0, dur)]
    for i, (px, py) in enumerate(pos):
        ev.append((actions[i], "Box",
                   f"\\an5\\pos({px + tile // 2},{py + tile + 46})\\3c{pal[i]}", 0, dur))
    _ass(ass, ev)
    cmd = [ffmpeg.FFMPEG, "-y", "-stream_loop", "-1", "-t", f"{dur}",
           "-i", os.path.abspath(bg_video)]
    for t in tiles:
        cmd += ["-loop", "1", "-t", f"{dur}", "-i", os.path.abspath(t)]
    parts = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
             f"eq=brightness=-0.35:saturation=0.85,setsar=1,fps={FPS},format=yuv420p[bg]"]
    for i in range(4):
        parts.append(f"[{i + 1}:v]scale={tile}:{tile}:force_original_aspect_ratio=decrease,"
                     f"pad={tile}:{tile}:(ow-iw)/2:(oh-ih)/2:white[t{i}]")
    chain = "[bg]"
    for i, (px, py) in enumerate(pos):
        nxt = "[grid]" if i == 3 else f"[o{i}]"
        parts.append(f"{chain}[t{i}]overlay={px}:{py}{nxt}")
        chain = f"[o{i}]"
    parts.append(f"[grid]ass={os.path.basename(ass)}[v]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[v]", "-t", f"{dur}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(FPS), os.path.abspath(out)]
    _run(cmd, os.path.dirname(os.path.abspath(ass)))
    if os.path.exists(ass):
        os.remove(ass)
