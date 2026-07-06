"""One-shot : envoie le carrousel sur Telegram + publie sur Instagram & TikTok."""
import asyncio
import os
from telegram import Bot, InputMediaPhoto
from telegram.request import HTTPXRequest
from backend import settings
from backend.distribution import uploadpost
from backend.posts.store import PostsStore
from backend.config import POSTS_DB

TOPIC = "Automatique ou quartz : laquelle choisir ?"
COLORWAY = "dark"
PLATFORMS = ["instagram", "tiktok"]
# TikTok limite le titre à 90 caractères -> version courte dédiée.
TIKTOK_TITLE = "Automatique ou quartz ? La vraie différence ⚙️ #seikomod #flowerschrome"

CAPTION = (
    "⚙️ Automatique ou quartz : le débat qui revient tout le temps.\n\n"
    "La vraie différence n'est pas le prix — c'est ce qu'il se passe à l'intérieur. "
    "Le quartz fonctionne à la pile : précis, pratique, mais jetable. L'automatique se "
    "remonte avec les mouvements de ton poignet : pas de pile, une trotteuse qui balaie "
    "le cadran, et un mécanisme qui se répare et se transmet.\n\n"
    "Chez Flowers Chrome, chaque pièce embarque un mouvement automatique japonais reconnu "
    "— fiable, réparable, fait pour durer des années. Une montre qui vit tant que tu la portes.\n\n"
    "📩 Une question, un projet sur-mesure, une commande → DM ouverts.\n\n"
    "#seikomod #montreautomatique #montrehomme #horlogerie #watchesofinstagram #flowerschrome"
)


def _paths():
    d = os.path.join(os.path.expanduser("~"), "value_post_today")
    return [os.path.join(d, f"post_{COLORWAY}_{i:02d}.png") for i in range(1, 6)]


async def _telegram(paths):
    s = settings.load()
    req = HTTPXRequest(read_timeout=120, write_timeout=120, connect_timeout=30, pool_timeout=30)
    bot = Bot(s["telegram_bot_token"], request=req)
    media = [InputMediaPhoto(open(p, "rb"), caption=(CAPTION if i == 0 else None))
             for i, p in enumerate(paths)]
    await bot.send_media_group(chat_id=s["telegram_chat_id"], media=media)
    print("[telegram] album envoyé")


def main():
    import sys
    paths = _paths()
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print("[ERREUR] PNG manquants:", missing); return 1

    # 1) copie Telegram (sauf --no-telegram, déjà envoyée)
    if "--no-telegram" not in sys.argv:
        asyncio.run(_telegram(paths))

    # 2) publication IG + TikTok
    s = settings.load()
    res = uploadpost.post_photos(paths, CAPTION, PLATFORMS,
                                 user=s.get("uploadpost_user", ""),
                                 token=s.get("uploadpost_token", ""),
                                 platform_titles={"tiktok": TIKTOK_TITLE})
    print("[uploadpost]", res)

    # 3) journal
    store = PostsStore(POSTS_DB)
    status = "posted" if res.get("ok") else "failed"
    store.insert(TOPIC, COLORWAY, caption=CAPTION, n_slides=len(paths), status=status)
    print("[store] enregistré, statut =", status)
    return 0 if res.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
