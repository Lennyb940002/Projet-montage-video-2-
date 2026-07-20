# -*- coding: utf-8 -*-
"""Vidéo VOIX OFF complète, bout-en-bout, orientée CONVERSION :
  script (voice_scripts) -> voix Gemini TTS -> visuel (clips banque, 9:16) ->
  transcription -> sous-titres maison -> mix musique de fond -> final.mp4

Usage :
  python deploy/make_full_video.py <script_name> out.mp4
  python deploy/make_full_video.py --text "..." out.mp4
Réutilise : make_voice, make_vo_reel, backend.pipeline.transcribe, make_subs, rafale_engine.
"""
import os
import sys
import glob
import json
import random
import tempfile
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# La bonne clé est dans ~/.automontage/gemini_key.txt ; on neutralise une éventuelle
# variable d'env cassée (clés AQ. défectueuses) pour forcer l'usage du fichier.
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("GOOGLE_API_KEY", None)

from deploy import make_voice, make_vo_reel, voice_scripts
from deploy import rafale_engine as E
from backend.pipeline import transcribe
from backend.config import SILENT

DEPLOY = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = SILENT["clips_dir"]
MUSIC_DIR = SILENT["music_dir"]
MUSIC_GAIN = 0.13          # musique de fond bien sous la voix


def pick_clips(rng, n=4):
    """n clips variés de la banque (modèles différents en priorité)."""
    by_model = {}
    for p in glob.glob(os.path.join(CLIPS_DIR, "*", "*.mp4")):
        by_model.setdefault(os.path.basename(os.path.dirname(p)), []).append(p)
    models = list(by_model); rng.shuffle(models)
    clips = [rng.choice(by_model[m]) for m in models[:n]]
    while len(clips) < n and by_model:                 # complète si peu de modèles
        clips.append(rng.choice(rng.choice(list(by_model.values()))))
    return clips


def pick_music(rng):
    songs = glob.glob(os.path.join(MUSIC_DIR, "**", "*.mp3"), recursive=True)
    return rng.choice(songs) if songs else None


def _mix_music(reel_voice, music, out):
    """Mixe la musique de fond SOUS la voix (voix intacte), loop + fade out."""
    dur = E.probe_dur(reel_voice)
    fo = max(0.0, dur - 0.6)
    fc = (f"[1:a]volume={MUSIC_GAIN},afade=t=out:st={fo:.2f}:d=0.6[m];"
          f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]")
    E.run([E.FF, "-y", "-i", reel_voice, "-stream_loop", "-1", "-i", music,
           "-filter_complex", fc, "-map", "0:v:0", "-map", "[a]", "-t", f"{dur:.2f}",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", out])


def _trim_silences(win, wout, keep=0.20, thr="-38dB"):
    """Réduit les longs blancs entre phrases (garde ~keep s de souffle)."""
    E.run([E.FF, "-y", "-i", win, "-af",
           f"silenceremove=stop_periods=-1:stop_duration={keep}:stop_threshold={thr}", wout])
    return wout


def make_full(vo_text, out, seed=None, cta=None, voice=None):
    rng = random.Random(seed)
    wd = tempfile.mkdtemp(prefix="fullvid_")
    # 1) voix (+ retrait des blancs trop longs)
    vo_raw = os.path.join(wd, "vo_raw.wav"); make_voice.synth(vo_text, vo_raw, voice=voice)
    vo = os.path.join(wd, "vo.wav"); _trim_silences(vo_raw, vo)
    # 2) visuel (clips banque) + voix muxée
    reel_novo = os.path.join(wd, "reel_novo.mp4")
    make_vo_reel.make(vo, reel_novo, clips=pick_clips(rng))
    # 3) transcription mot-à-mot (normalise Word/objets -> dicts)
    words_raw, _ = transcribe.transcribe(vo)
    def _wd(w):
        if isinstance(w, dict):
            return {"word": w["word"], "start": w["start"], "end": w["end"]}
        return {"word": getattr(w, "text", None) or getattr(w, "word", ""),
                "start": w.start, "end": w.end}
    words = [_wd(w) for w in words_raw]
    wjson = os.path.join(wd, "words.json")
    json.dump(words, open(wjson, "w", encoding="utf-8"), ensure_ascii=False)
    # 4) sous-titres maison
    reel_subs = os.path.join(wd, "reel_subs.mp4")
    subprocess.run([sys.executable, os.path.join(DEPLOY, "make_subs.py"),
                    reel_novo, wjson, reel_subs], check=True)
    # 5) mix musique de fond
    music = pick_music(rng)
    if music:
        _mix_music(reel_subs, music, out)
    else:
        os.replace(reel_subs, out)
    print(f"\n[make_full_video] OK -> {out}  ({E.probe_dur(out):.1f}s)")
    return out


def main():
    args = sys.argv[1:]
    voice = None
    if "--voice" in args:
        i = args.index("--voice"); voice = args[i + 1]; del args[i:i + 2]
    if len(args) >= 2 and args[0] == "--text":
        make_full(args[1], args[2], voice=voice)
    elif len(args) >= 2:
        sc = voice_scripts.get(args[0])
        make_full(sc["vo"], args[1], cta=sc.get("cta"), voice=voice)
    else:
        raise SystemExit('Usage: make_full_video.py [--voice NAME] <script_name> out.mp4 | --text "..." out.mp4')


if __name__ == "__main__":
    main()
