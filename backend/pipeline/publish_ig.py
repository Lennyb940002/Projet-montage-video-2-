import time
import httpx

GRAPH = "https://graph.facebook.com/v21.0"

def _err(j):
    return j.get("error", {}).get("message", str(j))

def create_container(ig_user_id, video_url, caption, token):
    r = httpx.post(f"{GRAPH}/{ig_user_id}/media",
                   data={"media_type": "REELS", "video_url": video_url,
                         "caption": caption, "access_token": token}, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError("Instagram: " + _err(j))
    return j["id"]

def container_status(creation_id, token):
    r = httpx.get(f"{GRAPH}/{creation_id}",
                  params={"fields": "status_code", "access_token": token}, timeout=30)
    return r.json().get("status_code")

def wait_ready(creation_id, token, timeout=180, interval=4, sleep=time.sleep):
    waited = 0
    while waited < timeout:
        st = container_status(creation_id, token)
        if st == "FINISHED":
            return
        if st == "ERROR":
            raise RuntimeError("Instagram: l'encodage de la vidéo a échoué")
        sleep(interval); waited += interval
    raise RuntimeError("Instagram: délai d'encodage dépassé")

def publish(ig_user_id, creation_id, token):
    r = httpx.post(f"{GRAPH}/{ig_user_id}/media_publish",
                   data={"creation_id": creation_id, "access_token": token}, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError("Instagram: " + _err(j))
    return j["id"]

def publish_reel(video_path, caption, token, ig_user_id, url_provider, sleep=time.sleep):
    with url_provider(video_path) as url:
        cid = create_container(ig_user_id, url, caption, token)
        wait_ready(cid, token, sleep=sleep)
        return publish(ig_user_id, cid, token)
