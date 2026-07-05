import os

FFMPEG_BIN = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

# Banque de clips muets par défaut (modifiable depuis l'UI plus tard)
DEFAULT_CLIPS_DIR = r"C:\Users\User\Downloads\Voix off\Clips\Muet"

WHISPER_MODEL = "small"

VIDEO = dict(width=1080, height=1920, fps=30, zoom=1.30)
SILENCE = dict(keep=0.12, below_peak=33, floor_min=-55, floor_max=-28)
DETECT = dict(fuzzy_ratio=0.82, pause_min=0.7)
SUBS = dict(font="Arial Black", size=84, maxwords=3,
            yellow="&H0000FFFF&", white="&H00FFFFFF&")

WORKDIR = os.path.join(os.path.expanduser("~"), ".automontage", "work")
os.makedirs(WORKDIR, exist_ok=True)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(PROJECT_ROOT, "SFX")

BOOST = dict(
    hook_dur=3.5,      # durée du hook (s)
    hook_cut=0.8,      # longueur d'un cut dans le hook (s)
    sfx_volume=0.7,    # volume des SFX dans le mix
    flash=0.12,        # durée du flash blanc (s)
    punch_zoom=1.5,    # zoom (constant) plus serré sur le 1er clip = effet punch
)

EMPHASIS = dict(active_scale=130, kw_active_scale=152, kw_idle_scale=116,
                accent="&H0000FFFF&", kw_outline=6)
MOTION = dict(kenburns_zoom=1.10, punch_zoom=1.16, shake_px=10, zoom_period=2.5)
TRANSITIONS = dict(dur=0.12, default_type="fade")

# --- Musique de fond + Ducking (V1) -----------------------------------------
MUSIC_DIR = os.path.join(PROJECT_ROOT, "MUSIC")
MUSIC = dict(
    base_gain_dB=-22.0,
    max_base_gain_dB=-16.0,         # plafond dur : musique JAMAIS au-dessus
    duck_depth_dB=-12.0,            # creux ducking pendant la voix
    fade_in_ms=800,
    fade_out_ms=1200,
    pre_cta_gap_s=1.2,
    pre_cta_fade_out_ms=250,
    pre_cta_fade_in_ms=200,
    target_lufs=-16.0,
    voice_dominance_min_dB=6.0,
    voice_floor_below_voice_dB=14.0,   # plancher : musique au moins X dB sous voix
    category_default="luxury",
    confidence_threshold=0.60,
    auto_fix_step_dB=-2.0,           # pas d'auto-fix (1 seule itération)
    min_track_duration_s=45.0,
    # --- Mastering V1 (ffmpeg loudnorm sur le mix final) ---
    master_lufs_target=-16.0,   # cible TikTok/Reels ; None pour désactiver le mastering
    master_lra=11.0,
    master_true_peak=-2.0,        # (réservé V2 loudnorm) marge anti-clipping AAC
    master_tolerance_dB=1.5,    # ± autour du target = succès (1.0)
    master_warn_dB=3.0,         # ± = avertissement (0.5)
    master_dominance_tolerance_dB=2.0,  # delta max acceptable sur dominance
)

DEFAULT_CTA = "Écris-moi en commentaire 👇"
BASE_HASHTAGS = ["#montre", "#montrehomme", "#seikomod", "#horlogerie", "#watch",
                 "#watchlover", "#pourtoi", "#fyp", "#luxe", "#style"]
DEFAULT_BENEFITS = ["✅ Qualité qui en jette", "✅ Prix accessible", "✅ Livraison rapide"]
BENEFIT_KEYWORDS = ["prix", "qualité", "livraison", "saphir", "acier", "24h", "€",
                    "euro", "garantie", "automatique", "mouvement", "bracelet", "cadran"]
BRAND_TAGS = {"rolex": "#rolex", "omega": "#omega", "cartier": "#cartier",
              "seiko": "#seiko", "patek": "#patek", "audemars": "#audemarspiguet",
              "tissot": "#tissot", "tag": "#tagheuer", "heuer": "#tagheuer",
              "daytona": "#daytona", "submariner": "#submariner", "datejust": "#datejust"}

# --- Silent Content Engine (V1) --------------------------------------------
SILENT = dict(
    width=1080, height=1920, fps=30,
    min_duration=3.0, max_duration=8.0,
    window_n=5,                 # sliding history window read by the Policy
    w_rep=0.30,                 # repetition bias weight
    w_pat=0.40,                 # ABAB pattern penalty weight
    temperature=0.7,            # softmax temperature (fixed in V1)
    base_score=1.0,
    reveal_blur_sigma=25,       # gblur sigma for the "reveal" layout
    reveal_at=2.0,              # when the de-blur starts (s)
    reveal_fade=0.6,            # de-blur fade duration (s)
    fonts=["Arial Black", "Impact"],
    accents=["&H0000FFFF&", "&H0000FF00&", "&H00FFFFFF&", "&H009314FF&"],
    text_anims=["fade", "pop"],
    # Banque vidéo des mannequins/montres (clips Kling, sous-dossiers par modèle)
    clips_dir=r"C:\Users\User\Downloads\Montage video\Banque video",
    # De-watermark : efface le logo "KlingAI" via delogo (interpolation des
    # pixels voisins) -> PAS de zoom/décalage, la montre reste CENTRÉE.
    # box = (x, y, w, h) en fractions de l'image (coin bas-droite).
    dewatermark=dict(enabled=True, box=(0.68, 0.88, 0.30, 0.11)),
    # Nom + couleur du cartouche par modèle (couleur ASS &H00BBGGRR ≈ couleur montre)
    models={
        "Rainbow Or rose": {"name": "Seiko Daytona Or rose", "color": "&H00C828E6&"},
        "Rainbow saphire": {"name": "Seiko Daytona Saphir",  "color": "&H00DC503C&"},
        "Rainbow ruby":    {"name": "Seiko Daytona Ruby",    "color": "&H003C1EDC&"},
        "Rainbow silver":  {"name": "Seiko Daytona Silver",  "color": "&H00B0A89C&"},
        "GMT":             {"name": "Seiko GMT",             "color": "&H00C87A2A&"},
    },
    model_default={"name": "Montre", "color": "&H00707070&"},
    # Dossier de concepts (hooks/CTA/règles) édité par l'utilisateur : source de
    # vérité des textes. L'app le parse ; fallback sur les JSON si absent.
    concepts_file=r"C:\Users\User\Downloads\Montage video\DOSSIER_CONCEPTS.md",
    # Rollback reels 1A (2026-07-05) : les 5 formats du guide servent leurs hooks
    # via les banques JSON dédiées (backend/silent/banks/). Plus aucune mécanique
    # ne tape dans le DOSSIER_CONCEPTS -> l'ancien contenu ne peut plus ressortir.
    mechanic_concept={},
    # Biais par mécanique (stratégie data-driven 22/06, cf docs/STRATEGIE_CONTENU_VIDEO.md).
    # Multiplie le poids softmax. Défaut = 1.0 si absent. 0.0 = banni (retiré).
    # Mix cible (copywriter) : 60% identité / 20% décision / 15% projection / 5% duel.
    mechanic_bias={
        # --- Formats 1A (guide 2026-07-05) ---
        "test": 3.0,               # identité
        "revelation_psy": 2.5,     # révélation psychologique
        "trahison": 2.0,           # ton choix te trahit
        "perception": 1.5,         # ce que ta montre dit aux autres
        "test_perso": 1.0,         # test rapide
        # --- BANNIS (guide : reels génériques) ---
        "elimination": 0.0, "vote": 0.0, "comparison": 0.0, "comparison_4": 0.0,
        "revelation": 0.0, "top3": 0.0, "collection": 0.0, "collection_4": 0.0,
        "battle": 0.0, "pov": 0.0, "erreur": 0.0, "transformation": 0.0,
        "projection": 0.0,         # reporté en Phase 1B
    },
    # Bed musical : l'utilisateur dépose ses sons ici (baked dans le MP4).
    music_dir=r"C:\Users\User\Downloads\Montage video\Musique",
    music_gain_db=-8.0,        # pas de voix à couvrir -> son présent mais pas saturé
    music_fade_out_s=0.8,
)
SILENT_DB = os.path.join(os.path.expanduser("~"), ".automontage", "silent.db")

# --- Architecture de contenu V2 (7 familles) — source unique famille->mécanique.
# objective = objectif PRINCIPAL unique de la famille ; cta_type = CTA principal.
# Un seul objectif par vidéo (cf docs/BRANDING_V2.md). Révisable.
FAMILIES_V2 = {
    "miroir":      {"mechanic": "test",           "objective": "profil",       "cta_type": "profile_visit", "visual_layout": "sequence_3"},
    "choix_force": {"mechanic": "elimination",    "objective": "commentaire",  "cta_type": "comment",       "visual_layout": "sequence_3"},
    "projection":  {"mechanic": "projection",     "objective": "save",         "cta_type": "save",          "visual_layout": "sequence_2"},
    "bascule":     {"mechanic": "transformation", "objective": "save",         "cta_type": "save",          "visual_layout": "sequence_2"},
    "revelation":  {"mechanic": "revelation",     "objective": "retention",    "cta_type": "profile_visit", "visual_layout": "reveal"},
    "conseil":     {"mechanic": "conseil",        "objective": "dm",           "cta_type": "dm_choix",      "visual_layout": "sequence_2"},
    "preuve":      {"mechanic": "preuve",         "objective": "confiance",    "cta_type": "proof_action",  "visual_layout": "reveal"},
}

# CTA autorisés par famille (un concept choisit UN seul type dans cet ensemble).
FAMILY_ALLOWED_CTA = {
    "miroir": {"profile_visit"}, "choix_force": {"comment"},
    "projection": {"save", "share"}, "bascule": {"save"},
    "revelation": {"profile_visit"}, "conseil": {"dm_choix"}, "preuve": {"proof_action"},
}

# --------------------------------------------------------------------------- #
# POSTS VALEUR (carrousels éducatifs Flowers Chrome — image, pas vidéo)
# --------------------------------------------------------------------------- #
POSTS = dict(
    # Fichier des sujets, DANS le projet (part sur Oracle avec le code).
    topics_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts", "sujets_valeur.txt"),
    # 2 carrousels/jour, coloris alternés (rotation dark -> light -> pink).
    slots=[12, 18],
    colorways=["dark", "light"],   # rose retiré : noir / blanc en alternance
    # anti-répétition : un sujet ne revient pas avant N posts.
    topic_cycle=30,
    width=1080, height=1350,
)
POSTS_DB = os.path.join(os.path.expanduser("~"), ".automontage", "posts.db")

# --------------------------------------------------------------------------- #
# POSTS PHOTO RÉELS (photos produit, 3/jour matin/aprèm/soir — IG seulement)
# --------------------------------------------------------------------------- #
PHOTOS = dict(
    dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "Photo réel"),
    slots=[(9, 0), (14, 0), (20, 0)],   # matin / après-midi / soir
)
