import re, difflib

def norm(w):
    return re.sub(r"[^0-9a-zàâäçéèêëîïôöùûüœæ]", "", w.lower())

def _clean(s):
    for ch in "«»“”\"":
        s = s.replace(ch, "")
    return s.strip()

def tokenize(text):
    """-> (tokens, n_sent). token = {disp, norm, sent, start, end}.
    Les symboles isolés (%, €, …) sont fusionnés au mot précédent."""
    sents = [p.strip() for p in re.split(r"(?<=[.!?…:])\s+", text.replace("\n", " ")) if p.strip()]
    tokens = []
    for si, sent in enumerate(sents):
        for raw in sent.split():
            n = norm(raw); disp = _clean(raw)
            if n == "":
                if disp and tokens:
                    tokens[-1]["disp"] += " " + disp
                continue
            tokens.append({"disp": disp, "norm": n, "sent": si,
                           "start": None, "end": None})
    return tokens, len(sents)

def align(tokens, words):
    """Transfère les timings des mots whisper sur les tokens du texte."""
    a = [t["norm"] for t in tokens]
    b = [norm(w.text) for w in words]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                tokens[i1 + k]["start"] = words[j1 + k].start
                tokens[i1 + k]["end"] = words[j1 + k].end
        elif tag == "replace" and j2 > j1:
            s = words[j1].start; e = words[j2 - 1].end; cnt = i2 - i1
            step = (e - s) / cnt if cnt else 0
            for k in range(cnt):
                tokens[i1 + k]["start"] = s + step * k
                tokens[i1 + k]["end"] = s + step * (k + 1)
    # interpolation des trous
    n = len(tokens); i = 0
    while i < n:
        if tokens[i]["start"] is None:
            j = i
            while j < n and tokens[j]["start"] is None:
                j += 1
            prev_e = tokens[i - 1]["end"] if i > 0 and tokens[i - 1]["end"] is not None else 0.0
            next_s = tokens[j]["start"] if j < n and tokens[j]["start"] is not None else prev_e + 0.4 * (j - i)
            cnt = j - i; step = (next_s - prev_e) / (cnt + 1)
            for k in range(cnt):
                tokens[i + k]["start"] = prev_e + step * (k + 1)
                tokens[i + k]["end"] = prev_e + step * (k + 2)
            i = j
        else:
            i += 1
    # monotonie
    last = 0.0
    for t in tokens:
        if t["start"] < last: t["start"] = last
        if t["end"] <= t["start"]: t["end"] = t["start"] + 0.08
        last = t["end"]
    return tokens
