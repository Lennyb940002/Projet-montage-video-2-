# AutoMontage (Phase 1 / MVP)

App locale de montage vidéo automatisé : audio (voix IA) → vidéo 9:16 sous-titrée.

## Prérequis
- Python 3.13 + `pip install -r backend/requirements.txt`
- ffmpeg (build Gyan, chemin dans `backend/config.py`)
- Node.js LTS

## Lancer
```
cd frontend
npm install
npm start
```
La fenêtre s'ouvre et lance automatiquement le backend Python en sidecar.

## Workflow
Glisser un audio → transcription + silences auto → corriger le texte → Générer l'aperçu → Exporter.

## Tests
`pytest backend/tests/ -v`

## Réglages
Voir `backend/config.py` (modèle Whisper, format, zoom, silences, banque de clips).

## Architecture (Phase 1)
- `backend/pipeline/` : transcribe · audio_clean · align · subtitles · montage
- `backend/service.py` : orchestration (load_audio, make_video)
- `backend/server.py` : API FastAPI (`/load`, `/preview`, `/export`)
- `frontend/` : Electron (main.js spawn le backend, renderer.js = UI)

## Phases suivantes (non incluses)
2 — détection 🟡 reprises / 🔴 mots peu sûrs · 3 — éditeur audio (forme d'onde) · 4 — finitions (banque de clips, réglages, annuler/refaire).
