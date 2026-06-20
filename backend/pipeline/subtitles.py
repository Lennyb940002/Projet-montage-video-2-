from backend.config import VIDEO, EMPHASIS

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
    "multicolor_fun": {"label": "Multicolore animé 🟢🟡 + emojis", "font": "Arial Black", "size": 86,
        "primary": "&H00FFFFFF&", "secondary": "&H00FFFFFF&", "outline_col": "&H00000000&",
        "back_col": "&H00000000&", "border_style": 1, "outline": 6, "shadow": 2,
        "alignment": 5, "margin_v": 60, "mode": "fun"},
    "premium_pop": {"label": "Premium Pop (emphase mots-clés)", "font": "Arial Black", "size": 82,
        # primary = couleur "passée" (jaune accent), secondary = couleur "à venir" (blanc).
        # \kf balaye secondary -> primary mot par mot pour créer un karaoké subtil sans bouger.
        "primary": "&H0000FFFF&", "secondary": "&H00FFFFFF&", "outline_col": "&H00000000&",
        "back_col": "&H00000000&", "border_style": 1, "outline": 5, "shadow": 2,
        "alignment": 5, "margin_v": 60, "mode": "premium"},
}

# Mode "fun" : couleurs alternées + emoji + pop animé
FUN_GREEN = "&H0000FF00&"
FUN_YELLOW = "&H0000FFFF&"
FUN_EMOJIS = ["🔥", "⌚", "💸", "👀", "✅", "🤑"]
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

def _premium_word_tag(role, disp_upper, dur_cs):
    """Tag ASS pour un mot dans une ligne premium V2 (minimaliste).

    - role "normal" : karaoké couleur via \\kf<cs> (sweep secondary -> primary
      durant la fenêtre du mot). Pas de scale, pas de bounce.
    - role "kw"     : couleur primary (accent) IMMÉDIATE pour faire ressortir
      le mot-clé, et \\kf<cs> conservé pour homogénéiser le timing/positionnement.

    `dur_cs` = durée du mot en centisecondes (au moins 1)."""
    if dur_cs < 1:
        dur_cs = 1
    if role == "kw":
        return "{\\kf%d\\1c%s}%s" % (dur_cs, EMPHASIS["accent"], disp_upper)
    # normal : pas de \1c -> hérite primary du style, qui sera atteint en fin de \kf
    return "{\\kf%d}%s" % (dur_cs, disp_upper)


def render_plan_subs(plan_subs, path, style=DEFAULT_STYLE):
    """Renderer purement exécutif — premium V2 minimaliste.

    Contrats visuels :
      - 1 Dialogue ASS par ligne du plan (pas de redessin par mot)
      - Mouvement subtil sur le BLOC ENTIER à l'apparition : \\fad(120,80) +
        \\t(0,180,\\fscx100\\fscy100) depuis 96%. Pas d'animation par mot.
      - Karaoké couleur via \\kf<cs> : balaye secondary -> primary mot par mot.
      - Keywords : \\1c<accent> persistant en plus du \\kf.

    plan_subs : [{start, end, words:[{disp, role, start, end}]}]
    """
    st = STYLES.get(style, STYLES[DEFAULT_STYLE])
    if st["mode"] != "premium":
        raise ValueError(f"render_plan_subs supporte uniquement les styles 'premium' (got mode={st['mode']!r})")
    lines = [HEADER.format(w=VIDEO["width"], h=VIDEO["height"], **st)]
    # Intro de ligne : fade-in 120ms (out 80ms) + léger pop 96% -> 100% sur 180ms.
    # 1 SEULE animation, sur le bloc entier, JAMAIS par mot.
    intro = "{\\fad(120,80)\\fscx96\\fscy96\\t(0,180,\\fscx100\\fscy100)}"
    for line in plan_subs:
        s, e = line["start"], line["end"]
        if e <= s: e = s + 0.08
        parts = []
        for w in line["words"]:
            disp = w["disp"].upper()
            dur_cs = int(round((w.get("end", s) - w.get("start", s)) * 100))
            parts.append(_premium_word_tag(w.get("role", "normal"), disp, dur_cs))
        text = intro + " ".join(parts)
        lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Default,,0,0,0,, " + text)
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path

def build_ass(tokens, n_sent, path, style=DEFAULT_STYLE):
    """Styles 'execution-only' (karaoke/fun/block...) : pas de logique métier
    (juste du rendu visuel). Le style 'premium' DOIT passer par render_plan_subs."""
    st = STYLES.get(style, STYLES[DEFAULT_STYLE])
    if st["mode"] == "premium":
        raise ValueError("Le style 'premium' nécessite un plan : utilise render_plan_subs(plan['subtitles'], ...)")
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
        elif st["mode"] == "fun":
            parts = []
            for j, wd in enumerate(chunk):
                col = FUN_GREEN if j % 2 == 0 else FUN_YELLOW
                parts.append("{\\c" + col + "}" + wd["disp"].upper())
            emo = FUN_EMOJIS[ci % len(FUN_EMOJIS)]
            pop = "{\\fad(40,0)\\fscx55\\fscy55\\t(0,150,\\fscx100\\fscy100)}"
            text = pop + " ".join(parts) + " " + emo
        else:  # block
            text = "{\\fad(80,0)}" + " ".join(w["disp"].upper() for w in chunk)
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,, " + text)
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path
