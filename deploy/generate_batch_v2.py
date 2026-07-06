"""Génère le batch de test Flowers Chrome V2 depuis deploy/test_batch_v2.json.

- `--dry-run` : valide les 24 concepts + classe la Preuve SANS rendre de vidéo.
- mode réel   : rend les concepts rendables dans un dossier dédié + manifeste.
Ne publie JAMAIS. Continue proprement si un concept échoue. Les concepts Preuve
sans matière réelle sont marqués `blocked_missing_asset` (aucune fausse preuve).

Usage :
    python deploy/generate_batch_v2.py --dry-run
    python deploy/generate_batch_v2.py --out output/v2_batch
"""
import argparse
import datetime
import json
import os
import sys
import zlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
from backend.config import SILENT, FAMILIES_V2, FAMILY_ALLOWED_CTA
from backend.silent import registry, canon, captions_v2
from backend.silent import render as _render
from backend.silent.recipe import VideoRecipe, validate as _validate

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BATCH = os.path.join(HERE, "test_batch_v2.json")
OUT_DEFAULT = os.path.join(ROOT, "output", "v2_batch")
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".m4v")

# model_id (banque V2) -> dossier de clips (clé SILENT['models'])
MODEL_FOLDER = {"aurora": "Rainbow Or rose", "nocturne": "Rainbow saphire",
                "braise": "Rainbow ruby", "eclipse": "Rainbow silver", "meridien": "GMT"}


def _display_name(model_id):
    folder = MODEL_FOLDER.get(model_id, "")
    return ((SILENT.get("models") or {}).get(folder) or {}).get("name", model_id)


def _default_clip_resolver(model_id):
    """model_id -> chemin d'un clip de la banque, ou None si absent."""
    folder = MODEL_FOLDER.get(model_id)
    if not folder:
        return None
    d = os.path.join(SILENT["clips_dir"], folder)
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if os.path.splitext(f)[1].lower() in VIDEO_EXT:
            return os.path.join(d, f)
    return None


def _validate_concept(c):
    """None si conforme, sinon message d'erreur (cohérence famille/mécanique/CTA)."""
    fam = c.get("family_id")
    if fam not in FAMILIES_V2:
        return f"famille inconnue: {fam!r}"
    spec = FAMILIES_V2[fam]
    for k in ("mechanic", "visual_layout"):
        if c.get(k) != spec[k]:
            return f"{k} {c.get(k)!r} != famille ({spec[k]!r})"
    if c.get("cta_type") not in FAMILY_ALLOWED_CTA[fam]:
        return f"cta_type {c.get('cta_type')!r} non autorisé pour {fam} ({FAMILY_ALLOWED_CTA[fam]})"
    m = registry.MECHANICS.get(c["mechanic"])
    if not m or not registry.is_active(c["mechanic"]):
        return f"mécanique inactive/inconnue: {c.get('mechanic')!r}"
    if len(c.get("models", [])) != m["asset_count"]:
        return f"nb modèles {len(c.get('models', []))} != asset_count {m['asset_count']}"
    if not canon.is_clean(c.get("hook", "")):
        return "hook non conforme Canon V1"
    return None


def _build_recipe(c, clips):
    m = registry.MECHANICS[c["mechanic"]]
    return _validate(VideoRecipe(
        mechanic=c["mechanic"], layout=c["visual_layout"], hook=c["hook"],
        content_angle=c.get("hook_id", "x"), assets=tuple(clips),
        duration=m["default_duration"], font=SILENT["fonts"][0],
        accent=SILENT["accents"][0], text_anim="fade",
        seed=zlib.crc32(c["concept_id"].encode()) % 10**8, cta_type=c["cta_type"]))


def _entry(c, status, out_path=None, cap_path=None, caption=None,
           caption_status=None, missing_material=None, error=None):
    return {"family_id": c["family_id"], "concept_id": c["concept_id"],
            "hook_id": c["hook_id"], "cta_type": c["cta_type"],
            "model_ids": c["models"], "visual_layout": c["visual_layout"],
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "output_path": out_path, "caption_path": cap_path, "caption": caption,
            "caption_status": caption_status, "missing_material": missing_material,
            "render_status": status, "error": error, "published_at": None}


def main(dry_run=True, out_dir=OUT_DEFAULT, only=None, clip_resolver=None):
    clip_resolver = clip_resolver or _default_clip_resolver
    concepts = json.load(open(BATCH, encoding="utf-8"))["concepts"]
    if only:
        keep = set(only)
        concepts = [c for c in concepts if c["concept_id"] in keep]
    os.makedirs(out_dir, exist_ok=True)
    entries = []
    for c in concepts:
        err = _validate_concept(c)
        if err:
            entries.append(_entry(c, "invalid", error=err))
            continue
        names = [_display_name(x) for x in c["models"]]
        # Preuve sans matière -> aucune caption publiable (caption null + brief).
        if captions_v2.is_blocked(c):
            entries.append(_entry(c, "blocked_missing_asset", caption=None,
                                  caption_status="blocked_missing_asset",
                                  missing_material=c.get("missing_material"),
                                  error="preuve nécessite une vraie prise de vue"))
            continue
        # Caption V2 (dépendante du contexte éditorial du concept).
        try:
            cap_text = captions_v2.build(c, names)
            ok, why = captions_v2.validate(cap_text, c)
            if not ok:
                entries.append(_entry(c, "invalid", error="caption: " + why))
                continue
        except Exception as e:
            entries.append(_entry(c, "invalid", error="caption: " + str(e)[:200]))
            continue
        cap_path = os.path.join(out_dir, c["concept_id"] + ".caption.txt")
        with open(cap_path, "w", encoding="utf-8") as f:
            f.write(cap_text)
        if dry_run:
            entries.append(_entry(c, "dry_run_ok", cap_path=cap_path, caption=cap_text,
                                  caption_status="finalisée"))
            continue
        try:
            clips = [clip_resolver(mid) for mid in c["models"]]
            missing = [mid for mid, p in zip(c["models"], clips) if not p]
            if missing:
                entries.append(_entry(c, "missing_clip", cap_path=cap_path, caption=cap_text,
                                      caption_status="finalisée",
                                      error="clip absent: " + ", ".join(missing)))
                continue
            out_mp4 = os.path.join(out_dir, c["concept_id"] + ".mp4")
            _render.render_recipe(_build_recipe(c, clips), out_mp4)
            entries.append(_entry(c, "rendered", out_mp4, cap_path, caption=cap_text,
                                  caption_status="finalisée"))
        except Exception as e:                                # jamais bloquant
            entries.append(_entry(c, "error", cap_path=cap_path, caption=cap_text,
                                  caption_status="finalisée", error=str(e)[:300]))
    manifest = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "dry_run": dry_run, "total": len(entries),
                "counts": dict(Counter(e["render_status"] for e in entries)),
                "concepts": entries}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    man = main(dry_run=a.dry_run, out_dir=a.out)
    print(f"[batch] dry_run={man['dry_run']} total={man['total']} {man['counts']}")
    print(f"[batch] manifeste -> {os.path.join(a.out, 'manifest.json')}")
