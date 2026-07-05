"""Prototypes rapides de 3 nouvelles mécaniques reels (fast-track 2026-07-05).
Rendus ffmpeg directs (hors moteur policy) — bruts mais visibles/testables.
1) Budget alternative  2) Prix choc  3) Tournoi 4 montres (grille 2x2 + fond vidéo).
NE POSTE RIEN. Sortie : output/prototypes_new_formats/."""
import os
import sys
import glob
import json
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import ffmpeg

W, H, FPS = 1080, 1920, 30
FONT = "Arial Black"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output", "prototypes_new_formats")
TILES = r"C:\Users\User\Desktop\Catalogue montre\_flowers_tiles"
CATA = r"C:\Users\User\Desktop\Catalogue montre"
BG_DIR = os.path.join(ROOT, "Vidéo montage fond")

_ASS_HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Big,{FONT},110,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,5,2,5,60,60,60,1
Style: Box,{FONT},64,&H00FFFFFF&,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,1,0,0,0,100,100,0,0,3,20,0,5,40,40,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _t(sec):
    cs = int(round(max(0, sec) * 100)); h = cs // 360000; cs %= 360000
    m = cs // 6000; cs %= 6000; s = cs // 100; c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _ass(path, events):
    """events = [(text, style, tags, start, end)]."""
    body = []
    for text, style, tags, s0, s1 in events:
        txt = text.replace("\n", "\\N")
        body.append(f"Dialogue: 0,{_t(s0)},{_t(s1)},{style},,0,0,0,,{{{tags}}}{txt}")
    open(path, "w", encoding="utf-8").write(_ASS_HEAD + "\n".join(body) + "\n")


def _run(cmd, cwd):
    r = ffmpeg.run(cmd, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])


# ---------------------------------------------------------------- séquences (1 & 2)
def _seg_image(img, text, dur, out):
    ass = out + ".ass"
    _ass(ass, [(text, "Big", f"\\an8\\pos({W//2},210)", 0, dur)])
    fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={FPS},format=yuv420p,"
          f"ass={os.path.basename(ass)}[v]")
    _run([ffmpeg.FFMPEG, "-y", "-loop", "1", "-t", f"{dur}", "-i", os.path.abspath(img),
          "-filter_complex", fc, "-map", "[v]", "-t", f"{dur}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
          "-pix_fmt", "yuv420p", "-r", str(FPS), os.path.abspath(out)],
         os.path.dirname(os.path.abspath(ass)))


def _seg_text(text, dur, out, bg="0x0b0b0d"):
    ass = out + ".ass"
    _ass(ass, [(text, "Big", f"\\an5\\pos({W//2},{H//2})", 0, dur)])
    fc = f"[0:v]fps={FPS},format=yuv420p,ass={os.path.basename(ass)}[v]"
    _run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-t", f"{dur}",
          "-i", f"color=c={bg}:s={W}x{H}:r={FPS}",
          "-filter_complex", fc, "-map", "[v]", "-t", f"{dur}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
          "-pix_fmt", "yuv420p", "-r", str(FPS), os.path.abspath(out)],
         os.path.dirname(os.path.abspath(ass)))


def _concat(segs, out):
    lst = out + ".txt"
    with open(lst, "w", encoding="utf-8") as f:
        for s in segs:
            f.write(f"file '{os.path.abspath(s)}'\n")
    _run([ffmpeg.FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", os.path.abspath(lst),
          "-c", "copy", os.path.abspath(out)], os.path.dirname(os.path.abspath(out)))


def render_sequence(screens, out):
    """screens = [{'kind':'image'|'text', 'img':..., 'text':..., 'dur':...}]."""
    segs = []
    for i, sc in enumerate(screens):
        seg = os.path.join(OUT, f"_seg_{os.path.basename(out)}_{i}.mp4")
        if sc["kind"] == "image":
            _seg_image(sc["img"], sc["text"], sc["dur"], seg)
        else:
            _seg_text(sc["text"], sc["dur"], seg)
        segs.append(seg)
    _concat(segs, out)
    for s in segs:
        for p in (s, s + ".ass"):
            if os.path.exists(p):
                os.remove(p)


# ---------------------------------------------------------------- tournoi (3)
def render_tournoi(tiles, bg_video, hook, mapping, out, dur=5.5):
    """4 tuiles en grille 2x2 sur fond vidéo assombri + hook + labels d'action."""
    ass = out + ".ass"
    tile = 420
    xs, ys = [110, 550], [430, 980]
    pos = [(xs[0], ys[0]), (xs[1], ys[0]), (xs[0], ys[1]), (xs[1], ys[1])]
    ev = [(hook, "Big", f"\\an5\\pos({W//2},200)\\fs84", 0, dur)]
    pal = ("&H0000FFFF&", "&H0000FF00&", "&H009314FF&", "&H00DC503C&")
    for i, (px, py) in enumerate(pos):
        cx = px + tile // 2
        ev.append((mapping[i], "Box", f"\\an5\\pos({cx},{py + tile + 46})\\3c{pal[i]}", 0, dur))
    _ass(ass, ev)
    cmd = [ffmpeg.FFMPEG, "-y", "-stream_loop", "-1", "-t", f"{dur}", "-i", os.path.abspath(bg_video)]
    for t in tiles:
        cmd += ["-loop", "1", "-t", f"{dur}", "-i", os.path.abspath(t)]
    parts = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
             f"eq=brightness=-0.4:saturation=0.85,setsar=1,fps={FPS},format=yuv420p[bg]"]
    for i in range(4):
        parts.append(f"[{i+1}:v]scale={tile}:{tile}:force_original_aspect_ratio=decrease,"
                     f"pad={tile}:{tile}:(ow-iw)/2:(oh-ih)/2:white[t{i}]")
    chain = "[bg]"
    for i, (px, py) in enumerate(pos):
        nxt = f"[o{i}]" if i < 3 else "[grid]"
        parts.append(f"{chain}[t{i}]overlay={px}:{py}{nxt}")
        chain = f"[o{i}]"
    parts.append(f"[grid]ass={os.path.basename(ass)}[v]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[v]", "-t", f"{dur}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(FPS), os.path.abspath(out)]
    _run(cmd, os.path.dirname(os.path.abspath(ass)))
    if os.path.exists(ass):
        os.remove(ass)


def _first(path_glob):
    files = sorted(glob.glob(path_glob))
    if not files:
        raise FileNotFoundError(path_glob)
    return files[0]


def main():
    os.makedirs(OUT, exist_ok=True)
    bg = _first(os.path.join(BG_DIR, "*.mp4"))
    manifest = []

    # --- Concept 1 : Budget alternative (Daytona) ---
    ref1 = _first(os.path.join(CATA, "Daytona", "*"))
    fc1 = _first(os.path.join(TILES, "Daytona", "*.png"))
    out1 = os.path.join(OUT, "concept1_budget.mp4")
    render_sequence([
        {"kind": "image", "img": ref1, "text": "Si t'as pas le budget pour ça…", "dur": 1.4},
        {"kind": "image", "img": fc1, "text": "…prends ça.", "dur": 1.4},
        {"kind": "text", "text": "même vibe\nbudget réel", "dur": 1.3},
        {"kind": "text", "text": "DM « MONTRE »", "dur": 1.3},
    ], out1)
    manifest.append({"concept": "budget_alternative", "hook": "Si t'as pas le budget pour ça, prends ça",
                     "assets": [ref1, fc1], "structure": "4 écrans séquentiels (img/img/texte/CTA)",
                     "nouveau_rendu": "oui (séquence d'écrans texte+image)", "export": out1})

    # --- Concept 2 : Prix choc (Nautilus) ---
    ref2 = _first(os.path.join(CATA, "Nautilus", "*"))
    fc2 = _first(os.path.join(TILES, "Nautilus", "*.png"))
    out2 = os.path.join(OUT, "concept2_prix_choc.mp4")
    render_sequence([
        {"kind": "image", "img": ref2, "text": "Eux la vendent 275 000 €", "dur": 1.5},
        {"kind": "image", "img": fc2, "text": "Moi, cette vibe à 275 €", "dur": 1.5},
        {"kind": "text", "text": "même énergie\npas le même prix", "dur": 1.3},
        {"kind": "text", "text": "Tu prends quoi ?", "dur": 1.3},
    ], out2)
    manifest.append({"concept": "prix_choc", "hook": "Eux la vendent 275 000, moi cette vibe à 275",
                     "assets": [ref2, fc2], "structure": "4 écrans séquentiels (comparaison prix)",
                     "nouveau_rendu": "oui (réutilise le rendu séquence)", "export": out2})

    # --- Concept 3 : Tournoi 4 montres ---
    t3 = [_first(os.path.join(TILES, m, "*.png"))
          for m in ["Datejust", "Daytona", "Seiko GMT", "Nautilus"]]
    out3 = os.path.join(OUT, "concept3_choix.mp4")
    render_tournoi(t3, bg, "TU CHOISIS LAQUELLE ?",
                   ["LIKE = 1", "PARTAGE = 2", "COMMENTE = 3", "ENREGISTRE = 4"], out3)
    manifest.append({"concept": "choix_4_montres", "hook": "Tu choisis laquelle ?",
                     "assets": t3 + [bg], "structure": "grille 2x2 + fond vidéo animé + 4 CTA d'action",
                     "nouveau_rendu": "oui (grille 2x2 sur fond vidéo)", "export": out3})

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("OK — 3 prototypes + manifest dans", OUT)


if __name__ == "__main__":
    main()
