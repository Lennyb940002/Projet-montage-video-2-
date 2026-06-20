"""Renderer — EXÉCUTION PURE. Consomme un VideoRecipe gelé, ne décide rien.
Texte (overlay ASS) = dernier filtre => toujours par-dessus les visuels.
Layouts V1 : split_2, reveal."""
import os, re
from backend import ffmpeg
from backend.config import SILENT

# Les emojis couleur ne rendent pas via libass (glyphes monochromes cassés) :
# on les retire du texte brûlé. (Rendu emoji couleur = overlay PNG, futur.)
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0000FE00-\U0000FE0F\U0001F1E6-\U0001F1FF\U0000200D\U000020E3]+",
    flags=re.UNICODE)


def _strip_emoji(text):
    return re.sub(r"\s{2,}", " ", _EMOJI_RE.sub("", text)).strip()

_W, _H, _FPS = SILENT["width"], SILENT["height"], SILENT["fps"]
_IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")


def _is_image(path):
    return os.path.splitext(path)[1].lower() in _IMG_EXT


def _dewm():
    """Préfixe de filtre de-watermark : léger zoom biaisé HAUT-GAUCHE pour
    évincer le logo 'KlingAI' en bas-droite des clips de la banque. Retourne
    '' si désactivé (config SILENT['dewatermark'])."""
    cfg = SILENT.get("dewatermark") or {}
    if not cfg.get("enabled"):
        return ""
    z = cfg.get("zoom", 1.12)
    # scale up puis crop ancré (0,0) => on garde le haut-gauche, on jette le
    # bas-droite (zone du watermark). Sortie = résolution d'origine.
    return f"scale=iw*{z}:ih*{z},crop=iw/{z}:ih/{z}:0:0,"


def _input_args(path, duration):
    """Args ffmpeg d'entrée selon image vs vidéo, calés sur `duration`."""
    if _is_image(path):
        return ["-loop", "1", "-t", f"{duration:.3f}", "-i", path]
    return ["-stream_loop", "-1", "-t", f"{duration:.3f}", "-i", path]


def _ass_time(sec):
    cs = int(round(max(0, sec) * 100)); h = cs // 360000; cs %= 360000
    m = cs // 6000; cs %= 6000; s = cs // 100; c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _write_ass(recipe, path, lines):
    """Écrit un ASS minimal. `lines` = [(text, alignment, margin_v)]."""
    anim = ("{\\fad(150,0)}" if recipe.text_anim == "fade"
            else "{\\fad(80,0)\\fscx70\\fscy70\\t(0,160,\\fscx100\\fscy100)}")
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {_W}
PlayResY: {_H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{recipe.font},96,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,2,5,70,70,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = []
    end = _ass_time(recipe.duration)
    for text, align, mv in lines:
        clean = _strip_emoji(text)
        body.append(
            f"Dialogue: 0,{_ass_time(0)},{end},Default,,0,0,{mv},,"
            f"{{\\an{align}}}{anim}{clean.upper()}")
    open(path, "w", encoding="utf-8").write(header + "\n".join(body) + "\n")


def _render_split_2(recipe, out_path):
    a, b = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    # Caption conversationnelle en HAUT (style POV des références) + badges A/B
    _write_ass(recipe, ass_path, [
        (recipe.hook, 8, 360),
        ("A", 4, 0),     # an4 = milieu-gauche (sur la cellule A, haut)
        ("B", 1, 60),    # an1 = bas-gauche (sur la cellule B, bas)
    ])
    cmd = [ffmpeg.FFMPEG, "-y"]
    cmd += _input_args(a, d)
    cmd += _input_args(b, d)
    half = _H // 2
    dw = _dewm()
    fc = (f"[0:v]{dw}scale={_W}:{half}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{half},setsar=1[top];"
          f"[1:v]{dw}scale={_W}:{half}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{half},setsar=1[bot];"
          f"[top][bot]vstack=inputs=2,fps={_FPS},format=yuv420p[stack];"
          f"[stack]ass={os.path.basename(ass_path)}[vout]")
    cmd += ["-filter_complex", fc, "-map", "[vout]", "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(_FPS),
            "-movflags", "+faststart", "-an", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=os.path.dirname(os.path.abspath(ass_path)))
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"silent split_2 render failed: {r.stderr[-400:]}")


def _render_split_3(recipe, out_path):
    """3 bandes horizontales (1080 x H/3), une montre par bande. Caption en haut
    + badges 1/2/3. De-watermark appliqué à chaque input."""
    a, b, c = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    third = _H // 3
    # Caption haut (an8) + numéros : an7=haut-gauche (bande 1), an4=milieu-gauche
    # (bande 2), an1=bas-gauche (bande 3).
    _write_ass(recipe, ass_path, [
        (recipe.hook, 8, 360),
        ("1", 7, 60), ("2", 4, 0), ("3", 1, 60),
    ])
    dw = _dewm()
    cmd = [ffmpeg.FFMPEG, "-y"]
    cmd += _input_args(a, d) + _input_args(b, d) + _input_args(c, d)
    fc = (f"[0:v]{dw}scale={_W}:{third}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{third},setsar=1[c0];"
          f"[1:v]{dw}scale={_W}:{third}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{third},setsar=1[c1];"
          f"[2:v]{dw}scale={_W}:{third}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{third},setsar=1[c2];"
          f"[c0][c1][c2]vstack=inputs=3,fps={_FPS},format=yuv420p[stack];"
          f"[stack]ass={os.path.basename(ass_path)}[vout]")
    cmd += ["-filter_complex", fc, "-map", "[vout]", "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(_FPS),
            "-movflags", "+faststart", "-an", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=os.path.dirname(os.path.abspath(ass_path)))
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"silent split_3 render failed: {r.stderr[-400:]}")


def render_recipe(recipe, out_path):
    """Dispatch par layout. Étend ici pour ajouter des layouts (V1.2)."""
    if recipe.layout == "split_2":
        return _render_split_2(recipe, out_path)
    if recipe.layout == "split_3":
        return _render_split_3(recipe, out_path)
    if recipe.layout == "reveal":
        return _render_reveal(recipe, out_path)
    raise ValueError(f"unknown layout: {recipe.layout!r}")


def _render_reveal(recipe, out_path):
    """1 asset plein écran ; couche floutée par-dessus qui se dissout (flou->net)
    sur [reveal_at, reveal_at+reveal_fade]. Texte hook en bas."""
    (asset,) = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    _write_ass(recipe, ass_path, [(recipe.hook, 8, 360)])
    sigma = SILENT["reveal_blur_sigma"]
    at = min(SILENT["reveal_at"], max(0.0, d - SILENT["reveal_fade"]))
    fade = SILENT["reveal_fade"]
    cmd = [ffmpeg.FFMPEG, "-y"] + _input_args(asset, d)
    fc = (f"[0:v]{_dewm()}scale={_W}:{_H}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{_H},setsar=1,fps={_FPS},format=yuv420p,split[sharp][toblur];"
          f"[toblur]gblur=sigma={sigma}[blurred];"
          f"[blurred]fade=t=out:st={at:.3f}:d={fade:.3f}:alpha=1[blurfade];"
          f"[sharp][blurfade]overlay=format=auto[revealed];"
          f"[revealed]ass={os.path.basename(ass_path)}[vout]")
    cmd += ["-filter_complex", fc, "-map", "[vout]", "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(_FPS),
            "-movflags", "+faststart", "-an", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=os.path.dirname(os.path.abspath(ass_path)))
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"silent reveal render failed: {r.stderr[-400:]}")
