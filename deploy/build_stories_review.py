"""Pack de REVUE VISUELLE Stories V2 -> output/stories_v2/review/
Contact sheets + PNG individuels + comparaison daylight A/B + debug safe-zones
+ manifeste enrichi + README. AUCUNE publication.

Usage : python deploy/build_stories_review.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw, ImageFont

from backend.posts import stories_v2 as sv
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "gen_stories_v2", os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_stories_v2.py"))
gs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gs)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW = os.path.join(ROOT, "output", "stories_v2", "review")
COVERS = os.path.join(ROOT, "assets", "highlight_covers")
FONT = "C:/Windows/Fonts/arial.ttf"

SETS = [  # (dossier_full, seq_id, frames_filter)
    ("highlight_models_full", "models", None),
    ("highlight_choose_full", "choose", None),
    ("faq_full", "faq", None),
    ("quality_full", "quality", None),
]
DAILIES = [("model_of_day", "braise", None), ("help_me_choose", None, ("aurora", "nocturne")),
           ("real_detail", "nocturne", None)]


def _font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except Exception:
        return ImageFont.load_default()


def _label(draw, x, y, lines, size=16):
    f = _font(size)
    for i, ln in enumerate(lines):
        draw.text((x, y + i * (size + 5)), ln, fill="#DDDDDD", font=f)


def contact_sheet(items, out_path, thumb_w=270, cols=5, label_h=92):
    """items = [(png_path, [label lines])]. Miniatures + labels HORS du visuel."""
    th = int(thumb_w * 1920 / 1080)
    rows = (len(items) + cols - 1) // cols
    pad = 26
    W = cols * (thumb_w + pad) + pad
    H = rows * (th + label_h + pad) + pad
    sheet = Image.new("RGB", (W, H), "#101012")
    d = ImageDraw.Draw(sheet)
    for i, (p, lines) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (thumb_w + pad)
        y = pad + r * (th + label_h + pad)
        im = Image.open(p).convert("RGB").resize((thumb_w, th), Image.LANCZOS)
        sheet.paste(im, (x, y))
        _label(d, x, y + th + 8, lines)
    sheet.save(out_path)


def covers_sheets():
    names = ["models", "choose", "reviews", "quality", "shipping", "faq"]
    # 512
    pad = 36
    sheet = Image.new("RGB", (3 * (512 + pad) + pad, 2 * (512 + 60 + pad) + pad), "#101012")
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        r, c = divmod(i, 3)
        x, y = pad + c * (512 + pad), pad + r * (512 + 60 + pad)
        sheet.paste(Image.open(os.path.join(COVERS, f"cover_{n}_512.png")), (x, y))
        _label(d, x, y + 516, [f"cover_{n}  512x512"], 22)
    sheet.save(os.path.join(REVIEW, "covers_512_contact_sheet.png"))
    # 60 — taille RÉELLE, jugement de lisibilité
    pad = 44
    sheet = Image.new("RGB", (6 * (60 + pad) + pad, 60 + 70 + 2 * pad), "#101012")
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        x = pad + i * (60 + pad)
        sheet.paste(Image.open(os.path.join(COVERS, f"cover_{n}_60.png")), (x, pad))
        _label(d, x - 6, pad + 66, [n], 14)
    sheet.save(os.path.join(REVIEW, "covers_60_contact_sheet.png"))


def main():
    os.makedirs(REVIEW, exist_ok=True)
    dbg_dir = os.path.join(REVIEW, "debug_safezones")
    os.makedirs(dbg_dir, exist_ok=True)
    bank = json.load(open(gs.BANK, encoding="utf-8"))
    facts = sv.load_facts()
    all_entries, hl_items, daily_items = [], [], []

    # --- Highlights : rendus pleins + debug ---
    for folder, seq, _ in SETS:
        out_dir = os.path.join(REVIEW, folder)
        os.makedirs(out_dir, exist_ok=True)
        frames = bank["highlights"][seq]["frames"]
        entries = gs.process_frames(frames, seq, out_dir, dry_run=False, facts=facts)
        all_entries += entries
        dbg = [dict(f, _debug=True) for f in frames]
        gs.process_frames(dbg, seq + "_debug", dbg_dir, dry_run=False, facts=facts)
        for e in entries:
            if e["render_status"] == "rendered":
                asset = os.path.basename((e["resolved_asset_path"] or "").split(";")[0]) or "-"
                hl_items.append((e["output_path"],
                                 [e["frame_id"] + "  " + e["template_id"],
                                  "1080x1920", "asset: " + asset]))

    # --- Familles quotidiennes rendables ---
    daily_dir = os.path.join(REVIEW, "daily_full")
    os.makedirs(daily_dir, exist_ok=True)
    for fam, model, pair in DAILIES:
        frames = bank["daily_families"][fam]["frames"]
        entries = gs.process_frames(frames, fam, daily_dir, dry_run=False, facts=facts,
                                    model=model, pair=pair)
        all_entries += entries
        gs.process_frames([dict(f, _debug=True) for f in frames], fam + "_debug",
                          dbg_dir, dry_run=False, facts=facts, model=model, pair=pair)
        for e in entries:
            if e["render_status"] == "rendered":
                asset = os.path.basename((e["resolved_asset_path"] or "").split(";")[0]) or "-"
                daily_items.append((e["output_path"],
                                    [fam, e["template_id"] + "  1080x1920",
                                     "asset: " + asset]))

    # --- Comparaison daylight A/B (mod_01, qua_02, model_of_day) ---
    cmp_dir = os.path.join(REVIEW, "_cmp")
    os.makedirs(cmp_dir, exist_ok=True)
    pairs = []
    mod01 = bank["highlights"]["models"]["frames"][0]
    qua02 = [f for f in bank["highlights"]["quality"]["frames"] if f["frame_id"] == "qua_02"][0]
    daym = gs._resolve_placeholders(bank["daily_families"]["model_of_day"]["frames"][0],
                                    model="eclipse")
    for tag, fr, framed_tpl in [("mod_01", mod01, "hero_model_framed"),
                                ("qua_02", qua02, "detail_macro_framed"),
                                ("day_model", daym, "hero_model_framed")]:
        photo = sv.photo_for_model(fr["model_id"])
        a = os.path.join(cmp_dir, f"{tag}_A_fullbleed.png")
        b = os.path.join(cmp_dir, f"{tag}_B_framed.png")
        sv.render_frame(fr, a, photo)
        sv.render_frame(dict(fr, template_id=framed_tpl), b, photo)
        pairs.append((tag, a, b))
    th = 700
    tw = int(th * 1080 / 1920)
    pad = 30
    W = 2 * (tw + pad) + pad
    H = len(pairs) * (th + 64 + pad) + pad
    sheet = Image.new("RGB", (W, H), "#101012")
    d = ImageDraw.Draw(sheet)
    for i, (tag, a, b) in enumerate(pairs):
        y = pad + i * (th + 64 + pad)
        sheet.paste(Image.open(a).convert("RGB").resize((tw, th), Image.LANCZOS), (pad, y))
        sheet.paste(Image.open(b).convert("RGB").resize((tw, th), Image.LANCZOS), (2 * pad + tw, y))
        _label(d, pad, y + th + 8, [f"{tag} — A full-bleed actuelle"], 20)
        _label(d, 2 * pad + tw, y + th + 8, [f"{tag} — B cadre Nocturne"], 20)
    sheet.save(os.path.join(REVIEW, "daylight_asset_comparison.png"))

    # --- Contact sheets ---
    contact_sheet(hl_items, os.path.join(REVIEW, "highlights_contact_sheet.png"))
    contact_sheet(daily_items, os.path.join(REVIEW, "daily_stories_contact_sheet.png"), cols=3)
    covers_sheets()

    # --- Manifeste + README ---
    with open(os.path.join(REVIEW, "manifest_review.json"), "w", encoding="utf-8") as f:
        json.dump({"frames": all_entries}, f, ensure_ascii=False, indent=2)
    open(os.path.join(REVIEW, "README.md"), "w", encoding="utf-8").write(
        "# Revue visuelle Stories V2\n\n"
        "- `highlights_contact_sheet.png` — MODÈLES x6, CHOISIR x4, QUALITÉ x1, FAQ x3 (ordre réel).\n"
        "- `daily_stories_contact_sheet.png` — Modèle du jour, Aide-moi à choisir, Détail réel.\n"
        "- `covers_512_contact_sheet.png` / `covers_60_contact_sheet.png` — juger la lisibilité sur le 60 px.\n"
        "- `daylight_asset_comparison.png` — A (full-bleed actuel) vs B (cadre Nocturne) sur 3 écrans.\n"
        "- `highlight_*_full/`, `faq_full/`, `quality_full/`, `daily_full/` — PNG individuels 1080x1920.\n"
        "- `debug_safezones/` — zones de sécurité (haut 220 / bas 280 / bande CTA / monogramme) + bounding boxes. NON publiables.\n"
        "- `manifest_review.json` — traçabilité complète (asset résolu, hash, dimensions, brand asset).\n")
    # --- Planche finale unique (sans debug) : 17 stories + 6 couvertures 60px ---
    tw = 216
    th = int(tw * 1920 / 1080)
    pad = 22
    cols = 6
    items = hl_items + daily_items
    rows = (len(items) + cols - 1) // cols
    W = cols * (tw + pad) + pad
    H = rows * (th + 58 + pad) + pad + 60 + 96
    sheet = Image.new("RGB", (W, H), "#0D0D0F")
    d = ImageDraw.Draw(sheet)
    for i, (p, lines) in enumerate(items):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), pad + r * (th + 58 + pad)
        sheet.paste(Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        _label(d, x, y + th + 6, lines[:2], 13)
    yc = pad + rows * (th + 58 + pad) + 16
    _label(d, pad, yc - 6, ["Couvertures (taille réelle 60 px) :"], 18)
    for i, n in enumerate(["models", "choose", "reviews", "quality", "shipping", "faq"]):
        sheet.paste(Image.open(os.path.join(COVERS, f"cover_{n}_60.png")), (pad + 240 + i * 100, yc - 16))
    sheet.save(os.path.join(REVIEW, "STORIES_V2_FINAL_REVIEW.png"))

    n_rendered = sum(1 for e in all_entries if e["render_status"] == "rendered")
    print(f"[review] rendus={n_rendered} bloqués={len(all_entries) - n_rendered} -> {REVIEW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
