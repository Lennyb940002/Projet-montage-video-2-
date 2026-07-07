# -*- coding: utf-8 -*-
"""Analyse rythmique : pour chaque piste, trouve la fenêtre de WIN s la plus
percussive, cale son début sur un BEAT FORT (pic d'onset = probable 1er temps),
et sort les temps de beats relatifs. Écrit analysis.json + ranked.json.
"""
import os, json, sys
import numpy as np
import librosa

# Dossier des wav sources + sortie analysis.json (surchargable par variable d'env).
SCRATCH = os.environ.get("RAFALE_MUSIC_SRC", r"C:\Users\zbull\Downloads\rafale_out\_assets\music")
NAMES = {"01": "DAME UN GRR", "05": "Beyonce - Diva", "07": "Kelis - Milkshake",
         "20": "MI CORAZON (BAM BAM)", "21": "Montagem Miau"}
WIN = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0


def analyze(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur = len(y) / sr
    hop = 512
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    t_env = librosa.frames_to_time(np.arange(len(onset)), sr=sr, hop_length=hop)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop, units='time')
    tempo = float(np.atleast_1d(tempo)[0])
    win_frames = int(WIN / (hop / sr))
    if win_frames >= len(onset):
        start_f = 0
    else:
        csum = np.cumsum(np.insert(onset, 0, 0))
        means = (csum[win_frames:] - csum[:-win_frames]) / win_frames
        penalty = np.where(t_env[:len(means)] < 8.0, 0.85, 1.0)
        start_f = int(np.argmax(means * penalty))
    win_start = float(t_env[start_f])
    # snap sur un BEAT FORT proche
    if len(beats):
        near = [b for b in beats if abs(b - win_start) <= 1.3]
        if not near:
            near = [float(beats[np.argmin(np.abs(beats - win_start))])]
        strengths = [onset[np.argmin(np.abs(t_env - b))] for b in near]
        win_start = float(near[int(np.argmax(strengths))])
    win_start = min(win_start, max(0.0, dur - WIN))
    win_end = win_start + WIN
    seg_beats = [round(float(b - win_start), 3) for b in beats if win_start <= b < win_end]
    mask = (t_env >= win_start) & (t_env < win_end)
    onset_mean = float(onset[mask].mean()) if mask.any() else 0.0
    ibi = np.diff([b for b in beats if win_start <= b < win_end]) if len(seg_beats) > 2 else np.array([0.5])
    regular = 1.0 / (1.0 + float(np.std(ibi))) if len(ibi) else 0.5
    score = onset_mean * (0.6 + 0.4 * regular)
    return dict(tempo=round(tempo, 1), win_start=round(win_start, 3), win_dur=WIN,
                n_beats=len(seg_beats), beats=seg_beats, onset_mean=round(onset_mean, 3),
                regular=round(regular, 3), score=round(score, 3), full_dur=round(dur, 1))


def main():
    res = {}
    for k, name in NAMES.items():
        a = analyze(os.path.join(SCRATCH, f"{k}.wav"))
        a["name"] = name; a["key"] = k
        res[k] = a
        print(f"{k} {name:24s} tempo={a['tempo']:6.1f} start={a['win_start']:6.1f}s "
              f"beats={a['n_beats']:3d} score={a['score']:.3f}")
    ranked = sorted(res.values(), key=lambda a: -a["score"])
    json.dump(res, open(os.path.join(SCRATCH, "analysis.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump([a['key'] for a in ranked], open(os.path.join(SCRATCH, "ranked.json"), "w"))
    print("analysis.json écrit (WIN=%.0fs)" % WIN)


if __name__ == "__main__":
    main()
