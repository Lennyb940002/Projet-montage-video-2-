"""Orchestrateur Stories V2 — génère les séquences depuis deploy/stories_v2.json.
AUCUNE publication. Frames bloquées -> statut explicite, le batch continue.

Usage :
    python deploy/generate_stories_v2.py --dry-run
    python deploy/generate_stories_v2.py --highlight models
    python deploy/generate_stories_v2.py --highlight choose
    python deploy/generate_stories_v2.py --daily-family model_of_day [--model aurora]
    python deploy/generate_stories_v2.py --covers

Statuts : rendered · dry_run_ok · blocked_unverified_claim · blocked_missing_asset ·
render_error. Sticker sondage = manual_instagram_action (pose manuelle IG)."""
import argparse
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.posts import stories_v2 as sv


def _asset_info(path):
    """Traçabilité d'une source : id, chemin, hash, dimensions réelles."""
    from PIL import Image
    with open(path, "rb") as f:
        h = hashlib.sha1(f.read()).hexdigest()[:16]
    with Image.open(path) as im:
        w, hgt = im.size
    return {"resolved_asset_id": os.path.splitext(os.path.basename(path))[0],
            "resolved_asset_path": os.path.abspath(path),
            "source_hash": h, "source_width": w, "source_height": hgt}


def _brand_info():
    path, _ = sv.brand_asset()
    if not path:
        return {"brand_asset_id": None, "brand_asset_path": None, "brand_asset_hash": None}
    info = _asset_info(path)
    return {"brand_asset_id": "fc_avatar_v1", "brand_asset_path": info["resolved_asset_path"],
            "brand_asset_hash": info["source_hash"]}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BANK = os.path.join(HERE, "stories_v2.json")
OUT_DEFAULT = os.path.join(ROOT, "output", "stories_v2")
COVERS_DIR = os.path.join(ROOT, "assets", "highlight_covers")

MODEL_TRAITS = {"aurora": "La lumière chaude", "nocturne": "Le bleu profond",
                "braise": "L'intensité", "eclipse": "La sobriété",
                "meridien": "L'appel du voyage"}

# ------------------------- Couvertures (pack homogène) -------------------------
_SVG_FRAME = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" fill="#070707"/>
<defs><linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#E8EAEC"/><stop offset="1" stop-color="#9EA3A8"/>
</linearGradient></defs>
<g fill="none" stroke="url(#chrome)" stroke-width="26" stroke-linecap="round" stroke-linejoin="round">
{glyph}</g>
<path d="{amber}" stroke="#C99645" stroke-width="7" opacity="0.55" fill="none" stroke-linecap="round"/>
</svg>"""

COVERS = {
    "models":   {"glyph": '<circle cx="256" cy="256" r="118"/><path d="M216 106 h80 M216 406 h80 M256 256 V196 M256 256 h44"/>',
                 "amber": "M340 176 A118 118 0 0 1 372 240"},
    "choose":   {"glyph": '<path d="M184 150 h144 a48 48 0 0 1 48 48 v70 a48 48 0 0 1 -48 48 h-88 l-60 56 v-56 h-44 a48 48 0 0 1 -48 -48 v-70 a48 48 0 0 1 48 -48 z"/><path d="M212 234 l32 32 58 -60"/>',
                 "amber": "M348 160 a48 48 0 0 1 24 30"},
    "reviews":  {"glyph": '<path d="M256 116 L294 222 404 226 318 292 348 398 256 336 164 398 194 292 108 226 218 222 Z"/>',
                 "amber": "M318 300 l20 66"},
    "quality":  {"glyph": '<circle cx="230" cy="230" r="104"/><path d="M306 306 L398 398 M230 230 v-44 M230 230 h32"/>',
                 "amber": "M304 156 a104 104 0 0 1 28 60"},
    "shipping": {"glyph": '<path d="M136 182 h240 v196 h-240 z M136 244 h240 M256 182 v62"/>',
                 "amber": "M136 400 h72"},
    "faq":      {"glyph": '<path d="M182 206 a74 74 0 1 1 116 60 c-26 19 -42 32 -42 66"/><circle cx="256" cy="398" r="8"/>',
                 "amber": "M312 156 a74 74 0 0 1 16 40"},
}


def make_covers():
    """6 SVG + 6 PNG 512 + 6 PNG 60 (contrôle) — pack homogène."""
    from playwright.sync_api import sync_playwright
    from PIL import Image
    os.makedirs(COVERS_DIR, exist_ok=True)
    made = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_context(viewport={"width": 512, "height": 512}).new_page()
        for name, spec in COVERS.items():
            svg = _SVG_FRAME.format(glyph=spec["glyph"], amber=spec["amber"])
            svg_path = os.path.join(COVERS_DIR, f"cover_{name}.svg")
            open(svg_path, "w", encoding="utf-8").write(svg)
            page.set_content(f"<body style='margin:0'>{svg}</body>")
            page.wait_for_timeout(120)
            png512 = os.path.join(COVERS_DIR, f"cover_{name}_512.png")
            page.screenshot(path=png512, clip={"x": 0, "y": 0, "width": 512, "height": 512})
            Image.open(png512).resize((60, 60), Image.LANCZOS).save(
                os.path.join(COVERS_DIR, f"cover_{name}_60.png"))
            made.append(name)
        b.close()
    return made


# ------------------------- Frames -------------------------
def _resolve_placeholders(fr, model=None, pair=None):
    fr = dict(fr)
    if fr.get("model_id") == "{rotation}" or fr.get("model_id") == "{manual}":
        fr["model_id"] = model or "aurora"
    if fr.get("model_id") == "{pair}":
        fr["model_id"] = list(pair or ("aurora", "nocturne"))
    name = sv.MODEL_NAMES.get(fr.get("model_id")) if isinstance(fr.get("model_id"), str) else None
    for k in ("on_screen_text", "subtext"):
        v = fr.get(k)
        if isinstance(v, str):
            v = v.replace("{model_name}", name or "")
            v = v.replace("{model_trait}", MODEL_TRAITS.get(fr.get("model_id"), "")
                          if isinstance(fr.get("model_id"), str) else "")
            fr[k] = v
    return fr


def _facts_text(fr, facts):
    """Remplace {fact_key} par la valeur vérifiée. Appelé APRÈS le gate claims."""
    fr = dict(fr)
    for k in ("on_screen_text", "subtext"):
        v = fr.get(k)
        if isinstance(v, str):
            for dep in fr.get("claim_dependencies", []):
                val = (facts.get(dep) or {}).get("value")
                if isinstance(val, list):
                    val = " · ".join(str(x) for x in val)
                v = v.replace("{%s}" % dep, str(val or ""))
            fr[k] = v
    return fr


def _entry(fr, seq_id, status, out_path=None, error=None, resolved=None):
    e = {"frame_id": fr["frame_id"], "sequence_id": seq_id,
         "template_id": fr["template_id"],
         "presentation_mode": fr.get("presentation_mode"),
         "model_id": fr.get("model_id"),
         "requested_asset_id": fr.get("asset_id"),
         "resolved_asset_id": None, "resolved_asset_path": None,
         "source_hash": None, "source_width": 0, "source_height": 0,
         "claim_status": fr.get("claim_status"), "render_status": status,
         "output_path": out_path,
         "manual_instagram_action": fr.get("manual_instagram_action"),
         "internal_brief": fr.get("internal_brief"),
         "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
         "published_at": None, "error": error}
    if resolved:
        e.update(resolved)
    e.update(_brand_info())
    # Règles strictes : un rendu qui utilise une image DOIT tracer sa source,
    # et TOUT rendu doit utiliser le vrai asset de marque (aucun fallback).
    if status == "rendered" and fr["template_id"] not in ("minimal_text", "faq") \
            and not e["resolved_asset_path"]:
        raise RuntimeError(f"rendu non tracé (asset source manquant) : {fr['frame_id']}")
    if status == "rendered" and not e["brand_asset_id"]:
        raise RuntimeError(f"rendu sans asset de marque tracé : {fr['frame_id']}")
    return e


def process_frames(frames, seq_id, out_dir, dry_run, facts, model=None, pair=None,
                   asset_resolver=None):
    entries = []
    for raw in frames:
        fr = _resolve_placeholders(raw, model=model, pair=pair)
        # 1) matière réelle absente -> bloqué (brief interne, jamais de faux rendu)
        if fr.get("render_mode") == "requires_real_asset":
            real = asset_resolver(fr) if asset_resolver else None
            if not real:
                entries.append(_entry(fr, seq_id, "blocked_missing_asset"))
                continue
            fr["_asset_path"] = real
        # 2) claims non confirmés -> bloqué
        deps = fr.get("claim_dependencies", [])
        if deps and not all(sv.fact_verified(facts, d) for d in deps):
            entries.append(_entry(fr, seq_id, "blocked_unverified_claim"))
            continue
        if dry_run:
            entries.append(_entry(fr, seq_id, "dry_run_ok"))
            continue
        # 3) rendu réel
        try:
            fr = _facts_text(fr, facts)
            resolved = None
            if fr["template_id"] == "choice":
                photo = tuple(sv.photo_for_model(m) for m in fr["model_id"])
                if not all(photo):
                    entries.append(_entry(fr, seq_id, "blocked_missing_asset",
                                          error="photo modèle absente"))
                    continue
                infos = [_asset_info(p) for p in photo]
                resolved = {"resolved_asset_id": "+".join(i["resolved_asset_id"] for i in infos),
                            "resolved_asset_path": ";".join(i["resolved_asset_path"] for i in infos),
                            "source_hash": "+".join(i["source_hash"] for i in infos),
                            "source_width": infos[0]["source_width"],
                            "source_height": infos[0]["source_height"]}
            elif fr.get("_asset_path"):
                photo = fr["_asset_path"]
                resolved = _asset_info(photo)
            elif fr.get("model_id"):
                photo = sv.photo_for_model(fr["model_id"])
                if fr["template_id"].startswith(("hero_model", "detail_macro")) \
                        or fr["template_id"] == "availability_verified":
                    if not photo:
                        entries.append(_entry(fr, seq_id, "blocked_missing_asset",
                                              error="photo modèle absente"))
                        continue
                    resolved = _asset_info(photo)
            else:
                photo = None
            out = os.path.join(out_dir, f"{seq_id}_{fr['frame_id']}.png")
            sv.render_frame(fr, out, photo, debug=fr.get("_debug", False))
            entries.append(_entry(fr, seq_id, "rendered", out, resolved=resolved))
        except sv.MissingBrandAsset as e:
            entries.append(_entry(fr, seq_id, "blocked_missing_brand_asset",
                                  error=str(e)[:200]))
        except Exception as e:
            entries.append(_entry(fr, seq_id, "render_error", error=str(e)[:300]))
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--highlight")
    ap.add_argument("--daily-family")
    ap.add_argument("--covers", action="store_true")
    ap.add_argument("--model")
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    if a.covers:
        made = make_covers()
        print(f"[stories] couvertures générées : {made} -> {COVERS_DIR}")
        return 0
    bank = json.load(open(BANK, encoding="utf-8"))
    facts = sv.load_facts()
    entries = []
    if a.highlight:
        hl = bank["highlights"][a.highlight]
        entries += process_frames(hl["frames"], a.highlight, a.out, a.dry_run, facts,
                                  model=a.model)
    elif a.daily_family:
        fam = bank["daily_families"][a.daily_family]
        entries += process_frames(fam["frames"], a.daily_family, a.out, a.dry_run,
                                  facts, model=a.model)
    else:   # tout (dry-run global par défaut)
        for hid, hl in bank["highlights"].items():
            entries += process_frames(hl["frames"], hid, a.out, a.dry_run, facts)
        for fid, fam in bank["daily_families"].items():
            entries += process_frames(fam["frames"], fid, a.out, a.dry_run, facts)
    from collections import Counter
    manifest = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "dry_run": a.dry_run, "total": len(entries),
                "counts": dict(Counter(e["render_status"] for e in entries)),
                "frames": entries}
    with open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[stories] total={manifest['total']} {manifest['counts']}")
    print(f"[stories] manifeste -> {os.path.join(a.out, 'manifest.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
