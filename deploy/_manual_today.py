"""Posts MANUELS exceptionnels (taggés -> exclus de la lecture analytique propre).
Reel + story, carrousel + story, et reel programmé à une heure donnée."""
import datetime
import random
import sys
import time

import httpx
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from backend import settings
from backend.config import SILENT_DB
from backend.distribution import orchestrator as vorch      # vidéos
from backend.distribution import uploadpost
from backend.distribution.store import DistStore
from backend.posts import orchestrator as corch             # carrousels
from backend.posts import analytics

STATUS = "https://api.upload-post.com/api/uploadposts/status"


def _ig_id(resp, token, tries=20, delay=6):
    """Récupère le platform_post_id Instagram d'une réponse upload-post (async)."""
    rid = (resp.get("results") or {}).get("request_id") if resp.get("ok") else None
    if not rid:
        return None
    for _ in range(tries):
        j = httpx.get(STATUS, params={"request_id": rid},
                      headers={"Authorization": f"Apikey {token}"}, timeout=60).json()
        if j.get("status") == "completed":
            for r in j.get("results", []):
                if r.get("platform") == "instagram" and r.get("platform_post_id"):
                    return r["platform_post_id"]
            return None
        time.sleep(delay)
    return None


def _flag_recent(minutes=12):
    """Filet de sécurité : tague comme manuels tous les posts IG des `minutes`
    dernières minutes (au cas où le polling a raté un platform_post_id)."""
    s = settings.load()
    user, token = s.get("uploadpost_user", ""), s.get("uploadpost_token", "")
    hist = httpx.get("https://api.upload-post.com/api/uploadposts/history",
                     params={"profile_username": user},
                     headers={"Authorization": f"Apikey {token}"}, timeout=60).json().get("history", [])
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    recent = []
    for h in hist:
        if h.get("platform") != "instagram" or not h.get("platform_post_id"):
            continue
        try:
            dt = datetime.datetime.strptime(h.get("upload_timestamp", "")[:19].replace("T", " "),
                                            "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if (now - dt).total_seconds() <= minutes * 60:
            recent.append(h["platform_post_id"])
    if recent:
        analytics.flag_manual(*recent)
    return recent


def post_reel(goal="engagement"):
    s = settings.load()
    user, token = s.get("uploadpost_user", ""), s.get("uploadpost_token", "")
    platforms = s.get("uploadpost_platforms") or ["instagram", "tiktok"]
    res = vorch.generate_for_slot(goal=goal, seed=random.randrange(10 ** 9))
    vid, caption = res["video_path"], res["caption"]
    fr = uploadpost.post(vid, caption, platforms, user, token)
    ig_post = _ig_id(fr, token)
    sr = uploadpost.post(vid, "", ["instagram"], user, token, media_type="STORIES")
    ig_story = _ig_id(sr, token)
    DistStore(SILENT_DB).update_status(res["pid"], "posted")
    vorch._cleanup_local(vid)
    analytics.flag_manual(ig_post, ig_story)
    time.sleep(90)                     # laisse le transcodage finir
    rec = _flag_recent(12)             # filet : tague les posts récents
    print(f"[reel MANUEL] feed={ig_post} story={ig_story} ok={fr.get('ok')} | filet={len(rec)} taggés")
    return ig_post


def post_carousel(kind="value"):
    s = settings.load()
    token = s.get("uploadpost_token", "")
    r = corch.generate_and_post(kind)
    ig_post = _ig_id(r.get("carousel") or {}, token)
    ig_story = _ig_id(r.get("story") or {}, token)
    analytics.flag_manual(ig_post, ig_story)
    print(f"[carrousel MANUEL] {r.get('id')} feed={ig_post} story={ig_story} posté={r.get('posted')}")
    return ig_post


def post_cta_story():
    import os
    import uuid
    from backend.posts import story
    from backend.config import WORKDIR
    s = settings.load()
    user, token = s.get("uploadpost_user", ""), s.get("uploadpost_token", "")
    out = os.path.join(WORKDIR, "cta_" + uuid.uuid4().hex + ".png")
    story.render_cta_story(out,
                           "Une de ces montres<br>vous tape dans l'œil ?",
                           "Dispos + prix, je réponds en privé.",
                           "📩 Écris « INTÉRESSÉ » en DM")
    r = uploadpost.post_photos([out], "", ["instagram"], user, token, media_type="STORIES")
    try:
        os.remove(out)
    except OSError:
        pass
    time.sleep(60)
    rec = _flag_recent(10)
    print(f"[CTA story MANUEL] ok={r.get('ok')} | filet={len(rec)} taggés")


def _sleep_until(hhmm):
    tz = ZoneInfo("Europe/Paris") if ZoneInfo else None
    h, m = (int(x) for x in hhmm.split(":"))
    now = datetime.datetime.now(tz)
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    delay = (target - now).total_seconds()
    if delay > 0:
        print(f"[attente] {round(delay/60)} min jusqu'à {hhmm}…", flush=True)
        time.sleep(delay)


def carousel_at(hhmm, kind="value"):
    _sleep_until(hhmm)
    post_carousel(kind)


def package_at(hhmm):
    """À l'heure dite : reel + story PUIS story CTA 'go DM'."""
    _sleep_until(hhmm)
    post_reel("engagement")
    post_cta_story()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "now"
    if cmd == "reel_now":
        post_reel("engagement")
    elif cmd == "cta_now":
        post_cta_story()
    elif cmd == "carousel_at":
        carousel_at(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "value")
    elif cmd == "package_at":
        package_at(sys.argv[2])
    elif cmd == "now":
        post_reel("engagement")
        post_carousel("value")
