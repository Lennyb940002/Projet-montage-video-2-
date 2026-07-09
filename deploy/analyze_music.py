# -*- coding: utf-8 -*-
"""Analyse rythmique + DÉTECTION DE DROP.

Pour chaque piste :
  1. detect_drop() : trouve le plus gros "saut d'énergie" (loudness + basses) = drop
     ou changement d'ambiance, calé sur le beat le plus proche.
  2. ancre une fenêtre de WIN s pour que le drop tombe ~LEAD s après le début
     (build-up sous l'intro -> 1re montre PILE sur le drop).
  3. sort tempo, beats relatifs, et 'drop' (offset relatif) -> analysis.json.

Si aucun drop franc (confiance faible) -> 'drop'=null (le driver retombe sur
l'ancien heuristique "temps fort après le dernier mot").
"""
import os, json, sys
import numpy as np
import librosa

SCRATCH = os.environ.get("RAFALE_MUSIC_SRC", r"C:\Users\zbull\Downloads\rafale_out\_assets\music")
# Noms lisibles connus ; tout autre {key}.wav déposé est analysé avec key comme nom.
NAMES = {"01": "DAME UN GRR", "05": "Beyonce - Diva", "07": "Kelis - Milkshake",
         "20": "MI CORAZON (BAM BAM)", "21": "Montagem Miau",
         "11": "Rock That Body - BEP", "39": "APT - Rose & Bruno Mars"}
WIN = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0
LEAD = 5.5          # temps de build-up voulu avant le drop (place pour le hook)
HOP = 512
DROP_CONF_MIN = 0.045   # sous ce saut d'énergie -> pas de drop franc


def _norm(x):
    x = x - x.min()
    m = x.max()
    return x / m if m > 0 else x


def detect_drop(y, sr, min_t=0.0):
    """Retourne (drop_time_s, confiance) : le plus gros saut d'énergie soutenu,
    cherché seulement à partir de min_t s (pour garder le build-up de l'intro avant)."""
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    bass = S[freqs < 150].sum(axis=0)
    feat = 0.55 * _norm(rms) + 0.45 * _norm(bass)
    k = max(1, int(0.25 / (HOP / sr)))                 # lissage ~0,25 s
    feat = np.convolve(feat, np.ones(k) / k, mode="same")
    times = librosa.frames_to_time(np.arange(len(feat)), sr=sr, hop_length=HOP)
    n = len(feat)
    W = max(1, int(1.6 / (HOP / sr)))                  # fenêtre avant/après
    csum = np.cumsum(np.insert(feat, 0, 0))
    step = np.full(n, -1.0)
    idx = np.arange(W, n - W)
    after = (csum[idx + W] - csum[idx]) / W
    before = (csum[idx] - csum[idx - W]) / W
    step[idx] = (after - before) * (0.4 + 0.6 * after)  # favorise saut vers haute énergie
    # ignore avant min_t (place pour l'intro) et la toute fin
    lo = int(max(2.0, min_t) / (HOP / sr)); hi = n - int(2.0 / (HOP / sr))
    step[:lo] = -1; step[hi:] = -1
    di = int(np.argmax(step))
    a = (csum[min(n, di + W)] - csum[di]) / W
    b = (csum[di] - csum[max(0, di - W)]) / W
    conf = float(a - b)
    # raffinage : viser le PIC D'IMPACT (instant le plus fort dans la seconde qui
    # suit la montée) et non le début de la montée -> la 1re montre tombe sur la frappe.
    look = int(1.0 / (HOP / sr))
    seg = feat[di:min(n, di + look)]
    if seg.size:
        di += int(np.argmax(seg))
    return float(times[di]), conf


def analyze(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur = len(y) / sr
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP, units='time')
    tempo = float(np.atleast_1d(tempo)[0])

    drop_t, conf = detect_drop(y, sr, LEAD)
    has_drop = conf >= DROP_CONF_MIN
    if beats.size:                                     # cale le drop sur le beat le plus proche
        drop_t = float(beats[np.argmin(np.abs(beats - drop_t))])

    if has_drop:
        win_start = max(0.0, drop_t - LEAD)
    else:
        # fallback : fenêtre la plus percussive
        t_env = librosa.frames_to_time(np.arange(len(onset)), sr=sr, hop_length=HOP)
        wf = int(WIN / (HOP / sr))
        if wf < len(onset):
            cs = np.cumsum(np.insert(onset, 0, 0))
            means = (cs[wf:] - cs[:-wf]) / wf
            pen = np.where(t_env[:len(means)] < 8.0, 0.85, 1.0)
            win_start = float(t_env[int(np.argmax(means * pen))])
        else:
            win_start = 0.0
    if beats.size:                                     # début de fenêtre sur un beat
        win_start = float(beats[np.argmin(np.abs(beats - win_start))])
    win_start = min(win_start, max(0.0, dur - WIN))
    win_end = win_start + WIN

    seg_beats = [round(float(b - win_start), 3) for b in beats if win_start <= b < win_end]
    drop_rel = None
    if has_drop:
        d = drop_t - win_start
        if seg_beats:                                  # cale sur un beat du segment
            d = min(seg_beats, key=lambda b: abs(b - d))
        drop_rel = round(float(d), 3)

    return dict(tempo=round(tempo, 1), win_start=round(win_start, 3), win_dur=WIN,
                n_beats=len(seg_beats), beats=seg_beats, drop=drop_rel,
                drop_conf=round(conf, 4), full_dur=round(dur, 1))


def main():
    import glob
    res = {}
    keys = sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(SCRATCH, "*.wav")))
    for k in keys:
        p = os.path.join(SCRATCH, f"{k}.wav")
        name = NAMES.get(k, k)
        a = analyze(p); a["name"] = name; a["key"] = k
        res[k] = a
        d = f"{a['drop']}s (conf {a['drop_conf']})" if a["drop"] else f"AUCUN (conf {a['drop_conf']})"
        print(f"{k} {name:22s} tempo={a['tempo']:6.1f} start={a['win_start']:7.1f}s  drop-> {d}")
    json.dump(res, open(os.path.join(SCRATCH, "analysis.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("analysis.json écrit (WIN=%.0fs, LEAD=%.1fs)" % (WIN, LEAD))


if __name__ == "__main__":
    main()
