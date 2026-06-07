import os, glob, random
from backend import ffmpeg
from backend.config import VIDEO, DEFAULT_CLIPS_DIR

def list_clips(clips_dir=DEFAULT_CLIPS_DIR):
    """Clips .mp4 dédoublonnés par taille de fichier."""
    seen = {}; clips = []
    for c in sorted(glob.glob(os.path.join(clips_dir, "*.mp4"))):
        sz = os.path.getsize(c)
        if sz in seen: continue
        seen[sz] = c; clips.append(c)
    return clips

def sentence_ranges(tokens, n_sent, duration):
    starts = []
    for si in range(n_sent):
        ws = [t for t in tokens if t["sent"] == si]
        starts.append(ws[0]["start"] if ws else (starts[-1] if starts else 0.0))
    if starts: starts[0] = 0.0
    ranges = []
    for si in range(n_sent):
        s = starts[si]; e = starts[si + 1] if si + 1 < n_sent else duration
        ranges.append((s, max(e, s + 0.3)))
    return ranges or [(0.0, duration)]

def apply_boost_cuts(ranges, hook_dur, hook_cut):
    """Redécoupe la portion [0, hook_dur] en tranches de hook_cut (cuts rapides)."""
    out = []
    for s, e in ranges:
        if s >= hook_dur:
            out.append((s, e)); continue
        hook_end = min(e, hook_dur)
        t = s
        while t < hook_end - 1e-3:
            nt = min(t + hook_cut, hook_end)
            out.append((t, nt)); t = nt
        if e > hook_dur:
            out.append((hook_dur, e))
    return out

def _pick_clips(ranges, clips):
    durs = {c: ffmpeg.probe_duration(c) for c in clips}
    avail = clips[:]; random.shuffle(avail); chosen = []
    for (s, e) in ranges:
        L = e - s; pick = None
        for n, c in enumerate(avail):
            if durs[c] >= L + 0.15:
                pick = avail.pop(n); break
        if pick is not None:
            off = random.uniform(0, max(0.0, durs[pick] - L))
            chosen.append((pick, off, L, False))
        elif avail:
            c = max(avail, key=lambda x: durs[x]); avail.remove(c)
            chosen.append((c, 0.0, L, True))
        else:
            avail = clips[:]; random.shuffle(avail); c = avail.pop(0)
            chosen.append((c, 0.0, L, durs[c] < L + 0.15))
    return chosen

def render(audio_path, ass_path, ranges, out_path, clips_dir=DEFAULT_CLIPS_DIR,
           boost=False, sfx_events=None, sfx_dir=None):
    """ranges = plages de clips FINALES (le redécoupage hook est fait par l'appelant).
    sfx_events = plan SFX [{time,category,gain_dB,fade_in_ms,fade_out_ms}] (catégories
    résolues ici en fichiers via sfx.pick)."""
    from backend.config import BOOST, SFX_DIR
    from backend.pipeline import sfx as sfxmod
    sfx_dir = sfx_dir or SFX_DIR
    clips = list_clips(clips_dir)
    if not clips:
        raise RuntimeError(f"Aucun clip dans {clips_dir}")
    chosen = _pick_clips(ranges, clips)
    W, H, FPS, ZOOM = VIDEO["width"], VIDEO["height"], VIDEO["fps"], VIDEO["zoom"]

    cmd = [ffmpeg.FFMPEG, "-y"]
    for (c, off, L, loop) in chosen:
        if loop: cmd += ["-stream_loop", "-1", "-t", f"{L:.3f}", "-i", c]
        else: cmd += ["-ss", f"{off:.3f}", "-t", f"{L:.3f}", "-i", c]
    cmd += ["-i", audio_path]
    Ncl = len(chosen)

    # 1 son cohérent par catégorie (réutilisé) + attaque calée pour impacts/drops
    cat_file = {}; cat_onset = {}
    resolved = []
    if sfx_events:
        for e in sfx_events:
            c = e["category"]
            if c not in cat_file:
                cf = sfxmod.choose(c, sfx_dir)
                cat_file[c] = cf
                cat_onset[c] = (sfxmod.onset(cf) if (cf and c in ("Impacts", "Drops")) else 0.0)
            if cat_file[c]:
                resolved.append((e, cat_file[c], cat_onset[c]))
    for (_e, f, _on) in resolved:
        cmd += ["-i", f]

    # vidéo
    fc = []
    for k in range(Ncl):
        # zoom CONSTANT (pas de zoompan -> aucune image figée + rapide).
        # 1er clip en mode boost = zoom plus serré (punch).
        zf = BOOST["punch_zoom"] if (boost and k == 0) else ZOOM
        cw, ch = int(W * zf), int(H * zf)
        fc.append(f"[{k}:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H},setsar=1,fps={FPS},format=yuv420p[v{k}]")
    fc.append("".join(f"[v{k}]" for k in range(Ncl)) + f"concat=n={Ncl}:v=1:a=0[cv]")
    ass_dir = os.path.dirname(os.path.abspath(ass_path))
    ass_name = os.path.basename(ass_path)
    if boost:
        fc.append(f"[cv]drawbox=x=0:y=0:w=iw:h=ih:color=white@1:t=fill:"
                  f"enable='lt(t,{BOOST['flash']})'[cf];[cf]ass={ass_name}[vout]")
    else:
        fc.append(f"[cv]ass={ass_name}[vout]")

    # audio : voix + SFX (volume/fondus par évènement)
    if resolved:
        fc.append(f"[{Ncl}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[av]")
        for i, (e, f, on) in enumerate(resolved):
            sdur = ffmpeg.probe_duration(f)
            eff = max(0.1, sdur - on)          # durée après retrait du lead-in
            fin = e.get("fade_in_ms", 0) / 1000.0
            fout = e.get("fade_out_ms", 0) / 1000.0
            d = int(round(e["time"] * 1000))
            parts = []
            if on > 0.01:
                parts.append(f"atrim=start={on:.3f}")
                parts.append("asetpts=N/SR/TB")
            parts.append(f"volume={e['gain_dB']}dB")
            if fin > 0:
                parts.append(f"afade=t=in:st=0:d={fin:.3f}")
            if fout > 0 and eff > fout:
                parts.append(f"afade=t=out:st={eff - fout:.3f}:d={fout:.3f}")
            parts.append(f"adelay={d}|{d}")
            parts.append("aformat=sample_fmts=fltp:channel_layouts=stereo")
            fc.append(f"[{Ncl + 1 + i}:a]" + ",".join(parts) + f"[se{i}]")
        mix = "[av]" + "".join(f"[se{i}]" for i in range(len(resolved)))
        fc.append(f"{mix}amix=inputs={len(resolved) + 1}:normalize=0:duration=first[aout]")
        amap = "[aout]"
    else:
        amap = f"{Ncl}:a"

    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", amap,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-r", str(FPS), "-shortest",
            "-movflags", "+faststart", "-map_metadata", "-1", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=ass_dir)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"Rendu échoué: {r.stderr[-400:]}")
    return out_path
