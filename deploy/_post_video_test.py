"""Test : génère 1 vidéo (moteur silencieux) et la poste sur IG + TikTok,
puis vérifie le statut par plateforme. But : confirmer le routage TikTok."""
import random
import time
import httpx
from backend import settings
from backend.distribution import orchestrator, uploadpost

STATUS_URL = "https://api.upload-post.com/api/uploadposts/status"


def poll(rid, token, tries=20, delay=6):
    for _ in range(tries):
        r = httpx.get(STATUS_URL, params={"request_id": rid},
                      headers={"Authorization": f"Apikey {token}"}, timeout=60)
        j = r.json()
        if j.get("status") == "completed":
            return j
        time.sleep(delay)
    return j


def main():
    s = settings.load()
    print("[gen] génération d'une vidéo…")
    res = orchestrator.generate_for_slot(goal="engagement", seed=random.randrange(10 ** 9))
    print(f"[gen] vidéo #{res['pid']} -> {res['video_path']}")
    print(f"[gen] caption: {res['caption'][:80]}…")

    out = uploadpost.post(res["video_path"], res["caption"],
                          ["instagram", "tiktok"],
                          s.get("uploadpost_user", ""), s.get("uploadpost_token", ""))
    print("[post]", out.get("ok"), "-", str(out.get("results") or out.get("error"))[:120])

    rid = (out.get("results") or {}).get("request_id") if out.get("ok") else None
    if rid:
        print(f"[poll] suivi du statut (request_id={rid})…")
        j = poll(rid, s["uploadpost_token"])
        for r in j.get("results", []):
            print(f"  {r['platform']:10} success={r['success']}  url={r.get('post_url')}")
            if r.get("error_message"):
                print("      erreur:", r["error_message"][:140])
    elif out.get("ok"):
        print("[post] réponse synchrone:", out["results"])


if __name__ == "__main__":
    main()
