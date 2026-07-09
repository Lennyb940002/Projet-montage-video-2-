# -*- coding: utf-8 -*-
"""Génère les 10 concepts DM/conversion dans rafale_out/ (dm_*.mp4)."""
import os, sys, importlib, traceback
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
G = (37, 211, 102); RED = (224, 16, 43); BLUE = (59, 130, 246); PUR = (147, 51, 234)


def run(modname, cfg):
    m = importlib.import_module("deploy." + modname)
    for k, v in cfg.items():
        setattr(m, k, v)
    try:
        m.main(); print(f"OK {cfg.get('OUT_NAME', modname)}")
    except Exception as e:
        print(f"FAIL {cfg.get('OUT_NAME', modname)}: {e}"); traceback.print_exc()


# --- 7 génériques (make_dm) ---
DM = [
 dict(WATCH=("Royal Oak", 0), HOOK=[("Le prix de", "ink"), ("cette montre", "ink"), ("va te choquer", "red")],
      CTA="Commente PRIX", CTA_COLOR=G, MUSIC="05", OUT_NAME="dm_01_prix_cache.mp4"),
 dict(WATCH=("Daytona", 0), HOOK=[("Ce modèle", "ink"), ("il en reste", "ink"), ("QUE 2", "red")],
      CTA="DM « DERNIÈRE »", CTA_COLOR=RED, MUSIC="01", OUT_NAME="dm_02_reste2.mp4"),
 dict(WATCH=("Datejust", 0), HOOK=[("-20% pour", "ink"), ("les 20 premiers", "red"), ("en DM", "ink")],
      CTA="DM « FLOWERS »", CTA_COLOR=BLUE, MUSIC="39", OUT_NAME="dm_03_code.mp4"),
 dict(WATCH=("Royal Oak", 0), HOOK=[("Quelle montre", "ink"), ("est faite", "ink"), ("pour TOI ?", "red")],
      CTA="DM « MOI »", CTA_COLOR=PUR, MUSIC="07", OUT_NAME="dm_05_quiz.mp4"),
 dict(WATCH=("Santos", 1), HOOK=[("Pas encore", "ink"), ("sur le site", "red")],
      CTA="DM « DROP »", CTA_COLOR=G, MUSIC="11", OUT_NAME="dm_06_drop.mp4"),
 dict(WATCH=("Royal Oak", 0), HOOK=[("Vraie Rolex", "ink"), ("ou mod", "ink"), ("à 195€ ?", "red")],
      CTA="DM ta réponse", CTA_COLOR=G, MUSIC="21", OUT_NAME="dm_09_vraiemod.mp4"),
 dict(WATCH=("Daytona", 0), HOOK=[("Je supprime", "ink"), ("ce post", "ink"), ("dans 24h", "red")],
      CTA="DM « STOCK »", CTA_COLOR=RED, MUSIC="05", OUT_NAME="dm_10_supprime.mp4"),
]
for c in DM:
    run("make_dm", c)

# --- #7 Reveal, CTA = commente LIEN ---
run("make_reveal", dict(MUSIC="07", CTA="Commente LIEN", OUT_NAME="dm_07_reveal_lien.mp4"))

# --- #4 Devine, réponse en DM ---
run("make_devine", dict(TOP=("Daytona", 0), BOTTOM=("Datejust", 0), MUSIC="11",
                        REVEAL="DM « PRIX »", OUT_NAME="dm_04_devine.mp4"))

# --- #8 Réponse à un commentaire ---
run("make_comment_reply", dict(OUT_NAME="dm_08_commentreply.mp4"))

import glob
print("TOTAL dm:", len(glob.glob(os.path.join(os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out"), "dm_*.mp4"))))
