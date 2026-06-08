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
