# -*- coding: utf-8 -*-
"""Lot 5 concepts : grille (calcul absurde) + 4 variantes texte via make_breakdown."""
import os, sys, importlib, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def bd(cfg):
    B = importlib.import_module("deploy.make_breakdown")
    for k, v in cfg.items():
        setattr(B, k, v)
    try:
        B.main(); print(f"OK {cfg['OUT_NAME']}")
    except Exception as e:
        print(f"FAIL {cfg['OUT_NAME']}: {e}"); traceback.print_exc()


try:
    importlib.import_module("deploy.make_grid").main(); print("OK grid_test.mp4")
except Exception as e:
    print("FAIL grid:", e); traceback.print_exc()

bd(dict(WATCH=("Datejust", 0), MUSIC="07", OUT_NAME="voient_test.mp4",
        TOP="Ce qu'ils voient : un mec riche",
        LINES=[("La réalité :", "ink"), ("malin, pas radin", "green")], PRICE="195€"))
bd(dict(WATCH=("Daytona", 0), MUSIC="01", OUT_NAME="hottake_test.mp4",
        TOP="Unpopular opinion :",
        LINES=[("Payer 40 000€", "red"), ("c'est se faire avoir", "red"), ("saphir + NH35", "green")], PRICE="195€"))
bd(dict(WATCH=("Royal Oak", 0), MUSIC="11", OUT_NAME="objection_test.mp4",
        TOP="« C'est du fake » ?",
        LINES=[("Fake ? Non.", "green"), ("Cheap ? Saphir.", "green"), ("Toc ? NH35 auto.", "green")], PRICE="195€"))
bd(dict(WATCH=("Santos", 1), MUSIC="39", OUT_NAME="vraiflex_test.mp4",
        TOP="Le vrai flex en 2026 :",
        LINES=[("pas payer 40 000€", "red"), ("le même look", "ink"), ("+ garder ton argent", "green")], PRICE="195€"))
print("FINI")
