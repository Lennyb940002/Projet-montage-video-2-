# -*- coding: utf-8 -*-
"""Batch de reels voix-off orientés PROSPECT (retour terrain 2026-07-23 : le script
« appel direct à envoyer sa photo/idée » convertit ; les scripts 'brand' font de
l'engagement mais peu de DM). Répartit les clips en round-robin -> chaque vidéo a
des extraits différents (anti-répétition inter-vidéos, dans la limite des 26 clips).

Usage : python deploy/generate_vo_batch.py [n]   (n reels, défaut 7)
Sortie : stock/vo_reel_NN_<script>.mp4 + stock/_vo_reels.json
"""
import sys, os, glob, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import make_full_video as M, voice_scripts
from backend.config import SILENT

# scripts à CTA direct (envoie ta photo / ton idée / ton budget) -> prospects
SCRIPTS = ["faisable", "ton_idee", "budget_200", "cadeau", "processus", "atelier", "erreur"]
CLIPS_DIR = SILENT["clips_dir"]


def clip_pool(rng):
    allc = glob.glob(os.path.join(CLIPS_DIR, "*", "*.mp4"))
    rng.shuffle(allc)
    return allc


def clips_for(pool, i, n=8):
    """8 clips de la vidéo i, en round-robin sur le pool -> peu de recoupement
    entre vidéos consécutives (cycle si le pool est plus petit que i*n)."""
    return [pool[(i * n + k) % len(pool)] for k in range(n)]


def main(n=7, seed=1):
    rng = random.Random(seed)
    pool = clip_pool(rng)
    names = (SCRIPTS * ((n // len(SCRIPTS)) + 1))[:n]
    done = []
    for i, name in enumerate(names):
        sc = voice_scripts.get(name)
        out = os.path.join("stock", f"vo_reel_{i + 1:02d}_{name}.mp4")
        try:
            M.make_full(sc["vo"], out, voice="Charon", cta=sc.get("cta"),
                        clips=clips_for(pool, i), seed=1000 + i)
            done.append({"fichier": os.path.basename(out), "script": name,
                         "cta": sc.get("cta"), "hook": sc.get("hook")})
            print(f"OK {i + 1} {name}", flush=True)
        except Exception as e:
            print(f"STOP {name}: {str(e)[:100]}", flush=True)
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("QUOTA EPUISE apres", len(done), "reels"); break
    json.dump(done, open("stock/_vo_reels.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("TOTAL:", len(done))
    return done


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
