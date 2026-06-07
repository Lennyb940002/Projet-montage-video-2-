from dataclasses import dataclass
from faster_whisper import WhisperModel
from backend.config import WHISPER_MODEL

@dataclass
class Word:
    text: str
    start: float
    end: float
    prob: float

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model

def transcribe(audio_path):
    """Retourne (list[Word], duree). PAS d'initial_prompt (sinon Whisper
    ne renvoie qu'un segment - bug constaté)."""
    model = _get_model()
    segs, info = model.transcribe(audio_path, language="fr",
                                  beam_size=5, word_timestamps=True)
    words = []
    for s in segs:
        for w in (s.words or []):
            if w.word.strip():
                words.append(Word(w.word.strip(), w.start, w.end, w.probability))
    return words, info.duration
