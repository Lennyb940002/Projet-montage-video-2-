"""music_engine — moteur d'exécution musique. Purement exécutif.

Transforme un `plan['music']` en fragment ffmpeg que `montage.render` intègre
dans son graphe audio.

Contrat d'architecture :
  - aucune logique métier ici (sélection, scoring, ducking strategy = Director)
  - itère sur beds[] et accents[] dès la V1 (anti-régression : préparer
    intro calme + montée + CTA final sans réécrire le moteur)
  - V1 : 1 bed maximum côté Director ; 0 accent ; le moteur supporte déjà N

API publique
------------
build(plan_music, voice_label, base_input_idx) -> dict
    plan_music : structure plan["music"] (ou None)
    voice_label : nom du label ffmpeg de la voix (ex "vmix")
    base_input_idx : index du PREMIER input ffmpeg ajouté

Renvoie
-------
{
    "extra_inputs":     [<tracks à ajouter en -i>],
    "filter_str":       "...;...",   # à concaténer dans filter_complex
    "out_label":        "<label de sortie audio>",
    "beds_processed":   int,
    "accents_processed":int,
}

No-op : si plan_music est None ou beds vide -> out_label = voice_label (inchangé).
"""


def _format_db(value):
    """volume=NN.NdB ou volume=NNdB selon la valeur (lisible dans le filter)."""
    if value == int(value):
        return f"{int(value)}"
    return f"{value:.1f}"


def _bed_chain(bed, input_idx, bi):
    """Construit la chaîne d'un seul bed jusqu'à son label de ducking ducked
    label.

    Renvoie (parts_list, ducked_label, voice_label_in, voice_label_out).
    parts_list : liste de fragments ffmpeg à joindre par ';'.
    ducked_label : label final du bed après ducking (ex "[m0]").

    NB : voice est dupliquée (asplit) à chaque bed pour pouvoir servir de
    sidechain ET continuer à être traitée par les beds suivants.
    """
    parts = []
    in_label = f"[{input_idx}:a]"
    trim_start = bed.get("trim_start", 0.0)
    dur = bed["duration"]
    base_gain = _format_db(bed["base_gain_dB"])
    fade_in_s = bed.get("fade_in_ms", 0) / 1000.0
    fade_out_s = bed.get("fade_out_ms", 0) / 1000.0

    # 1) trim + reset PTS + reformatage stéréo float
    bed_chain = (f"{in_label}atrim=start={trim_start:.3f}:end={trim_start + dur:.3f},"
                 f"asetpts=N/SR/TB,"
                 f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"volume={base_gain}dB")
    # 2) fades
    if fade_in_s > 0:
        bed_chain += f",afade=t=in:st=0:d={fade_in_s:.3f}"
    if fade_out_s > 0:
        bed_chain += f",afade=t=out:st={dur - fade_out_s:.3f}:d={fade_out_s:.3f}"
    # 3) gaps : volume=0 sur les intervalles + fades aux bords du gap
    for g in bed.get("gaps", []):
        bed_chain += (f",volume=0:enable='between(t,"
                      f"{g['start']:.3f},{g['end']:.3f})'")
    raw_label = f"[mraw{bi}]"
    parts.append(bed_chain + raw_label)

    return parts, raw_label


def build(plan_music, voice_label, base_input_idx):
    """Convertit plan['music'] en (extra_inputs, filter_str, out_label).
    No-op si plan_music None ou beds vide.
    """
    if not plan_music:
        return {"extra_inputs": [], "filter_str": "",
                "out_label": voice_label,
                "beds_processed": 0, "accents_processed": 0}

    beds = plan_music.get("beds") or []
    accents = plan_music.get("accents") or []

    if not beds:
        return {"extra_inputs": [], "filter_str": "",
                "out_label": voice_label,
                "beds_processed": 0, "accents_processed": 0}

    inputs = []
    fc_parts = []
    current_voice = voice_label
    last_ducked = None
    idx = base_input_idx

    # --- Boucle beds (garde-fou : prête pour multi-beds futurs) ---
    for bi, bed in enumerate(beds):
        inputs.append(bed["track"])
        bed_parts, raw_label = _bed_chain(bed, idx, bi)
        fc_parts.extend(bed_parts)

        # Duplique la voix : une copie sert de sidechain, l'autre continue
        # vers le bed suivant (ou le mix final).
        side_label = f"[vside{bi}]"
        keep_label = f"[vkeep{bi}]"
        fc_parts.append(f"[{current_voice}]asplit=2{side_label}{keep_label}")

        d = bed["duck"]
        ducked_label = f"[m{bi}]"
        fc_parts.append(
            f"{raw_label}{side_label}sidechaincompress="
            f"threshold={d['threshold_dB']}dB:"
            f"ratio={d['ratio']}:"
            f"attack={d['attack_ms']}:"
            f"release={d['release_ms']}"
            f"{ducked_label}"
        )

        # La voix conservée devient la voix d'entrée du bed suivant
        current_voice = f"vkeep{bi}"
        last_ducked = f"m{bi}"
        idx += 1

    # --- Boucle accents (V1 toujours vide, mais le moteur l'exécute déjà) ---
    accents_processed = 0
    for ai, accent in enumerate(accents):
        # V1 : si un accent est posé par erreur, on le traite comme un
        # impact court mixé. Reste minimal et défensif.
        inputs.append(accent["track"])
        a_in = f"[{idx}:a]"
        a_lab = f"[acc{ai}]"
        gain = _format_db(accent.get("gain_dB", -10.0))
        fc_parts.append(f"{a_in}volume={gain}dB,"
                        f"aformat=sample_fmts=fltp:channel_layouts=stereo{a_lab}")
        accents_processed += 1
        idx += 1
        # Mixer l'accent dans le dernier ducked
        new_last = f"acc{ai}_mixed"
        fc_parts.append(f"[{last_ducked}]{a_lab}amix=inputs=2:normalize=0[{new_last}]")
        last_ducked = new_last

    # --- Mix final voix + dernière musique ---
    fc_parts.append(
        f"[{current_voice}][{last_ducked}]"
        f"amix=inputs=2:normalize=0:duration=longest[mout]"
    )

    return {
        "extra_inputs": inputs,
        "filter_str": ";".join(fc_parts),
        "out_label": "mout",
        "beds_processed": len(beds),
        "accents_processed": accents_processed,
    }
