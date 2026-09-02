"""
Bot Runner – Polling mit automatischem Retry bei Conflict.
Telegram beendet alte Verbindungen nach ~60 Sekunden automatisch.
"""

import threading
import asyncio
import logging
import os
import time
import urllib.request

logger = logging.getLogger(__name__)

_bot_thread = None


def _drop_webhook(token: str):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        urllib.request.urlopen(url, timeout=10)
        logger.info("Webhook gelöscht")
    except Exception as e:
        logger.warning(f"deleteWebhook Fehler: {e}")


async def _poll(token: str):
    from telegram import Update
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler
    from telegram.error import Conflict

    from telegram_bot.handlers import (
        start_handler, lang_handler, today_handler, dates_handler,
        date_handler, bet_handler, button_callback_handler, error_handler,
        bankroll_handler, setbank_handler, open_bets_handler, stats_handler,
        profil_handler,
    )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("lang", lang_handler))
    app.add_handler(CommandHandler("bankroll", bankroll_handler))
    app.add_handler(CommandHandler("setbank", setbank_handler))
    app.add_handler(CommandHandler("open", open_bets_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("profil", profil_handler))
    app.add_handler(CommandHandler("today", today_handler))
    app.add_handler(CommandHandler("dates", dates_handler))
    app.add_handler(CommandHandler("date", date_handler))
    app.add_handler(CommandHandler("bet", bet_handler))
    app.add_handler(CallbackQueryHandler(button_callback_handler))
    app.add_error_handler(error_handler)

    await app.initialize()

    while True:
        try:
            await app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
            await app.start()
            logger.info("Bot Polling gestartet")
            while True:
                await asyncio.sleep(60)
        except Conflict:
            logger.warning("Conflict – warte 65 Sekunden und versuche erneut...")
            try:
                await app.updater.stop()
            except Exception:
                pass
            await asyncio.sleep(65)
        except Exception as e:
            logger.error(f"Unerwarteter Fehler: {e} – Neustart in 30s")
            await asyncio.sleep(30)


def _run_bot(token: str):
    _drop_webhook(token)
    time.sleep(2)  # kurz warten damit alte Verbindung abbaut

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_poll(token))
    finally:
        loop.close()


def start_bot_in_background():
    global _bot_thread

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        try:
            import streamlit as st
            token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
            if token:
                os.environ["TELEGRAM_BOT_TOKEN"] = token
        except Exception:
            pass

    if not token:
        return

    if _bot_thread is not None and _bot_thread.is_alive():
        return

    _bot_thread = threading.Thread(
        target=_run_bot, args=(token,), daemon=True, name="TelegramBot"
    )
    _bot_thread.start()
    logger.info("Telegram Bot Thread gestartet")
