"""Logger analytics : snapshot périodique des métriques IG par post, dans un CSV.
Accumule une série temporelle (signal IG réel = 24-72h) → base de décision.

Logge par post : famille + hook séparés, âge du post, métriques brutes ET ratios
(like/comment/share/engagement rate sur le reach). En quelques semaines → on peut
trancher « quel hook gagne ? » ET « quelle famille gagne ? » objectivement.

CSV : ~/.automontage/analytics.csv (hors git).
Registre : ~/.automontage/post_ids.json (suivre un post même hors fenêtre /history).
"""
import csv
import datetime
import json
import os
import re

import httpx
from backend import settings
from backend.config import SILENT
from backend.silent import registry

_DIR = os.path.join(os.path.expanduser("~"), ".automontage")
IDS_PATH = os.path.join(_DIR, "post_ids.json")
CSV_PATH = os.path.join(_DIR, "analytics.csv")
DMS_PATH = os.path.join(_DIR, "dms.json")   # {post_id: nb_dm} — saisie MANUELLE (pas d'API DM)
MANUAL_PATH = os.path.join(_DIR, "manual_posts.json")   # posts hors-protocole (exclus de la lecture propre)
PHOTO_PATH = os.path.join(_DIR, "photo_posts.json")     # posts photo réels (famille 'photo')
HISTORY_URL = "https://api.upload-post.com/api/uploadposts/history"
ANALYTICS_URL = "https://api.upload-post.com/api/uploadposts/post-analytics"

_FIELDS = ["snapshot", "post_date", "age_hours", "family", "hook", "cta_code",
           "primary_watch", "secondary_watch", "models",
           "views", "reach", "likes", "comments", "shares", "saves", "dm_count",
           "like_rate", "comment_rate", "share_rate", "engagement_rate", "dm_rate",
           "first_dm_age_h", "post_id"]

# Mécanique -> famille (libellé d'analyse).
_FAMILY_BY_MECHANIC = {
    "test": "identité", "elimination": "élimination", "projection": "projection",
    "vote": "duel", "collection": "duel", "top3": "classement", "pov": "pov",
    "comparison": "comparaison", "comparison_4": "grille", "collection_4": "grille",
    "battle": "vs", "transformation": "transfo", "erreur": "erreur",
    "revelation": "révélation",
}

# Noms de modèles connus (pour extraire les montres d'une caption).
_MODEL_NAMES = sorted(((m.get("name") or "") for m in (SILENT.get("models") or {}).values()),
                      key=len, reverse=True)


def _hook_family_map():
    """{hook_text_lower: famille} à partir de toutes les banques de hooks JSON."""
    out = {}
    for mech in registry.MECHANICS:
        fam = _FAMILY_BY_MECHANIC.get(mech, "autre")
        try:
            from backend.silent import hooks as _h
            for e in _h.load_hooks(mech):
                out[e["text"].strip().lower()] = fam
        except Exception:
            pass
    return out


_HOOK_FAMILY = None


def _family(hook):
    """Classe un hook (texte parsé) dans sa famille (exact, sinon sous-chaîne)."""
    global _HOOK_FAMILY
    if _HOOK_FAMILY is None:
        _HOOK_FAMILY = _hook_family_map()
    h = (hook or "").strip().lower()
    if h in _HOOK_FAMILY:
        return _HOOK_FAMILY[h]
    for text, fam in _HOOK_FAMILY.items():
        if text and (text in h or h in text):
            return fam
    return "autre"


# Posts antérieurs à la fenêtre /history (semés : date, plateforme, hook, famille).
_SEED = {
    "18061360529726853": ("2026-06-22 09:38", "instagram", "Le gagnant selon vous ?", "duel"),
    "18111781417937555": ("2026-06-22 13:01", "instagram", "Quel style gagne ?", "duel"),
    "17893352970488347": ("2026-06-22 15:03", "instagram", "Ce que ton choix dit de toi", "identité"),
    "18120638554740809": ("2026-06-22 19:01", "instagram", "POV ton salaire", "pov"),
    "17923144284366911": ("2026-06-22 19:09", "instagram", "Carrousel Automatique ou quartz", "carrousel"),
    "17951244297187845": ("2026-06-22 19:18", "instagram", "À ne jamais faire", "erreur"),
    "17931631092336667": ("2026-06-21 21:02", "instagram", "Le classement du jour", "classement"),
    "18046868531795027": ("2026-06-21 18:22", "instagram", "Qui mérite de gagner ?", "duel"),
}


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _load_ids():
    return _load_json(IDS_PATH)


def _cta_code(caption):
    m = re.search(r"\bFC\d+\b", caption or "")
    return m.group(0) if m else ""


def flag_manual(*post_ids):
    """Marque des posts comme 'manuels' (hors-protocole) -> exclus du rapport propre."""
    s = set(_load_json(MANUAL_PATH) or [])
    s.update(str(p) for p in post_ids if p)
    os.makedirs(_DIR, exist_ok=True)
    with open(MANUAL_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(s), f, ensure_ascii=False, indent=1)
    return len(s)


def flag_photo_recent(minutes=12):
    """Marque les posts IG des `minutes` dernières minutes comme 'photo' (famille
    dédiée). Robuste : pas besoin de capturer l'id au moment du post."""
    s = settings.load()
    user, token = s.get("uploadpost_user", ""), s.get("uploadpost_token", "")
    hist = httpx.get(HISTORY_URL, params={"profile_username": user},
                     headers={"Authorization": f"Apikey {token}"}, timeout=60).json().get("history", [])
    now = datetime.datetime.utcnow()
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
        cur = set(_load_json(PHOTO_PATH) or [])
        cur.update(recent)
        os.makedirs(_DIR, exist_ok=True)
        with open(PHOTO_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(cur), f, ensure_ascii=False, indent=1)
    return recent


def log_dm(key, count):
    """Enregistre le nb de DM d'un post (saisie manuelle). `key` = post_id OU code
    CTA (FCxxx, résolu vers le post). Renvoie (post_id, count)."""
    pid = str(key)
    if pid.upper().startswith("FC"):
        ids = _load_ids()
        match = [p for p, m in ids.items()
                 if (m.get("cta_code") or "").upper() == pid.upper()]
        if not match:
            raise ValueError(f"code CTA inconnu : {key}")
        pid = match[0]
    dms = _load_json(DMS_PATH)
    now = datetime.datetime.utcnow().isoformat(timespec="minutes") + "Z"
    entry = dms.get(pid) or {}
    if not isinstance(entry, dict):           # compat ancien format (int)
        entry = {"count": entry}
    entry["count"] = int(count)
    entry.setdefault("first_at", now)         # 1er DM loggé = proxy temps de décision
    entry["last_at"] = now
    dms[pid] = entry
    os.makedirs(_DIR, exist_ok=True)
    with open(DMS_PATH, "w", encoding="utf-8") as f:
        json.dump(dms, f, ensure_ascii=False, indent=1)
    return pid, int(count)


def _save_ids(ids):
    os.makedirs(_DIR, exist_ok=True)
    with open(IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=1)


def _parse(caption):
    """(hook, models) depuis une caption : hook = texte avant le 1er modèle."""
    caption = (caption or "").replace("\n", " ").strip()
    models = [n for n in _MODEL_NAMES if n and n in caption]
    cut = len(caption)
    for n in models:
        cut = min(cut, caption.find(n))
    hook = caption[:cut].strip(" .—-") if models else caption
    return hook[:70], " + ".join(models)


def _age_hours(post_date, now_utc):
    """Heures écoulées depuis la publication (post_date en UTC 'YYYY-MM-DD HH:MM')."""
    try:
        dt = datetime.datetime.strptime(post_date[:16], "%Y-%m-%d %H:%M")
        return round((now_utc - dt).total_seconds() / 3600.0, 1)
    except (ValueError, TypeError):
        return ""


def _first_dm_age(post_date, first_at):
    """Délai (h) entre la publication et le 1er DM loggé = proxy 'temps de décision'."""
    if not first_at:
        return ""
    try:
        p = datetime.datetime.strptime(post_date[:16], "%Y-%m-%d %H:%M")
        d = datetime.datetime.strptime(first_at[:16], "%Y-%m-%dT%H:%M")
        return round((d - p).total_seconds() / 3600.0, 1)
    except (ValueError, TypeError):
        return ""


def _rates(m):
    """Ratios sur le reach (le plus pertinent ; comment_rate surtout pour l'élim.)."""
    reach = m.get("reach", 0) or 0
    if reach <= 0:
        return 0.0, 0.0, 0.0, 0.0
    li, co = m.get("likes", 0), m.get("comments", 0)
    sh, sa = m.get("shares", 0), m.get("saves", 0)
    r = lambda x: round(x / reach, 4)
    return r(li), r(co), r(sh), r(li + co + sh + sa)


def _metrics(pid, user, token):
    r = httpx.get(ANALYTICS_URL, params={"platform_post_id": pid, "platform": "instagram",
                  "user": user}, headers={"Authorization": f"Apikey {token}"}, timeout=60)
    return ((r.json().get("platforms", {}) or {}).get("instagram", {}) or {}).get("post_metrics", {})


def register_from_history(ids, user, token):
    """Ajoute les posts de /history pas encore connus (avec famille déduite du hook)."""
    r = httpx.get(HISTORY_URL, params={"profile_username": user},
                  headers={"Authorization": f"Apikey {token}"}, timeout=60)
    photo_set = set(_load_json(PHOTO_PATH) or [])
    for h in r.json().get("history", []):
        pid = h.get("platform_post_id")
        if not pid or pid in ids:
            continue
        cap = h.get("post_caption") or h.get("post_title") or ""
        hook, models = _parse(cap)
        if pid in photo_set:
            fam = "photo"
        elif h.get("media_type") == "photo":
            fam = "carrousel"
        else:
            fam = _family(hook)
        ids[pid] = {"post_date": (h.get("upload_timestamp") or "")[:16].replace("T", " "),
                    "platform": h.get("platform"), "hook": hook, "models": models,
                    "family": fam, "cta_code": _cta_code(cap)}
    return ids


def snapshot():
    """Écrit une ligne de métriques (+ âge + ratios + famille) par post IG. Renvoie le nb."""
    s = settings.load()
    user, token = s.get("uploadpost_user", ""), s.get("uploadpost_token", "")
    ids = _load_ids()
    for pid, (date, plat, hook, fam) in _SEED.items():
        ids.setdefault(pid, {"post_date": date, "platform": plat, "hook": hook,
                             "models": "", "family": fam})
    register_from_history(ids, user, token)
    _save_ids(ids)
    dms = _load_json(DMS_PATH)

    now_utc = datetime.datetime.utcnow()
    snap = now_utc.isoformat(timespec="minutes") + "Z"
    new = not os.path.exists(CSV_PATH)
    n = 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        if new:
            w.writeheader()
        for pid, meta in ids.items():
            if meta.get("platform") != "instagram":
                continue
            m = _metrics(pid, user, token)
            lr, cr, sr, er = _rates(m)
            reach = m.get("reach", 0) or 0
            dm_entry = dms.get(pid) or {}
            if not isinstance(dm_entry, dict):
                dm_entry = {"count": dm_entry}
            dm = int(dm_entry.get("count", 0))
            models = meta.get("models", "")
            mods = models.split(" + ") if models else []
            w.writerow({"snapshot": snap, "post_date": meta["post_date"],
                        "age_hours": _age_hours(meta["post_date"], now_utc),
                        "family": meta.get("family", ""), "hook": meta["hook"],
                        "cta_code": meta.get("cta_code", ""),
                        "primary_watch": mods[0] if mods else "",
                        "secondary_watch": mods[1] if len(mods) > 1 else "",
                        "models": models,
                        "views": m.get("views", 0), "reach": reach,
                        "likes": m.get("likes", 0), "comments": m.get("comments", 0),
                        "shares": m.get("shares", 0), "saves": m.get("saves", 0),
                        "dm_count": dm,
                        "like_rate": lr, "comment_rate": cr, "share_rate": sr,
                        "engagement_rate": er,
                        "dm_rate": round(dm / reach, 4) if reach else 0.0,
                        "first_dm_age_h": _first_dm_age(meta["post_date"], dm_entry.get("first_at")),
                        "post_id": pid})
            n += 1
    return n


def _latest_per_post():
    """Dernier snapshot connu de chaque post (métriques les plus à jour)."""
    if not os.path.exists(CSV_PATH):
        return []
    latest = {}
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cur = latest.get(r["post_id"])
            if cur is None or r["snapshot"] > cur["snapshot"]:
                latest[r["post_id"]] = r
    return list(latest.values())


def _avg(rs, k):
    return sum(float(r.get(k) or 0) for r in rs) / len(rs)


def report():
    """3 tableaux : par FAMILLE (acquisition/engagement/vente), par HOOK, par MONTRE."""
    rows = _latest_per_post()
    if not rows:
        print("Aucune donnée."); return
    manual = set(_load_json(MANUAL_PATH) or [])
    excl = sum(1 for r in rows if r["post_id"] in manual)
    rows = [r for r in rows if r["post_id"] not in manual]
    if excl:
        print(f"(lecture propre : {excl} post(s) manuel(s) hors-protocole exclu(s))")

    by_fam, by_hook, by_watch = {}, {}, {}
    for r in rows:
        by_fam.setdefault(r["family"], []).append(r)
        by_hook.setdefault(r["hook"], []).append(r)
        for w in (r.get("models") or "").split(" + "):
            if w.strip():
                by_watch.setdefault(w.strip(), []).append(r)

    print(f"\n=== PAR FAMILLE ===\n{'famille':13}{'n':>3}{'vues':>7}{'reach':>7}{'com/reach':>10}{'DM':>5}{'DM/reach':>9}")
    for fam, rs in sorted(by_fam.items(), key=lambda kv: -_avg(kv[1], "views")):
        print(f"{fam:13}{len(rs):>3}{round(_avg(rs,'views')):>7}{round(_avg(rs,'reach')):>7}"
              f"{round(_avg(rs,'comment_rate'),4):>10}{round(_avg(rs,'dm_count'),1):>5}{round(_avg(rs,'dm_rate'),4):>9}")

    print(f"\n=== PAR HOOK ===\n{'hook':34}{'n':>3}{'vues':>7}{'DM':>5}")
    for hk, rs in sorted(by_hook.items(), key=lambda kv: -_avg(kv[1], "views")):
        print(f"{hk[:33]:34}{len(rs):>3}{round(_avg(rs,'views')):>7}{round(_avg(rs,'dm_count'),1):>5}")

    print(f"\n=== PAR MONTRE ===\n{'montre':24}{'n':>3}{'vues':>7}{'DM':>5}")
    for w, rs in sorted(by_watch.items(), key=lambda kv: -_avg(kv[1], "views")):
        print(f"{w[:23]:24}{len(rs):>3}{round(_avg(rs,'views')):>7}{round(_avg(rs,'dm_count'),1):>5}")


if __name__ == "__main__":
    import sys
    if "--report" in sys.argv:
        report()
    elif "--dm" in sys.argv:                       # --dm <post_id> <count>
        i = sys.argv.index("--dm")
        print("DM enregistrés :", log_dm(sys.argv[i + 1], sys.argv[i + 2]))
    else:
        print("[analytics] lignes écrites :", snapshot(), "->", CSV_PATH)
