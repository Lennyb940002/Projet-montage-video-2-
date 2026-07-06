"""Posteur autonome (GitHub Actions) : lit stock/planning.json, publie via
upload-post.com les items DUS (date/heure Europe/Paris <= maintenant, non postés),
coche `posted`. Standalone (requests) — aucun backend, aucun ffmpeg.
Route par `kind` : video | carrousel (N photos) | story (media_type STORIES).
Secrets via env : UPLOAD_POST_TOKEN, UPLOAD_POST_USER."""
import os
import sys
import json
import datetime

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Paris")
except Exception:                       # runner sans tzdata -> UTC (léger décalage acceptable)
    TZ = datetime.timezone.utc

API_VIDEO = "https://api.upload-post.com/api/upload"
API_PHOTOS = "https://api.upload-post.com/api/upload_photos"
TIKTOK_TITLE_MAX = 90
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "2"))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK = os.path.join(ROOT, "stock")
PLANNING = os.path.join(STOCK, "planning.json")


def _short_title(caption, limit=TIKTOK_TITLE_MAX):
    caption = caption.strip()
    if len(caption) <= limit:
        return caption
    cut = caption[:limit]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" .,—-")


def _due(item, now):
    if item.get("posted"):
        return False
    try:
        d = datetime.datetime.fromisoformat(f"{item['date']}T{item['heure']}:00")
    except Exception:
        return False
    return d.replace(tzinfo=TZ) <= now


def _files(item):
    return item.get("fichiers") or ([item["fichier"]] if item.get("fichier") else [])


def _upload_video(path, caption, platforms, user, token):
    import requests
    data = {"user": user, "platform[]": platforms, "title": caption}
    if "tiktok" in platforms and len(caption.strip()) > TIKTOK_TITLE_MAX:
        data["tiktok_title"] = _short_title(caption)
    with open(path, "rb") as f:
        r = requests.post(API_VIDEO, headers={"Authorization": f"Apikey {token}"},
                          data=data, files={"video": ("video.mp4", f, "video/mp4")}, timeout=300)
    return _result(r)


def _upload_photos(paths, caption, platforms, media_type, user, token):
    import requests
    data = {"user": user, "platform[]": platforms, "title": caption}
    if media_type:
        data["media_type"] = media_type          # ex "STORIES"
    if "tiktok" in platforms and len(caption.strip()) > TIKTOK_TITLE_MAX:
        data["tiktok_title"] = _short_title(caption)
    handles = [open(p, "rb") for p in paths]
    try:
        files = [("photos[]", (os.path.basename(p), h, "image/png"))
                 for p, h in zip(paths, handles)]
        r = requests.post(API_PHOTOS, headers={"Authorization": f"Apikey {token}"},
                          data=data, files=files, timeout=300)
    finally:
        for h in handles:
            h.close()
    return _result(r)


def _result(r):
    try:
        j = r.json()
    except Exception:
        j = {"raw": r.text[:300]}
    if r.status_code == 200 and j.get("success", True):
        return True, j.get("results", j)
    return False, j.get("error", f"HTTP {r.status_code}: {j}")


def _post_item(item, user, token):
    kind = item.get("kind", "video")
    caption = item.get("caption", item.get("hook", ""))
    platforms = item.get("platforms", ["instagram"])
    files = [os.path.join(STOCK, f) for f in _files(item)]
    missing = [f for f in files if not os.path.isfile(f)]
    if not files or missing:
        return False, f"fichier(s) manquant(s): {missing or 'aucun'}"
    if kind == "video":
        return _upload_video(files[0], caption, platforms, user, token)
    if kind == "story":
        return _upload_photos(files, caption, platforms, "STORIES", user, token)
    if kind == "carrousel":
        return _upload_photos(files, caption, platforms, None, user, token)
    return False, f"kind inconnu: {kind}"


def main():
    token = os.environ.get("UPLOAD_POST_TOKEN")
    user = os.environ.get("UPLOAD_POST_USER")
    if not token or not user:
        print("ERREUR : UPLOAD_POST_TOKEN / UPLOAD_POST_USER manquants (GitHub Secrets)")
        sys.exit(1)
    if not os.path.isfile(PLANNING):
        print(f"planning.json introuvable : {PLANNING}"); sys.exit(1)

    planning = json.load(open(PLANNING, encoding="utf-8"))
    now = datetime.datetime.now(TZ)
    due = sorted([it for it in planning if _due(it, now)],
                 key=lambda it: (it["date"], it["heure"]))
    print(f"{now.isoformat()} — {len(due)} item(s) dû(s), on en poste au plus {MAX_PER_RUN}")

    posted = 0
    for it in due[:MAX_PER_RUN]:
        ok, res = _post_item(it, user, token)
        label = f"{it.get('kind', 'video')} {it.get('format', '')}".strip()
        if ok:
            it["posted"] = True
            it["posted_at"] = now.isoformat()
            posted += 1
            print(f"  [{it.get('id', '?')}] OK {label}")
        else:
            it["last_error"] = str(res)
            print(f"  [{it.get('id', '?')}] ECHEC {label} : {res}")

    json.dump(planning, open(PLANNING, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Terminé : {posted} posté(s). Restants : "
          f"{sum(1 for it in planning if not it.get('posted'))}")


if __name__ == "__main__":
    main()
