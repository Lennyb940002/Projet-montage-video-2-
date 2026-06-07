import os

FFMPEG_BIN = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

# Banque de clips muets par défaut (modifiable depuis l'UI plus tard)
DEFAULT_CLIPS_DIR = r"C:\Users\User\Downloads\Voix off\Clips\Muet"

WHISPER_MODEL = "small"

VIDEO = dict(width=1080, height=1920, fps=30, zoom=1.30)
SILENCE = dict(keep=0.10, threshold="-35dB")
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
