"""Adapter upload-post.com (publication IG + TikTok). Exécutif et NON BLOQUANT :
renvoie {ok: bool, ids|error} au lieu de lever (le scheduler ne doit jamais crash)."""
import os
import httpx

API_URL = "https://api.upload-post.com/api/upload"
API_PHOTOS_URL = "https://api.upload-post.com/api/upload_photos"


TIKTOK_TITLE_MAX = 90


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _short_title(caption, limit=TIKTOK_TITLE_MAX):
    """Tronque proprement un titre (coupe au dernier espace, sans casser un mot)."""
    caption = caption.strip()
    if len(caption) <= limit:
        return caption
    cut = caption[:limit]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" .,—-")


def _apply_platform_titles(data, caption, platforms, platform_titles):
    """Ajoute les titres par plateforme. Auto : si TikTok est ciblé et le titre
    dépasse 90 car., on génère un `tiktok_title` tronqué (sinon TikTok refuse)."""
    titles = dict(platform_titles or {})
    if "tiktok" in platforms and "tiktok" not in titles and len(caption.strip()) > TIKTOK_TITLE_MAX:
        titles["tiktok"] = _short_title(caption)
    for plat, t in titles.items():
        data[f"{plat}_title"] = t
    return data


def post(video_path, caption, platforms, user, token, _open=_read, platform_titles=None,
         media_type=None):
    """Publie la vidéo sur `platforms` (ex ["tiktok","instagram"]). `media_type=
    "STORIES"` => story vidéo IG (sinon Reel). Renvoie {ok, results} ou {ok:False}."""
    if not token or not user:
        return {"ok": False, "error": "missing credentials (token/user)"}
    try:
        data = {"user": user, "platform[]": list(platforms), "title": caption}
        if media_type:
            data["media_type"] = media_type
        _apply_platform_titles(data, caption, list(platforms), platform_titles)
        files = {"video": ("video.mp4", _open(video_path), "video/mp4")}
        r = httpx.post(API_URL, headers={"Authorization": f"Apikey {token}"},
                       data=data, files=files, timeout=180)
        j = r.json()
        if r.status_code == 200 and j.get("success", True):
            return {"ok": True, "results": j.get("results", j)}
        return {"ok": False, "error": j.get("error", f"HTTP {r.status_code}: {j}")}
    except Exception as e:
        return {"ok": False, "error": f"upload-post exception: {e}"}


def post_photos(photo_paths, caption, platforms, user, token, _open=_read,
                platform_titles=None, media_type=None):
    """Publie des photos sur `platforms`. `media_type="STORIES"` => story IG
    (sinon post/carrousel feed). `platform_titles` : titres par plateforme
    (ex TikTok limité à 90 car.). Non bloquant."""
    if not token or not user:
        return {"ok": False, "error": "missing credentials (token/user)"}
    if not photo_paths:
        return {"ok": False, "error": "no photos"}
    try:
        # platform[] = liste (httpx répète le champ) ; photos[] = liste de fichiers.
        data = {"user": user, "title": caption, "platform[]": list(platforms)}
        if media_type:
            data["media_type"] = media_type      # ex STORIES
        _apply_platform_titles(data, caption, list(platforms), platform_titles)
        files = [("photos[]", (os.path.basename(p), _open(p), "image/png"))
                 for p in photo_paths]
        r = httpx.post(API_PHOTOS_URL, headers={"Authorization": f"Apikey {token}"},
                       data=data, files=files, timeout=300)
        j = r.json()
        if r.status_code == 200 and j.get("success", True):
            return {"ok": True, "results": j.get("results", j)}
        return {"ok": False, "error": j.get("error", f"HTTP {r.status_code}: {j}")}
    except Exception as e:
        return {"ok": False, "error": f"upload-post exception: {e}"}
