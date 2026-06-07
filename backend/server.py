import os, uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend import service
from backend.pipeline import subtitles
from backend.config import WORKDIR

app = FastAPI(title="AutoMontage")

# L'UI Electron (page file://) appelle cette API locale -> autoriser toutes origines.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

@app.exception_handler(Exception)
def on_error(request: Request, exc: Exception):
    # Renvoie une erreur JSON propre (sinon le front reçoit du texte = crash parse).
    return JSONResponse(status_code=500, content={"error": str(exc)})

class LoadReq(BaseModel):
    audio_path: str

class VideoReq(BaseModel):
    clean_path: str
    text: str
    out_path: str | None = None
    style: str = "karaoke_yellow"
    boost: bool = False

class CutReq(BaseModel):
    clean_path: str
    ranges: list[tuple[float, float]]

class CaptionReq(BaseModel):
    text: str

class SettingsReq(BaseModel):
    ig_token: str
    ig_user_id: str

class PublishReq(BaseModel):
    video_path: str
    caption: str

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

@app.post("/caption")
def caption_ep(req: CaptionReq):
    return service.make_caption(req.text)

@app.get("/settings")
def get_settings_ep():
    return service.get_settings()

@app.post("/settings")
def save_settings_ep(req: SettingsReq):
    return service.save_settings(req.ig_token, req.ig_user_id)

@app.post("/publish/instagram")
def publish_ig_ep(req: PublishReq):
    return service.publish_instagram(req.video_path, req.caption)

@app.post("/preview")
def preview(req: VideoReq):
    out = req.out_path or os.path.join(WORKDIR, uuid.uuid4().hex + ".mp4")
    return {"video_path": service.make_video(req.clean_path, req.text, out, req.style, req.boost)}

@app.post("/export")
def export(req: VideoReq):
    return {"video_path": service.make_video(req.clean_path, req.text, req.out_path, req.style, req.boost)}
