from backend.config import VIDEO

# Presets de sous-titres. mode = "karaoke" (mot surligné l'un après l'autre)
# ou "block" (le bloc s'affiche d'un coup, couleur unie).
STYLES = {
    "karaoke_yellow": {"label": "Karaoké jaune (centre)", "font": "Arial Black", "size": 84,
        "primary": "&H0000FFFF&", "secondary": "&H00FFFFFF&", "outline_col": "&H00000000&",
        "back_col": "&H00000000&", "border_style": 1, "outline": 5, "shadow": 2,
        "alignment": 5, "margin_v": 60, "mode": "karaoke"},
    "karaoke_green": {"label": "Karaoké vert (centre)", "font": "Arial Black", "size": 84,
        "primary": "&H0000FF00&", "secondary": "&H00FFFFFF&", "outline_col": "&H00000000&",
        "back_col": "&H00000000&", "border_style": 1, "outline": 5, "shadow": 2,
        "alignment": 5, "margin_v": 60, "mode": "karaoke"},
    "karaoke_pink": {"label": "Karaoké rose néon", "font": "Arial Black", "size": 88,
        "primary": "&H009314FF&", "secondary": "&H00FFFFFF&", "outline_col": "&H00000000&",
        "back_col": "&H00000000&", "border_style": 1, "outline": 6, "shadow": 2,
        "alignment": 5, "margin_v": 60, "mode": "karaoke"},
    "white_block": {"label": "Blanc gras (centre)", "font": "Arial Black", "size": 82,
        "primary": "&H00FFFFFF&", "secondary": "&H00FFFFFF&", "outline_col": "&H00000000&",
        "back_col": "&H00000000&", "border_style": 1, "outline": 5, "shadow": 2,
        "alignment": 5, "margin_v": 60, "mode": "block"},
    "bottom_white": {"label": "Bas classique", "font": "Arial", "size": 66,
        "primary": "&H00FFFFFF&", "secondary": "&H00FFFFFF&", "outline_col": "&H00000000&",
        "back_col": "&H00000000&", "border_style": 1, "outline": 4, "shadow": 1,
        "alignment": 2, "margin_v": 130, "mode": "block"},
    "boxed_bottom": {"label": "Encadré bas", "font": "Arial", "size": 62,
        "primary": "&H00FFFFFF&", "secondary": "&H00FFFFFF&", "outline_col": "&H64000000&",
        "back_col": "&H64000000&", "border_style": 3, "outline": 6, "shadow": 0,
        "alignment": 2, "margin_v": 130, "mode": "block"},
}
DEFAULT_STYLE = "karaoke_yellow"

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{primary},{secondary},{outline_col},{back_col},1,0,0,0,100,100,0,0,{border_style},{outline},{shadow},{alignment},80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

MAXWORDS = 3

def list_styles():
    return [{"key": k, "label": v["label"]} for k, v in STYLES.items()]

def ass_time(sec):
    if sec < 0: sec = 0
    cs = int(round(sec * 100)); h = cs // 360000; cs %= 360000
    m = cs // 6000; cs %= 6000; s = cs // 100; c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

def build_ass(tokens, n_sent, path, style=DEFAULT_STYLE):
    st = STYLES.get(style, STYLES[DEFAULT_STYLE])
    lines = [HEADER.format(w=VIDEO["width"], h=VIDEO["height"], **st)]
    chunks = []
    for si in range(n_sent):
        ws = [t for t in tokens if t["sent"] == si]
        for c in range(0, len(ws), MAXWORDS):
            chunks.append(ws[c:c + MAXWORDS])
    for ci, chunk in enumerate(chunks):
        start = chunk[0]["start"]
        end = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else chunk[-1]["end"] + 0.3
        if end <= start: end = start + 0.1
        if st["mode"] == "karaoke":
            n = len(chunk); parts = []
            for j in range(n):
                if j < n - 1:
                    k = int(round((chunk[j + 1]["start"] - chunk[j]["start"]) * 100))
                else:
                    k = int(round((chunk[j]["end"] - chunk[j]["start"]) * 100))
                if k < 1: k = 1
                parts.append("{\\k%d}%s" % (k, chunk[j]["disp"].upper()))
            text = " ".join(parts)
        else:  # block
            text = "{\\fad(80,0)}" + " ".join(w["disp"].upper() for w in chunk)
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,, " + text)
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path
