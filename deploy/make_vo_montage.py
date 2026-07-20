# -*- coding: utf-8 -*-
"""Gros montage VOIX OFF : colle plusieurs clips inventaire BOUT A BOUT (pleine
longueur) -> grosse video, avec voix Puck (Gemini TTS) des le debut + fond
musical leger sur toute la duree. Les sous-titres se posent APRES via make_subs.

Chaine :
  1) ce script -> montage_novo.mp4 (clips colles + VO + musique)
  2) transcribe -> words.json     (sur le wav VO)
  3) make_subs  -> FINAL.mp4      (sous-titres maison synchro, garde l'audio)

Usage :
  python deploy/make_vo_montage.py --subject ton_idee out_novo.mp4
  python deploy/make_vo_montage.py --wav vo.wav out_novo.mp4
Regle CLIPS / MUSIC ci-dessous (chemins locaux, a adapter selon le PC).
"""
import os, sys, tempfile, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E
from deploy import make_vo_reel as V

# Clips inventaire colles dans cet ordre (pleine longueur). Adapter les chemins.
CLIPS = [
    r"C:\Users\zbull\Downloads\kling_20260716_VIDEO_Vid_o_vert_1834_0.mp4",
    r"C:\Users\zbull\Downloads\kling_20260716_Image_to_Video_Vid_o_vert_1895_0.mp4",
    r"C:\Users\zbull\Downloads\Royal Oak Or rose.mp4",
    r"C:\Users\zbull\Downloads\Daytona Blue Saphire.mp4",
    r"C:\Users\zbull\Downloads\Fuck 95 Santos.mp4",
]
MUSIC = os.path.join(os.environ.get("RAFALE_ASSETS",
        r"C:\Users\zbull\Downloads\rafale_out\_assets"), "music", "08.wav")
MUSIC_VOL = 0.10          # fond musical leger sous la voix


def montage(vo_wav, out, clips=None, music=MUSIC):
    clips = [c for c in (clips or CLIPS) if os.path.exists(c)]
    if not clips:
        raise SystemExit("[make_vo_montage] Aucun clip trouve (adapte CLIPS).")
    wd = tempfile.mkdtemp(prefix="vomontage_")
    norm = []
    for i, c in enumerate(clips):
        n = os.path.join(wd, f"n{i}.mp4"); V._norm_clip(c, n); norm.append(n)
    lst = os.path.join(wd, "seq.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{n}'\n" for n in norm))
    big = os.path.join(wd, "big.mp4")
    subprocess.run([E.FF, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", big], check=True, stderr=subprocess.DEVNULL)
    bigdur = E.probe_dur(big)
    if music and os.path.exists(music):
        fc = (f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur={bigdur:.2f}[vo];"
              f"[2:a]volume={MUSIC_VOL}[mus];"
              f"[vo][mus]amix=inputs=2:duration=longest:dropout_transition=0[a]")
        ins = ["-i", big, "-i", vo_wav, "-stream_loop", "-1", "-i", music]
        amap = ["-filter_complex", fc, "-map", "0:v:0", "-map", "[a]"]
    else:  # VO seule
        fc = f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur={bigdur:.2f}[a]"
        ins = ["-i", big, "-i", vo_wav]
        amap = ["-filter_complex", fc, "-map", "0:v:0", "-map", "[a]"]
    subprocess.run([E.FF, "-y", *ins, *amap, "-t", f"{bigdur:.2f}", *E._X264,
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out],
                   check=True, stderr=subprocess.DEVNULL)
    print(f"[make_vo_montage] OK -> {out}  ({bigdur:.1f}s, {len(clips)} clips)")
    return out


def main():
    args = sys.argv[1:]
    wd = tempfile.mkdtemp(prefix="vomontage_src_")
    if args and args[0] == "--wav":
        vo, out = args[1], args[2]
    elif args and args[0] == "--subject":
        from deploy import voice_scripts, make_voice
        out = args[2]; vo = os.path.join(wd, "vo.wav")
        make_voice.synth(voice_scripts.get(args[1])["vo"], vo)
    else:
        raise SystemExit('Usage: --subject NAME out.mp4 | --wav vo.wav out.mp4')
    montage(vo, out)


if __name__ == "__main__":
    main()
