"""Publie le carrousel valeur du jour (IG + TikTok) PUIS sa story de partage (IG)."""
import os
import time
import httpx
from backend import settings
from backend.distribution import uploadpost
from backend.posts.story import render_story, pick_cta
from backend.posts.store import PostsStore
from backend.config import POSTS_DB

STATUS = "https://api.upload-post.com/api/uploadposts/status"
DIR = os.path.join(os.path.expanduser("~"), "carousel_value_today")
SLIDES = [os.path.join(DIR, f"val_light_{i:02d}.png") for i in range(1, 6)]

CAPTION = (
    "On pense souvent qu'une montre de qualité se reconnaît à son prix. En réalité, "
    "les passionnés regardent surtout le verre, le mouvement et les finitions. Ce sont "
    "ces détails qui influencent l'expérience au quotidien et la durabilité dans le temps.\n\n"
    "Chez Flowers Chrome®, nous privilégions la transparence : chaque modèle est présenté "
    "avec ses caractéristiques et son histoire.\n\n"
    "📩 DM \"MONTRE\" pour découvrir les modèles actuellement disponibles.\n\n"
    "#montre #horlogerie #seikomod #watchlover #montrestyle #flowerschrome"
)


def poll(rid, token, tries=15, delay=6):
    for _ in range(tries):
        j = httpx.get(STATUS, params={"request_id": rid},
                      headers={"Authorization": f"Apikey {token}"}, timeout=60).json()
        if j.get("status") == "completed":
            return j
        time.sleep(delay)
    return j


def show(j, label):
    for r in j.get("results", []):
        print(f"  [{label}] {r['platform']:10} success={r['success']} url={r.get('post_url')}")
        if r.get("error_message"):
            print("      ", r["error_message"][:90])


def main():
    s = settings.load()
    user, token = s.get("uploadpost_user", ""), s.get("uploadpost_token", "")
    miss = [p for p in SLIDES if not os.path.exists(p)]
    if miss:
        print("[ERREUR] slides manquantes:", miss); return 1

    # 1) carrousel feed -> IG + TikTok
    res = uploadpost.post_photos(SLIDES, CAPTION, ["instagram", "tiktok"], user, token)
    print("[carrousel]", res.get("ok"))
    rid = (res.get("results") or {}).get("request_id") if res.get("ok") else None
    if rid:
        show(poll(rid, token), "carrousel")

    # 2) story de partage (image, IG seulement)
    store = PostsStore(POSTS_DB)
    n = store.count()
    story_png = os.path.join(DIR, "story.png")
    render_story(SLIDES[0], story_png, hook="📚 Nouveau conseil", cta=pick_cta(n))
    sres = uploadpost.post_photos([story_png], "", ["instagram"], user, token,
                                  media_type="STORIES")
    print("[story]", sres.get("ok"), "-", str(sres.get("results") or sres.get("error"))[:90])
    srid = (sres.get("results") or {}).get("request_id") if sres.get("ok") else None
    if srid:
        show(poll(srid, token), "story")

    store.insert("Comment reconnaître une montre de qualité ?", "light",
                 caption=CAPTION, n_slides=5, status="posted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
