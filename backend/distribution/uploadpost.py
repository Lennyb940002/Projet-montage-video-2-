"""Adapter upload-post.com (publication IG + TikTok). Exécutif et NON BLOQUANT :
renvoie {ok: bool, ids|error} au lieu de lever (le scheduler ne doit jamais crash)."""
import httpx

API_URL = "https://api.upload-post.com/api/upload"


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def post(video_path, caption, platforms, user, token, _open=_read):
    """Publie la vidéo sur `platforms` (ex ["tiktok","instagram"]) via le profil
    `user`. Renvoie {ok, results} ou {ok:False, error}."""
    if not token or not user:
        return {"ok": False, "error": "missing credentials (token/user)"}
    try:
        data = {"user": user, "platform[]": list(platforms), "title": caption}
        files = {"video": ("video.mp4", _open(video_path), "video/mp4")}
        r = httpx.post(API_URL, headers={"Authorization": f"Apikey {token}"},
                       data=data, files=files, timeout=180)
        j = r.json()
        if r.status_code == 200 and j.get("success", True):
            return {"ok": True, "results": j.get("results", j)}
        return {"ok": False, "error": j.get("error", f"HTTP {r.status_code}: {j}")}
    except Exception as e:
        return {"ok": False, "error": f"upload-post exception: {e}"}
