# -*- coding: utf-8 -*-
"""Voix off maison via Google AI Studio (Gemini TTS). REGLAGES FIGES (memes a
chaque fois) pour une identite de marque constante. Sort un .wav mono 24k.

Cle API (jamais dans le chat) : variable d'env GEMINI_API_KEY, sinon fichier
local  ~/.automontage/gemini_key.txt  (une ligne = la cle).

Usage :
    python deploy/make_voice.py "Le texte a dire" sortie.wav
    python deploy/make_voice.py --file script.txt sortie.wav
Importable :
    from deploy.make_voice import synth ; synth("bonjour", "out.wav")
"""
import os, sys, struct, mimetypes
from google import genai
from google.genai import types

# ---- REGLAGES FIGES (ne pas changer sans raison) ---------------------------
MODEL = "gemini-3.1-flash-tts-preview"
VOICE = "Charon"          # VOIX OFFICIELLE validee 2026-07-20 par Lenny (masculine posee, credible). Ne pas changer.
TEMPERATURE = 1.0
# Profil de jeu fige (director's notes) lu avant le transcript -> identite constante.
STYLE = (
    "# PROFIL VOIX\n"
    "Voix masculine francaise de France, jeune adulte 25-30 ans. Naturelle, "
    "chaleureuse, credible : un createur de contenu qui parle direct a sa "
    "communaute sur Instagram/TikTok. Surtout PAS presentateur radio, "
    "documentaire, ni pub tele classique.\n"
    "# JEU\n"
    "Accent neutre France. Style naturel, conversationnel, confiant, engageant. "
    "Debit dynamique mais clair. Ton chaleureux, premium, legerement enthousiaste. "
    "Respirations subtiles entre les phrases. Courtes pauses apres les infos "
    "importantes. Articulation claire mais jamais robotique. Emotion : commence "
    "curieux, deviens plus enthousiaste sur la presentation produit, finis confiant.\n"
    "# CONSIGNE\n"
    "Prononce le transcript EXACTEMENT comme ecrit : n'ajoute, ne retire, ne "
    "reformule aucun mot. Les indications entre crochets (ex : [confident], "
    "[short pause]) sont des directions de jeu : NE LES PRONONCE PAS, applique-les.\n"
    "# TRANSCRIPT")
# ---------------------------------------------------------------------------


def _api_key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if k:
        return k.strip()
    p = os.path.expanduser("~/.automontage/gemini_key.txt")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    raise SystemExit(
        "[make_voice] Cle Gemini absente. Mets-la dans la variable d'env "
        "GEMINI_API_KEY, ou dans le fichier  ~/.automontage/gemini_key.txt")


def _parse_mime(mime_type: str):
    bits, rate = 16, 24000
    for part in mime_type.split(";"):
        part = part.strip()
        if part.lower().startswith("rate="):
            try: rate = int(part.split("=", 1)[1])
            except Exception: pass
        elif part.startswith("audio/L"):
            try: bits = int(part.split("L", 1)[1])
            except Exception: pass
    return bits, rate


def _wav_header(data_size, bits, rate, channels=1):
    bps = bits // 8
    block = channels * bps
    byte_rate = rate * block
    return struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + data_size, b"WAVE",
                       b"fmt ", 16, 1, channels, rate, byte_rate, block, bits,
                       b"data", data_size)


def synth(text, out_path, voice=None):
    """Genere la voix off de `text` et ecrit un WAV dans out_path. Retourne out_path.
    voice : override la voix (pour tester) ; None = VOICE de marque."""
    voice = voice or VOICE
    client = genai.Client(api_key=_api_key())
    contents = [types.Content(role="user",
                parts=[types.Part.from_text(text=f"{STYLE}\n{text.strip()}")])]
    cfg = types.GenerateContentConfig(
        temperature=TEMPERATURE,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
    )
    pcm = bytearray(); bits = rate = None
    for chunk in client.models.generate_content_stream(model=MODEL, contents=contents, config=cfg):
        if not chunk.candidates:
            continue
        parts = chunk.candidates[0].content.parts if chunk.candidates[0].content else None
        if not parts:
            continue
        idata = parts[0].inline_data
        if idata and idata.data:
            ext = mimetypes.guess_extension(idata.mime_type or "")
            if ext in (None, ".wav") or (idata.mime_type or "").startswith("audio/L"):
                if bits is None:
                    bits, rate = _parse_mime(idata.mime_type or "audio/L16;rate=24000")
                pcm += idata.data
            else:  # deja un container -> ecrit tel quel
                open(out_path, "wb").write(idata.data)
                print(f"[make_voice] OK (container) -> {out_path}")
                return out_path
    if not pcm:
        raise SystemExit("[make_voice] Aucune donnee audio recue (modele/quotas ?).")
    with open(out_path, "wb") as f:
        f.write(_wav_header(len(pcm), bits, rate)); f.write(pcm)
    dur = len(pcm) / (rate * (bits // 8))
    print(f"[make_voice] OK -> {out_path}  ({dur:.1f}s, voix={voice})")
    return out_path


def main():
    args = sys.argv[1:]
    voice = None
    if "--voice" in args:
        i = args.index("--voice"); voice = args[i + 1]; del args[i:i + 2]
    if len(args) >= 3 and args[0] == "--file":
        text = open(args[1], encoding="utf-8").read()
        out = args[2]
    elif len(args) >= 2:
        text, out = args[0], args[1]
    else:
        raise SystemExit('Usage: python deploy/make_voice.py [--voice NAME] "texte" out.wav  |  --file script.txt out.wav')
    synth(text, out, voice=voice)


if __name__ == "__main__":
    main()
