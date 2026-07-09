# -*- coding: utf-8 -*-
"""Lot des nouveaux concepts prêts sans tournage : iMessage, breakdown,
types de mecs, cadeau."""
import os, sys, importlib, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(modname, cfg=None):
    m = importlib.import_module("deploy." + modname)
    for k, v in (cfg or {}).items():
        setattr(m, k, v)
    try:
        m.main(); print(f"OK {modname} {cfg.get('OUT_NAME','') if cfg else ''}")
    except Exception as e:
        print(f"FAIL {modname}: {e}"); traceback.print_exc()


run("make_imessage")
run("make_breakdown")
run("make_personality", dict(
    INTRO="intro_05.jpg", MUSIC="21", OUT_NAME="typesdemecs_test.mp4",
    HOOK=[("Le type de mec", "white"), ("selon", "white"), ("sa montre", "yellow"), ("part 1", "white")],
    TRAITS=[("Royal Oak", 0, "il se prend pour un trader"),
            ("Daytona", 0, "il va vite en tout"),
            ("Datejust", 0, "le mec safe, zéro risque"),
            ("Santos", 1, "il sort du lot, il assume")]))
run("make_dm", dict(
    WATCH=("Royal Oak", 0), MUSIC="05", OUT_NAME="cadeau_test.mp4",
    HOOK=[("Le cadeau qui", "ink"), ("te fait passer", "ink"), ("pour un boss", "red")],
    CTA="195€ · DM « CADEAU »", CTA_COLOR=(15, 169, 88)))

import glob
d = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
print("faits:", [os.path.basename(x) for x in glob.glob(os.path.join(d, "*_test.mp4"))
                 if any(n in x for n in ("imessage", "breakdown", "typesdemecs", "cadeau"))])
