"""Pack d'assets avatar Flowers Chrome depuis le master validé.
NE MODIFIE PAS la géométrie du monogramme — resize Lanczos + masque alpha propre.

Sort : fc_avatar_512/180/48.png, fc_monogram_transparent.png (fond noir retiré
par masque luminance avec antialiasing, couleurs dé-prémultipliées pour éviter
tout halo sombre), manifest.json (dims + sha1 de chaque fichier)."""
import hashlib
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.abspath(os.path.join(HERE, "..", "assets", "avatar"))
SRC = os.path.join(DIR, "fc_avatar_master.png")
SIZES = {"fc_avatar_512.png": 512, "fc_avatar_180.png": 180, "fc_avatar_48.png": 48}


def _sha1(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:16]


def make_transparent(img):
    """Monogramme chrome-sur-noir -> RGBA transparent. alpha = luminance ;
    RGB dé-prémultiplié (rgb/alpha) pour des bords antialiasés sans halo."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    lum = a.max(axis=2)                                  # le métal est neutre -> max canal
    alpha = np.clip(lum * 1.06, 0, 255)                  # léger boost, garde l'antialias
    safe = np.maximum(alpha, 1.0)[..., None]
    rgb = np.clip(a * 255.0 / safe, 0, 255)
    out = np.dstack([rgb, alpha]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def main():
    if not os.path.isfile(SRC):
        print(f"[avatar] master introuvable : {SRC}")
        return 1
    img = Image.open(SRC).convert("RGBA")
    w, h = img.size
    if w != h:
        s = min(w, h)
        img = img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
    for name, sz in SIZES.items():
        img.resize((sz, sz), Image.LANCZOS).save(os.path.join(DIR, name))
    trans = make_transparent(img)
    tpath = os.path.join(DIR, "fc_monogram_transparent.png")
    trans.save(tpath)
    # contrôle halo : composite sur #070707 vs master -> écart max
    bg = Image.new("RGBA", trans.size, "#070707")
    comp = Image.alpha_composite(bg, trans).convert("RGB")
    diff = np.abs(np.asarray(comp, np.int16) - np.asarray(img.convert("RGB"), np.int16))
    halo = int(diff.max())
    manifest = {}
    for name in ["fc_avatar_master.png", *SIZES, "fc_monogram_transparent.png"]:
        p = os.path.join(DIR, name)
        with Image.open(p) as im:
            manifest[name] = {"width": im.size[0], "height": im.size[1], "sha1": _sha1(p)}
    manifest["_halo_check_max_diff"] = halo   # < ~12 = aucun halo visible
    with open(os.path.join(DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[avatar] pack OK — halo max diff = {halo} (seuil visuel ~12)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
