# -*- coding: utf-8 -*-
"""Sous-titres 'style maison' (Arial Black blanc contour noir) synchronisés à la
voix, sur une vraie vidéo filmée. Garde l'audio original. Downscale en 1080x1920.

python deploy/make_subs.py <video_in> <words.json> <video_out>
"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

Y_SUB = 0.73          # position verticale des sous-titres (laisse les mains visibles)
SIZE = 74             # taille MAX ; chaque ligne rétrécit si trop large (anti-débordement)
MAXW = 3              # mots max par groupe (lignes courtes)
MAXDUR = 1.4          # durée max d'un groupe (s)


def chunk_words(words):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        dur = w["end"] - cur[0]["start"]
        end_punct = w["word"][-1:] in ".,!?:"
        if len(cur) >= MAXW or dur >= MAXDUR or end_punct:
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        s = c[0]["start"]; e = c[-1]["end"] + 0.12
        if i + 1 < len(chunks):
            e = min(e, chunks[i + 1][0]["start"] - 0.01)
        txt = " ".join(w["word"] for w in c).strip().strip(".,")
        txt = txt.replace(" '", "'").replace("' ", "'").replace(" ,", ",")   # apostrophes collées
        if txt:
            out.append((max(0, s), max(s + 0.2, e), txt))
    return out


def _sub_drawtext(textfile, y, size, color, start, end, borderw=9):
    tf = textfile.replace("\\", "/").replace(":", "\\:")
    en = E._esc(f"between(t,{round(start,2)},{round(end,2)})")
    opts = [f"fontfile='{E.FONT_FF}'", f"textfile='{tf}'", f"fontcolor={color}",
            f"fontsize={size}", f"borderw={borderw}", "bordercolor=black@0.95",
            "shadowx=0", "shadowy=5", "shadowcolor=black@0.6",
            "x=(w-text_w)/2", f"y={y}", f"enable='{en}'"]
    return "drawtext=" + ":".join(opts)


def main():
    vin, wjson, vout = sys.argv[1], sys.argv[2], sys.argv[3]
    words = json.load(open(wjson, encoding="utf-8"))
    subs = chunk_words(words)
    wd = tempfile.mkdtemp(prefix="subs_")
    y = int(E.H * Y_SUB)
    dt = []
    for i, (s, e, txt) in enumerate(subs):
        p = os.path.join(wd, f"s{i:03d}.txt")
        open(p, "w", encoding="utf-8").write(txt)
        color = E.YELLOW if ("€" in txt or "195" in txt) else E.WHITE
        size = E._fit_size(txt, SIZE, ratio=0.86, adv=0.64)   # rétrécit si la ligne est trop large
        dt.append(_sub_drawtext(p, y, size, color, s, e))
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
          + ",".join(dt) + ",format=yuv420p")
    E.run([E.FF, "-y", "-i", vin, "-vf", vf, *E._X264,
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", vout])
    print(f"OK -> {vout}  ({len(subs)} sous-titres, {E.probe_dur(vout):.1f}s)")


if __name__ == "__main__":
    main()
