import os, uuid
from fastapi import FastAPI
from pydantic import BaseModel
from backend import service
from backend.config import WORKDIR

app = FastAPI(title="AutoMontage")

class LoadReq(BaseModel):
    audio_path: str

class VideoReq(BaseModel):
    clean_path: str
    text: str
    out_path: str | None = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/load")
def load(req: LoadReq):
    return service.load_audio(req.audio_path)

@app.post("/preview")
def preview(req: VideoReq):
    out = req.out_path or os.path.join(WORKDIR, uuid.uuid4().hex + ".mp4")
    return {"video_path": service.make_video(req.clean_path, req.text, out)}

@app.post("/export")
def export(req: VideoReq):
    return {"video_path": service.make_video(req.clean_path, req.text, req.out_path)}
