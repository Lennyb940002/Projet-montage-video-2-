"""Renderer — EXÉCUTION PURE. Consomme un VideoRecipe gelé, ne décide rien.
Texte (overlay ASS) = dernier filtre => toujours par-dessus les visuels.
Layouts : split_2, split_3, reveal.

Style (réf uniquebymparis) : cartouche coloré par montre (couleur ≈ couleur de
la montre, via SILENT['models']) + question blanche au centre. Watermark Kling
effacé par `delogo` (sans décalage -> montres restent centrées)."""
import os, re
from backend import ffmpeg
from backend.config import SILENT
from backend.silent import registry
from backend.silent import cta_v2

# Couleurs ASS (&H00BBGGRR) pour les label_modes non liés à la montre.
_RED = "&H003C1EDC&"; _GREEN = "&H005CC95C&"; _GOLD = "&H0033B4E7&"
_GREY = "&H00909090&"; _BLUE = "&H00DC503C&"
# Palette des cartouches numérotés/profils : couleurs distinctes, JAMAIS de blanc
# (sinon "3" blanc sur fond blanc = invisible).
_LABEL_PALETTE = ("&H0000FFFF&", "&H0000FF00&", "&H009314FF&", "&H00DC503C&")  # jaune, vert, rose, bleu

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


def _dims(path):
    """(width, height) de la 1re piste vidéo via ffprobe."""
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", path])
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def _delogo(w, h):
    """Filtre delogo (suffixe ',') pour effacer le watermark dans le coin
    bas-droite, calé sur les dimensions réelles de l'asset. PAS de décalage
    d'image -> la montre reste centrée. '' si désactivé."""
    cfg = SILENT.get("dewatermark") or {}
    if not cfg.get("enabled"):
        return ""
    fx, fy, fw, fh = cfg.get("box", (0.68, 0.88, 0.30, 0.11))
    x, y = int(w * fx), int(h * fy)
    bw = max(1, min(int(w * fw), w - x - 2))
    bh = max(1, min(int(h * fh), h - y - 2))
    return f"delogo=x={x}:y={y}:w={bw}:h={bh},"


def _model_meta(asset_path):
    """(nom affiché, couleur ASS du cartouche) d'après le dossier modèle parent."""
    folder = os.path.basename(os.path.dirname(asset_path))
    m = (SILENT.get("models") or {}).get(folder)
    if m:
        return m["name"], m["color"]
    d = SILENT.get("model_default") or {"name": folder or "Montre", "color": "&H00707070&"}
    return d["name"], d["color"]


_FORMATS_1A = {"test", "revelation_psy", "trahison", "perception", "test_perso"}


def _cell_labels(recipe):
    """[(texte, couleur)] par cellule. Formats 1A : labels décidés par la Policy
    (recipe.labels). Fail dur si un format 1A arrive sans labels (le fallback
    hardcodé est interdit sur les formats du guide). Legacy : label_mode."""
    if getattr(recipe, "labels", None) is not None:
        return [tuple(l) for l in recipe.labels]
    if recipe.mechanic in _FORMATS_1A:
        raise ValueError(
            f"labels manquants pour le format 1A {recipe.mechanic!r} : "
            "le fallback hardcodé est interdit sur les formats du guide")
    meta = registry.MECHANICS.get(recipe.mechanic, {})
    mode = meta.get("label_mode", "model_name")
    n = len(recipe.assets)
    pal = _LABEL_PALETTE   # jamais de blanc -> chiffres toujours visibles
    if mode == "number":
        return [(str(i + 1), pal[i % len(pal)]) for i in range(n)]
    if mode == "podium":
        return list(zip(["N°3", "N°2", "N°1"][:n], [_GREY, _BLUE, _GOLD][:n]))
    if mode == "before_after":
        return [("AVANT", _GREY), ("APRÈS", _GOLD)][:n]
    if mode == "wrong_right":
        return [("À ÉVITER", _RED), ("LE BON CHOIX", _GREEN)][:n]
    if mode == "category":
        return [("STYLE A", _BLUE), ("STYLE B", _RED)][:n]
    if mode == "profile":
        profs = ["MINIMALISTE", "AMBITIEUX", "CLASSIQUE", "AUDACIEUX"]
        return [(profs[i], pal[i % len(pal)]) for i in range(n)]
    return [_model_meta(a) for a in recipe.assets]   # "model_name" (défaut)


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
    """`lines` = [(text, kind, tags)] où kind ∈ {'q','box'} et tags = override
    inline ASS (ex: '\\an8\\3c&Hcolor&'). 'q' = question blanche ; 'box' =
    cartouche coloré (BorderStyle 3, couleur de boîte via \\3c)."""
    fade = "\\fad(120,0)"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {_W}
PlayResY: {_H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Q,{recipe.font},96,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,2,5,80,80,60,1
Style: Box,{recipe.font},58,&H00FFFFFF&,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,1,0,0,0,100,100,0,0,3,18,0,5,40,40,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    style_of = {"q": "Q", "box": "Box"}
    end = _ass_time(recipe.duration)
    body = []
    for text, kind, tags in lines:
        clean = _strip_emoji(text)
        body.append(
            f"Dialogue: 0,{_ass_time(0)},{end},{style_of[kind]},,0,0,0,,"
            f"{{{tags}{fade}}}{clean.upper()}")
    open(path, "w", encoding="utf-8").write(header + "\n".join(body) + "\n")


def _ass_header(recipe):
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {_W}
PlayResY: {_H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Q,{recipe.font},96,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,2,5,80,80,60,1
Style: Box,{recipe.font},58,&H00FFFFFF&,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,1,0,0,0,100,100,0,0,3,18,0,5,40,40,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _write_ass_timed(recipe, path, events):
    """ASS avec timing PAR événement. events = [(text, kind, tags, start_s, end_s)].
    Sert aux layouts séquentiels (montres successives + écran CTA)."""
    fade = "\\fad(120,0)"
    style_of = {"q": "Q", "box": "Box"}
    body = []
    for text, kind, tags, s0, s1 in events:
        clean = _strip_emoji(text)
        if not clean:
            continue
        body.append(
            f"Dialogue: 0,{_ass_time(s0)},{_ass_time(s1)},{style_of[kind]},,0,0,0,,"
            f"{{{tags}{fade}}}{clean.upper()}")
    open(path, "w", encoding="utf-8").write(_ass_header(recipe) + "\n".join(body) + "\n")


def _encode(inputs_cmd, fc, out_path, d, ass_dir, label, recipe, n_video):
    """Assemble filtres + map + encode. Bake un bed musical si recipe.music
    est défini (son baissé + fade) ; sinon vidéo muette (-an)."""
    cmd = list(inputs_cmd)
    amap = ["-an"]
    track = getattr(recipe, "music", None)
    if track:
        cmd += ["-stream_loop", "-1", "-t", f"{d:.3f}", "-i", os.path.abspath(track)]
        g = SILENT.get("music_gain_db", -8.0)
        fo = SILENT.get("music_fade_out_s", 0.8)
        fc = fc + (f";[{n_video}:a]volume={g}dB,afade=t=in:st=0:d=0.4,"
                   f"afade=t=out:st={max(0.0, d - fo):.3f}:d={fo:.3f},"
                   f"aformat=sample_fmts=fltp:channel_layouts=stereo[aout]")
        amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-filter_complex", fc, "-map", "[vout]"] + amap + [
        "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(_FPS),
        "-movflags", "+faststart", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=ass_dir)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"silent {label} render failed: {r.stderr[-400:]}")


def _render_split_2(recipe, out_path):
    a, b = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    (na, ca), (nb, cb) = _cell_labels(recipe)
    cx = _W // 2
    # Tout regroupé au CENTRE (zone sûre) : nom A juste au-dessus du hook,
    # nom B juste en dessous. Évite la notch (haut) et la description (bas).
    _write_ass(recipe, ass_path, [
        (na, "box", f"\\an5\\pos({cx},780)\\3c{ca}"),
        (recipe.hook, "q", f"\\an5\\pos({cx},960)"),
        (nb, "box", f"\\an5\\pos({cx},1140)\\3c{cb}"),
    ])
    half = _H // 2
    wa, ha = _dims(a); wb, hb = _dims(b)
    cmd = [ffmpeg.FFMPEG, "-y"] + _input_args(a, d) + _input_args(b, d)
    fc = (f"[0:v]{_delogo(wa,ha)}scale={_W}:{half}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{half},setsar=1[top];"
          f"[1:v]{_delogo(wb,hb)}scale={_W}:{half}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{half},setsar=1[bot];"
          f"[top][bot]vstack=inputs=2,fps={_FPS},format=yuv420p[stack];"
          f"[stack]ass={os.path.basename(ass_path)}[vout]")
    _encode(cmd, fc, out_path, d, os.path.dirname(os.path.abspath(ass_path)),
            "split_2", recipe, 2)


def _render_split_3(recipe, out_path):
    a, b, c = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    third = _H // 3
    metas = _cell_labels(recipe)
    cx = _W // 2
    # Cartouches calés sur chaque montre (centres de cellule 320/960/1600), bornés
    # à la zone sûre (<=1500) : symétriques autour du centre, jamais sur la frontière.
    ys = [430, 960, 1480]
    lines = [(recipe.hook, "q", f"\\an5\\pos({cx},270)")]
    for (name, col), y in zip(metas, ys):
        lines.append((name, "box", f"\\an5\\pos({cx},{y})\\3c{col}"))
    _write_ass(recipe, ass_path, lines)
    wa, ha = _dims(a); wb, hb = _dims(b); wc, hc = _dims(c)
    cmd = [ffmpeg.FFMPEG, "-y"] + _input_args(a, d) + _input_args(b, d) + _input_args(c, d)
    fc = (f"[0:v]{_delogo(wa,ha)}scale={_W}:{third}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{third},setsar=1[c0];"
          f"[1:v]{_delogo(wb,hb)}scale={_W}:{third}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{third},setsar=1[c1];"
          f"[2:v]{_delogo(wc,hc)}scale={_W}:{third}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{third},setsar=1[c2];"
          f"[c0][c1][c2]vstack=inputs=3,fps={_FPS},format=yuv420p[stack];"
          f"[stack]ass={os.path.basename(ass_path)}[vout]")
    _encode(cmd, fc, out_path, d, os.path.dirname(os.path.abspath(ass_path)),
            "split_3", recipe, 3)


def _render_reveal(recipe, out_path):
    """1 montre plein écran ; couche floutée qui se dissout (flou->net). Question
    en haut + cartouche nom en bas."""
    (asset,) = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    name, col = _model_meta(asset)
    cx = _W // 2
    _write_ass(recipe, ass_path, [
        (recipe.hook, "q", f"\\an5\\pos({cx},820)"),
        (name, "box", f"\\an5\\pos({cx},1080)\\3c{col}"),
    ])
    sigma = SILENT["reveal_blur_sigma"]
    at = min(SILENT["reveal_at"], max(0.0, d - SILENT["reveal_fade"]))
    fade = SILENT["reveal_fade"]
    w, h = _dims(asset)
    cmd = [ffmpeg.FFMPEG, "-y"] + _input_args(asset, d)
    fc = (f"[0:v]{_delogo(w,h)}scale={_W}:{_H}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{_H},setsar=1,fps={_FPS},format=yuv420p,split[sharp][toblur];"
          f"[toblur]gblur=sigma={sigma}[blurred];"
          f"[blurred]fade=t=out:st={at:.3f}:d={fade:.3f}:alpha=1[blurfade];"
          f"[sharp][blurfade]overlay=format=auto[revealed];"
          f"[revealed]ass={os.path.basename(ass_path)}[vout]")
    _encode(cmd, fc, out_path, d, os.path.dirname(os.path.abspath(ass_path)),
            "reveal", recipe, 1)


def _render_single(recipe, out_path):
    """1 montre plein écran + texte (POV : la phrase situation, centrée)."""
    (asset,) = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    cx = _W // 2
    _write_ass(recipe, ass_path, [(recipe.hook, "q", f"\\an5\\pos({cx},760)")])
    w, h = _dims(asset)
    cmd = [ffmpeg.FFMPEG, "-y"] + _input_args(asset, d)
    fc = (f"[0:v]{_delogo(w,h)}scale={_W}:{_H}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{_H},setsar=1,fps={_FPS},format=yuv420p,"
          f"ass={os.path.basename(ass_path)}[vout]")
    _encode(cmd, fc, out_path, d, os.path.dirname(os.path.abspath(ass_path)),
            "single", recipe, 1)


def _render_grid_4(recipe, out_path):
    """4 montres en grille 2×2 (540×960 chacune). Cartouches par cellule + hook
    au centre. De-watermark sur chaque input."""
    d = recipe.duration
    ass_path = out_path + ".ass"
    hw, hh = _W // 2, _H // 2
    labels = _cell_labels(recipe)
    cx = _W // 2
    # Cartouches en bas de chaque quadrant, dans la zone sûre (250..1500).
    pos = [(hw // 2, 760), (hw + hw // 2, 760),
           (hw // 2, 1240), (hw + hw // 2, 1240)]
    lines = [(recipe.hook, "q", f"\\an5\\pos({cx},{_H // 2})")]
    for (txt, col), (px, py) in zip(labels, pos):
        lines.append((txt, "box", f"\\an5\\pos({px},{py})\\3c{col}"))
    _write_ass(recipe, ass_path, lines)
    dims = [_dims(x) for x in recipe.assets]
    cmd = [ffmpeg.FFMPEG, "-y"]
    for x in recipe.assets:
        cmd += _input_args(x, d)
    parts = [
        f"[{i}:v]{_delogo(w, h)}scale={hw}:{hh}:force_original_aspect_ratio=increase,"
        f"crop={hw}:{hh},setsar=1[g{i}]"
        for i, (w, h) in enumerate(dims)]
    fc = ";".join(parts) + ";" + (
        f"[g0][g1]hstack=inputs=2[top];[g2][g3]hstack=inputs=2[bot];"
        f"[top][bot]vstack=inputs=2,fps={_FPS},format=yuv420p[stack];"
        f"[stack]ass={os.path.basename(ass_path)}[vout]")
    _encode(cmd, fc, out_path, d, os.path.dirname(os.path.abspath(ass_path)),
            "grid_4", recipe, 4)


def _render_sequence(recipe, out_path):
    """Layout V2 `sequence_N` : montres plein cadre SUCCESSIVES (une seule à la
    fois, même cadrage) puis un écran CTA final. Aucun split, aucune grille."""
    assets = list(recipe.assets)
    n = len(assets)
    d = recipe.duration
    cta_dur = min(1.4, d * 0.28)
    seg = (d - cta_dur) / n
    watch_total = seg * n
    ass_path = out_path + ".ass"
    cx = _W // 2
    labels = _cell_labels(recipe)                 # (nom, couleur) par montre
    # ASS daté : hook sur toute la séquence (haut, jamais sur le cadran),
    # cartouche de chaque montre pendant SON segment, CTA sur l'écran final.
    events = [(recipe.hook, "q", f"\\an5\\pos({cx},760)", 0.0, watch_total)]
    for i, (name, col) in enumerate(labels):
        events.append((name, "box", f"\\an5\\pos({cx},1200)\\3c{col}", i * seg, (i + 1) * seg))
    events.append((cta_v2.screen(getattr(recipe, "cta_type", None)), "q",
                   f"\\an5\\pos({cx},{_H // 2})", watch_total, d))
    _write_ass_timed(recipe, ass_path, events)
    # Vidéo : chaque montre plein cadre (trim=seg) + écran CTA noir, concaténés.
    cmd = [ffmpeg.FFMPEG, "-y"]
    for a in assets:
        cmd += _input_args(a, seg)
    cmd += ["-f", "lavfi", "-t", f"{cta_dur:.3f}",
            "-i", f"color=c=0x070707:s={_W}x{_H}:r={_FPS}"]
    parts = []
    for i, a in enumerate(assets):
        w, h = _dims(a)
        parts.append(
            f"[{i}:v]{_delogo(w, h)}scale={_W}:{_H}:force_original_aspect_ratio=increase,"
            f"crop={_W}:{_H},setsar=1,fps={_FPS},format=yuv420p,"
            f"trim=0:{seg:.3f},setpts=PTS-STARTPTS[v{i}]")
    parts.append(f"[{n}:v]setsar=1,format=yuv420p,setpts=PTS-STARTPTS[vcta]")
    concat_in = "".join(f"[v{i}]" for i in range(n)) + "[vcta]"
    parts.append(f"{concat_in}concat=n={n + 1}:v=1:a=0[cat]")
    parts.append(f"[cat]ass={os.path.basename(ass_path)}[vout]")
    _encode(cmd, ";".join(parts), out_path, d,
            os.path.dirname(os.path.abspath(ass_path)), f"sequence_{n}", recipe, n + 1)


def render_recipe(recipe, out_path):
    """Dispatch par layout."""
    dispatch = {"split_2": _render_split_2, "split_3": _render_split_3,
                "reveal": _render_reveal, "single": _render_single,
                "grid_4": _render_grid_4,
                "sequence_2": _render_sequence, "sequence_3": _render_sequence}
    fn = dispatch.get(recipe.layout)
    if fn is None:
        raise ValueError(f"unknown layout: {recipe.layout!r}")
    return fn(recipe, out_path)
