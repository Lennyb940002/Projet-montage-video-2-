from backend.config import VIDEO, SUBS

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{fs},{yellow},{white},&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,5,2,5,80,80,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def ass_time(sec):
    if sec < 0: sec = 0
    cs = int(round(sec * 100)); h = cs // 360000; cs %= 360000
    m = cs // 6000; cs %= 6000; s = cs // 100; c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

def build_ass(tokens, n_sent, path):
    mw = SUBS["maxwords"]
    lines = [HEADER.format(w=VIDEO["width"], h=VIDEO["height"], font=SUBS["font"],
                           fs=SUBS["size"], yellow=SUBS["yellow"], white=SUBS["white"])]
    chunks = []
    for si in range(n_sent):
        ws = [t for t in tokens if t["sent"] == si]
        for c in range(0, len(ws), mw):
            chunks.append(ws[c:c + mw])
    for ci, chunk in enumerate(chunks):
        start = chunk[0]["start"]
        end = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else chunk[-1]["end"] + 0.3
        if end <= start: end = start + 0.1
        n = len(chunk); parts = []
        for j in range(n):
            if j < n - 1:
                k = int(round((chunk[j + 1]["start"] - chunk[j]["start"]) * 100))
            else:
                k = int(round((chunk[j]["end"] - chunk[j]["start"]) * 100))
            if k < 1: k = 1
            parts.append("{\\k%d}%s" % (k, chunk[j]["disp"].upper()))
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,80,80,80,, " + " ".join(parts))
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path
