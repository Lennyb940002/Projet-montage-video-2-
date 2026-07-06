"""Test one-shot : rend le carrousel de référence dans les 3 coloris et les
envoie sur Telegram en 3 albums. (Aucun post Instagram — juste un aperçu.)"""
import asyncio
import os
from telegram import Bot, InputMediaPhoto
from telegram.request import HTTPXRequest
from backend import settings
from backend.posts.carousel import render_carousel, REFERENCE_CONTENT

LABELS = {"dark": "🖤 Coloris 1 — Fond noir / écriture blanche",
          "light": "🤍 Coloris 2 — Fond blanc / écriture noire",
          "pink": "🩷 Coloris 3 — Fond rose / écriture blanche"}


def render_all():
    """Rend les 3 coloris (SYNC, hors boucle asyncio)."""
    out = os.path.join(os.path.expanduser("~"), "carousel_test")
    return {theme: render_carousel(REFERENCE_CONTENT, theme=theme, out_dir=out, prefix="ref")
            for theme in ("dark", "light", "pink")}


async def send(rendered):
    s = settings.load()
    token, chat = s.get("telegram_bot_token"), s.get("telegram_chat_id")
    req = HTTPXRequest(read_timeout=90, write_timeout=90, connect_timeout=30, pool_timeout=30)
    bot = Bot(token, request=req)
    await bot.send_message(chat_id=chat,
                           text="🧪 TEST carrousel valeur « Pourquoi cette montre "
                                "vaut son prix » — 3 coloris à valider :")
    for theme in ("dark", "light", "pink"):
        media = []
        for i, p in enumerate(rendered[theme]):
            cap = LABELS[theme] if i == 0 else None
            media.append(InputMediaPhoto(open(p, "rb"), caption=cap))
        await bot.send_media_group(chat_id=chat, media=media)
    await bot.send_message(chat_id=chat,
                           text="Dis-moi quel(s) coloris tu valides (ou ce qu'on ajuste).")


if __name__ == "__main__":
    _rendered = render_all()          # sync d'abord
    asyncio.run(send(_rendered))      # async ensuite
