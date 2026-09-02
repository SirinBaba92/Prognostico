"""
Konfiguration für den Telegram Bot
"""

import os


class BotConfig:
    # Bot Token aus Umgebungsvariable
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Admin User IDs (Telegram User ID als Integer)
    # Mehrere IDs kommagetrennt: "123456789,987654321"
    _admin_ids_raw: str = os.getenv("TELEGRAM_ADMIN_IDS", "")
    admin_ids: list[int] = [
        int(x.strip())
        for x in _admin_ids_raw.split(",")
        if x.strip().isdigit()
    ]


BOT_CONFIG = BotConfig()


def is_admin(user_id: int) -> bool:
    """Prüft ob ein User Admin ist"""
    # Wenn keine Admins konfiguriert: alle dürfen (für Entwicklung)
    if not BOT_CONFIG.admin_ids:
        return True
    return user_id in BOT_CONFIG.admin_ids
