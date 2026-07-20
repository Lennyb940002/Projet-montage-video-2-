# -*- coding: utf-8 -*-
"""Reel VOIX OFF complet, automatise : voix Puck (Gemini TTS) + clips KlingAI
en visuel (watermark retire, cadres 9:16, boucles pour couvrir la voix) -> une
video muxee (visuel + VO). Les sous-titres se posent APRES via make_subs.

Chaine complete (voir aussi run_vo_reel plus bas) :
  1) make_voice   -> vo.wav
  2) ce script    -> reel_novo.mp4 (visuel Kling + audio VO)
  3) transcribe   -> words.json
  4) make_subs    -> final.mp4 (sous-titres maison, garde la VO)

Usage direct :
  python deploy/make_vo_reel.py --subject ton_idee out_novo.mp4
  python deploy/make_vo_reel.py --text "..." out_novo.mp4
  python deploy/make_vo_reel.py --wav vo.wav out_novo.mp4    (VO deja generee)
"""
import os, sys, glob, tempfile, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

FF = E.FF
W, H, FPS = 1080, 1920, 30
CROP_WM = 130            # retire le watermark Kling (bas)

# Clips Kling montre par defaut (ordre = ordre a l'ecran, bouclé si besoin)
DEFAULT_CLIPS = [
    r"C:\Users\zbull\Downloads\Royal Oak Or rose.mp4",
    r"C:\Users\zbull\Downloads\Daytona Blue Saphire.mp4",
    r"C:\Users\zbull\Downloads\Fuck 95 Santos.mp4",
]


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _norm_clip(src, out):
    """Cadre un clip en 1080x1920, retire le watermark bas, 30fps, sans audio."""
    vf = (f"crop=iw:ih-{CROP_WM}:0:0,"
          f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"setsar=1,fps={FPS},format=yuv420p")
    _run([FF, "-y", "-i", src, "-vf", vf, "-an", *E._X264, out])


def build_visual(clips, dur, out, wd):
    """Concatene les clips normalises et boucle jusqu'a couvrir `dur` secondes."""
    norm = []
    for i, c in enumerate(clips):
        n = os.path.join(wd, f"n{i}.mp4"); _norm_clip(c, n); norm.append(n)
    lst = os.path.join(wd, "seq.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for n in norm:
            f.write(f"file '{n}'\n")
    seq = os.path.join(wd, "seq.mp4")
    _run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", seq])
    # boucle la sequence pour couvrir dur, puis coupe pile a dur
    _run([FF, "-y", "-stream_loop", "-1", "-i", seq, "-t", f"{dur:.2f}",
          "-an", *E._X264, out])


def mux_vo(visual, vo_wav, out):
    """Colle la VO sur le visuel (VO = audio), normalise le volume, faststart."""
    _run([FF, "-y", "-i", visual, "-i", vo_wav,
          "-map", "0:v:0", "-map", "1:a:0", "-shortest",
          "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
          *E._X264, "-c:a", "aac", "-b:a", "192k",
          "-movflags", "+faststart", out])


def make(vo_wav, out_novo, clips=None):
    clips = clips or DEFAULT_CLIPS
    clips = [c for c in clips if os.path.exists(c)]
    if not clips:
        raise SystemExit("[make_vo_reel] Aucun clip Kling trouve.")
    dur = E.probe_dur(vo_wav)
    wd = tempfile.mkdtemp(prefix="voreel_")
    visual = os.path.join(wd, "visual.mp4")
    build_visual(clips, dur + 0.1, visual, wd)
    mux_vo(visual, vo_wav, out_novo)
    print(f"[make_vo_reel] OK -> {out_novo}  ({dur:.1f}s, {len(clips)} clips Kling)")
    return out_novo


def main():
    args = sys.argv[1:]
    wd = tempfile.mkdtemp(prefix="voreel_src_")
    if args and args[0] == "--wav":
        vo = args[1]; out = args[2]
    elif args and args[0] == "--subject":
        from deploy import voice_scripts, make_voice
        sc = voice_scripts.get(args[1]); out = args[2]
        vo = os.path.join(wd, "vo.wav"); make_voice.synth(sc["vo"], vo)
    elif args and args[0] == "--text":
        from deploy import make_voice
        out = args[2]; vo = os.path.join(wd, "vo.wav"); make_voice.synth(args[1], vo)
    else:
        raise SystemExit('Usage: --subject NAME out.mp4 | --text "..." out.mp4 | --wav vo.wav out.mp4')
    make(vo, out)


if __name__ == "__main__":
    main()
