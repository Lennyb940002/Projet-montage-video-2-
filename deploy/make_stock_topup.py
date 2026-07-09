# -*- coding: utf-8 -*-
"""Complément de stock pour le planning optimisé (moins de Rafale, plus de
conversion). +2 Reveal, +2 Personnalité, +2 This or that, +1 Devine."""
import os, sys, glob, importlib, traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK = r"C:\Users\zbull\Downloads\stock_concepts"
os.makedirs(STOCK, exist_ok=True)
os.environ["RAFALE_OUT"] = STOCK
sys.path.insert(0, REPO)
RO = r"C:\Users\zbull\Downloads\Royal Oak Or rose.mp4"


def gen(modname, configs):
    m = importlib.import_module("deploy." + modname)
    for cfg in configs:
        for k, v in cfg.items():
            setattr(m, k, v)
        try:
            m.main(); print(f"OK {cfg['OUT_NAME']}")
        except Exception as e:
            print(f"FAIL {cfg.get('OUT_NAME')}: {e}"); traceback.print_exc()


gen("make_reveal", [
    dict(CLAIM_CLIP=RO, REVEAL_FOLDER="Royal Oak", REVEAL_IMG_IDX=0, MUSIC="39",
         CLAIM=[("Il pense que", "white"), ("c'est une AP", "yellow"), ("à 50 000€", "yellow")],
         OUT_NAME="stk_reveal_03.mp4"),
    dict(CLAIM_CLIP=RO, REVEAL_FOLDER="Royal Oak", REVEAL_IMG_IDX=0, MUSIC="11",
         CLAIM=[("Sa montre de", "white"), ("rappeur", "yellow"), ("à 45 000€", "yellow")],
         OUT_NAME="stk_reveal_04.mp4"),
])
gen("make_personality", [
    dict(INTRO="intro_03.jpg", MUSIC="07", OUT_NAME="stk_perso_03.mp4"),
    dict(INTRO="intro_16.jpg", MUSIC="39", OUT_NAME="stk_perso_04.mp4"),
])
gen("make_thisorthat", [
    dict(TOP=("Datejust", 0), BOTTOM=("Daytona", 0), MUSIC="07", OUT_NAME="stk_tot_04.mp4"),
    dict(TOP=("Royal Oak", 0), BOTTOM=("Santos", 1), MUSIC="11", OUT_NAME="stk_tot_05.mp4"),
])
gen("make_devine", [
    dict(TOP=("Santos", 1), BOTTOM=("Datejust", 0), MUSIC="01", OUT_NAME="stk_devine_04.mp4"),
])
print("TOTAL stock_concepts:", len(glob.glob(os.path.join(STOCK, "*.mp4"))))
