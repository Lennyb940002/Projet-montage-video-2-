"""Posteur autonome (GitHub Actions) : lit stock/planning.json, publie via
upload-post.com les reels DUS (date/heure Europe/Paris <= maintenant, non postés),
coche `posted`. Standalone (requests) — aucune dépendance au backend, aucun ffmpeg.
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

API_URL = "https://api.upload-post.com/api/upload"
TIKTOK_TITLE_MAX = 90
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "2"))   # lisse le rattrapage (anti-flood)

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


def _upload(video_path, caption, platforms, user, token):
    import requests   # import paresseux : la logique de sélection reste testable sans requests
    data = {"user": user, "platform[]": platforms, "title": caption}
    if "tiktok" in platforms and len(caption.strip()) > TIKTOK_TITLE_MAX:
        data["tiktok_title"] = _short_title(caption)
    with open(video_path, "rb") as f:
        files = {"video": ("video.mp4", f, "video/mp4")}
        r = requests.post(API_URL, headers={"Authorization": f"Apikey {token}"},
                          data=data, files=files, timeout=300)
    try:
        j = r.json()
    except Exception:
        j = {"raw": r.text[:300]}
    if r.status_code == 200 and j.get("success", True):
        return True, j.get("results", j)
    return False, j.get("error", f"HTTP {r.status_code}: {j}")


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
    due = [it for it in planning if _due(it, now)]
    due.sort(key=lambda it: (it["date"], it["heure"]))
    print(f"{now.isoformat()} — {len(due)} reel(s) dû(s), on en poste au plus {MAX_PER_RUN}")

    posted = 0
    for it in due[:MAX_PER_RUN]:
        video = os.path.join(STOCK, it["fichier"])
        if not os.path.isfile(video):
            it["last_error"] = "fichier manquant"; print(f"  [{it['id']}] MANQUANT {it['fichier']}")
            continue
        ok, res = _upload(video, it.get("caption", it.get("hook", "")),
                          it.get("platforms", ["instagram"]), user, token)
        if ok:
            it["posted"] = True
            it["posted_at"] = now.isoformat()
            posted += 1
            print(f"  [{it['id']}] OK {it['format']} -> {it['fichier']}")
        else:
            it["last_error"] = str(res)
            print(f"  [{it['id']}] ECHEC {it['fichier']} : {res}")

    json.dump(planning, open(PLANNING, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Terminé : {posted} posté(s). Restants non postés : "
          f"{sum(1 for it in planning if not it.get('posted'))}")


if __name__ == "__main__":
    main()
