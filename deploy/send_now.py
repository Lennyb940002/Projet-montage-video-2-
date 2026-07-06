#!/usr/bin/env python3
"""Génère UNE vidéo et l'envoie sur Telegram pour validation MAINTENANT, SANS
auto-post (pas de timeout). Utile quand le PC va être éteint : la vidéo attend
sagement ton ✅. Au réveil : relance le bot (bouton bureau) puis appuie sur ✅.

Usage : python deploy/send_now.py [engagement|retention]
"""
import asyncio
import random
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from backend import settings
from backend.distribution import orchestrator

_BUTTONS = InlineKeyboardMarkup([[
    InlineKeyboardButton("✅ Publier", callback_data="approve"),
    InlineKeyboardButton("❌ Skip", callback_data="skip"),
    InlineKeyboardButton("🔄 Refaire", callback_data="regenerate"),
]])


async def _send(token, chat, video_path, caption, pid):
    bot = Bot(token)
    with open(video_path, "rb") as f:
        await bot.send_video(chat_id=chat, video=f,
                             caption=(caption[:980] + f"\n#{pid}"),
                             reply_markup=_BUTTONS)


def main():
    goal = sys.argv[1] if len(sys.argv) > 1 else "engagement"
    s = settings.load()
    token, chat = s.get("telegram_bot_token"), s.get("telegram_chat_id")
    if not (token and chat):
        print("[send_now] Telegram non configuré.")
        return 1
    res = orchestrator.generate_for_slot(goal=goal, seed=random.randrange(10 ** 9))
    print(f"[send_now] vidéo #{res['pid']} générée ({goal}) — envoi Telegram…")
    asyncio.run(_send(token, chat, res["video_path"], res["caption"], res["pid"]))
    print(f"[send_now] ✅ envoyée. En attente de TON ✅ (pas d'auto-post).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
