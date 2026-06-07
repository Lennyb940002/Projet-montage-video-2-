import os, uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend import service
from backend.pipeline import subtitles
from backend.config import WORKDIR

app = FastAPI(title="AutoMontage")

# L'UI Electron (page file://) appelle cette API locale -> autoriser toutes origines.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

class LoadReq(BaseModel):
    audio_path: str

class VideoReq(BaseModel):
    clean_path: str
    text: str
    out_path: str | None = None
    style: str = "karaoke_yellow"

class CutReq(BaseModel):
    clean_path: str
    ranges: list[tuple[float, float]]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/styles")
def styles():
    return subtitles.list_styles()

@app.post("/load")
def load(req: LoadReq):
    return service.load_audio(req.audio_path)

@app.post("/cut")
def cut(req: CutReq):
    return service.cut(req.clean_path, req.ranges)

@app.post("/preview")
def preview(req: VideoReq):
    out = req.out_path or os.path.join(WORKDIR, uuid.uuid4().hex + ".mp4")
    return {"video_path": service.make_video(req.clean_path, req.text, out, req.style)}

@app.post("/export")
def export(req: VideoReq):
    return {"video_path": service.make_video(req.clean_path, req.text, req.out_path, req.style)}
