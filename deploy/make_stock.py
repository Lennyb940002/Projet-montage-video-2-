# -*- coding: utf-8 -*-
"""Génère un lot de reels des 7 formats validés dans Downloads/stock_concepts/.
Rafale : déjà 20 prêts dans reels_fond_blanc/. Ici on produit les 6 autres formats.
Chaque config = on patche les globals du module puis on appelle main()."""
import os, sys, glob, importlib, traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK = r"C:\Users\zbull\Downloads\stock_concepts"
os.makedirs(STOCK, exist_ok=True)
os.environ["RAFALE_OUT"] = STOCK
sys.path.insert(0, REPO)

RO = r"C:\Users\zbull\Downloads\Royal Oak Or rose.mp4"
DAY = r"C:\Users\zbull\Downloads\Daytona Blue Saphire.mp4"


def gen(modname, configs):
    m = importlib.import_module("deploy." + modname)
    for cfg in configs:
        for k, v in cfg.items():
            setattr(m, k, v)
        try:
            m.main()
            print(f"OK {cfg['OUT_NAME']}")
        except Exception as e:
            print(f"FAIL {cfg.get('OUT_NAME')}: {e}")
            traceback.print_exc()


gen("make_reveal", [
    dict(CLAIM_CLIP=RO, REVEAL_FOLDER="Royal Oak", REVEAL_IMG_IDX=0, MUSIC="05",
         CLAIM=[("Tout le monde", "white"), ("pense que c'est", "white"), ("une AP", "yellow"), ("à 40 000€", "yellow")],
         OUT_NAME="stk_reveal_01.mp4"),
    dict(CLAIM_CLIP=RO, REVEAL_FOLDER="Royal Oak", REVEAL_IMG_IDX=0, MUSIC="07",
         CLAIM=[("Il croit avoir", "white"), ("une AP", "yellow"), ("à 40 000€", "yellow")],
         OUT_NAME="stk_reveal_02.mp4"),
])
gen("make_pov", [
    dict(CLIP=DAY, MUSIC="07", SETUP=[("POV :", "white"), ("tu dis à tout", "white"), ("le monde que", "white"), ("c'est une vraie", "yellow")],
         PUNCH="elle est à 195€", OUT_NAME="stk_pov_01.mp4"),
    dict(CLIP=RO, MUSIC="39", SETUP=[("Ton pote :", "white"), ("t'as claqué", "white"), ("40 000€ ??", "yellow")],
         PUNCH="195€ en vrai", OUT_NAME="stk_pov_02.mp4"),
    dict(CLIP=DAY, MUSIC="01", SETUP=[("Personne sait", "white"), ("que ma Rolex", "yellow"), ("est un mod", "white")],
         PUNCH="195€", OUT_NAME="stk_pov_03.mp4"),
])
gen("make_devine", [
    dict(TOP=("Daytona", 0), BOTTOM=("Datejust", 0), MUSIC="11", OUT_NAME="stk_devine_01.mp4"),
    dict(TOP=("Royal Oak", 0), BOTTOM=("Santos", 1), MUSIC="05", OUT_NAME="stk_devine_02.mp4"),
    dict(TOP=("Datejust", 0), BOTTOM=("Royal Oak", 0), MUSIC="39", OUT_NAME="stk_devine_03.mp4"),
])
gen("make_toi_moi", [
    dict(WATCH=("Royal Oak", 0), MUSIC="07", OUT_NAME="stk_toimoi_01.mp4"),
    dict(WATCH=("Daytona", 0), MUSIC="01", OUT_NAME="stk_toimoi_02.mp4"),
    dict(WATCH=("Datejust", 0), MUSIC="21", OUT_NAME="stk_toimoi_03.mp4"),
])
gen("make_personality", [
    dict(INTRO="intro_07.jpg", MUSIC="05", OUT_NAME="stk_perso_01.mp4"),
    dict(INTRO="intro_12.jpg", MUSIC="11", OUT_NAME="stk_perso_02.mp4"),
])
gen("make_thisorthat", [
    dict(TOP=("Daytona", 0), BOTTOM=("Santos", 1), MUSIC="01", OUT_NAME="stk_tot_01.mp4"),
    dict(TOP=("Royal Oak", 0), BOTTOM=("Datejust", 0), MUSIC="39", OUT_NAME="stk_tot_02.mp4"),
    dict(TOP=("Santos", 1), BOTTOM=("Daytona", 0), MUSIC="05", OUT_NAME="stk_tot_03.mp4"),
])

print("TOTAL stock_concepts:", len(glob.glob(os.path.join(STOCK, "*.mp4"))))
