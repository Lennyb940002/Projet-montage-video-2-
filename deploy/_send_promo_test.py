"""Test : rend des stories PROMO (fond blanc, prix barré 195->179) pour quelques
photos réelles et les envoie sur Telegram pour validation."""
import asyncio
import os

from telegram import Bot, InputMediaPhoto
from telegram.request import HTTPXRequest
from backend import settings
from backend.config import PHOTOS
from backend.posts.story import render_promo_story

PICK = ["photo_01", "photo_03", "photo_08", "photo_10"]   # gmt / saphir / ruby / or_rose


def render_all():
    out = os.path.join(os.path.expanduser("~"), "promo_test")
    paths = []
    for name in PICK:
        src = os.path.join(PHOTOS["dir"], name + ".jpeg")
        dst = os.path.join(out, name + "_promo.png")
        render_promo_story(dst, src, "195 €", "179 €")
        paths.append(dst)
    return paths


async def send(paths):
    s = settings.load()
    req = HTTPXRequest(read_timeout=120, write_timeout=120, connect_timeout=30, pool_timeout=30)
    bot = Bot(s["telegram_bot_token"], request=req)
    await bot.send_message(chat_id=s["telegram_chat_id"],
                           text="🧪 TEST stories PROMO D'ÉTÉ (fond blanc, 195€ barré → 179€). "
                                "Valide le style ?")
    media = [InputMediaPhoto(open(p, "rb")) for p in paths]
    await bot.send_media_group(chat_id=s["telegram_chat_id"], media=media)


if __name__ == "__main__":
    _paths = render_all()
    asyncio.run(send(_paths))
    print("envoyé :", len(_paths))
