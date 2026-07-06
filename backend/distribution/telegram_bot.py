"""Bot Telegram : envoie la vidéo pour validation (boutons ✅/❌/🔄), gère les
callbacks et le timeout 30 min. Long-polling (OK sur VM always-on)."""
import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import NetworkError, TimedOut
from telegram.ext import Application, CallbackQueryHandler
from backend import settings
from backend.distribution import orchestrator

_log = logging.getLogger("automontage.telegram")

APPROVAL_TIMEOUT_S = 30 * 60

_BUTTONS = InlineKeyboardMarkup([[
    InlineKeyboardButton("✅ Publier", callback_data="approve"),
    InlineKeyboardButton("❌ Skip", callback_data="skip"),
    InlineKeyboardButton("🔄 Refaire", callback_data="regenerate"),
]])


def _cfg():
    s = settings.load()
    return s.get("telegram_bot_token"), s.get("telegram_chat_id")


async def send_for_approval(app, pid, video_path, caption):
    """Envoie la vidéo + boutons. Programme le timeout -> post auto. Le pid est
    encodé en fin de légende (#<pid>) pour être retrouvé au callback."""
    _, chat_id = _cfg()
    with open(video_path, "rb") as f:
        msg = await app.bot.send_video(chat_id=chat_id, video=f,
                                       caption=(caption[:980] + f"\n#{pid}"),
                                       reply_markup=_BUTTONS)
    app.job_queue.run_once(_on_timeout, APPROVAL_TIMEOUT_S, data=pid, name=f"to_{pid}")
    return msg.message_id


async def _on_timeout(context):
    await asyncio.to_thread(orchestrator.decide_and_post, context.job.data, "timeout")


def _pid_from_message(message):
    import re
    m = re.search(r"#(\d+)\s*$", message.caption or "")
    return int(m.group(1)) if m else None


async def _on_callback(update, context):
    q = update.callback_query
    await q.answer()
    decision = q.data
    pid = _pid_from_message(q.message)
    for j in context.job_queue.get_jobs_by_name(f"to_{pid}"):
        j.schedule_removal()
    if decision == "regenerate":
        await q.edit_message_caption(caption="🔄 Nouvelle version en cours…")
        from backend.distribution.scheduler import run_slot
        res = await asyncio.to_thread(run_slot)
        await send_for_approval(context.application, res["pid"],
                                res["video_path"], res["caption"])
        return
    await asyncio.to_thread(orchestrator.decide_and_post, pid,
                            "approve" if decision == "approve" else "skip")
    await q.edit_message_caption(
        caption="✅ Publié" if decision == "approve" else "❌ Skippé")


async def _on_error(update, context):
    """Erreurs réseau (ReadError/TimedOut) = transitoires : PTB relance le polling
    tout seul. On loggue une ligne discrète au lieu du pavé de stacktrace."""
    err = context.error
    if isinstance(err, (NetworkError, TimedOut)):
        _log.warning("Telegram réseau (transitoire, reprise auto) : %s", err)
    else:
        _log.exception("Erreur Telegram non gérée", exc_info=err)


def build_app():
    token, _ = _cfg()
    app = Application.builder().token(token).build()
    app.add_handler(CallbackQueryHandler(_on_callback))
    app.add_error_handler(_on_error)
    return app
