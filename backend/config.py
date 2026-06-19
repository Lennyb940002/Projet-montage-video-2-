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
)
SILENT_DB = os.path.join(os.path.expanduser("~"), ".automontage", "silent.db")
