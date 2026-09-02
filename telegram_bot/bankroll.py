"""
Demo Bankroll System für den Telegram Bot
- Pro User separate Bankroll
- Persistent in Google Sheets + In-Memory Cache
- Kelly Criterion für Stake-Empfehlung
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# In-Memory Cache: {user_id: {bankroll_data}}
_cache: dict = {}


def _now() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def _today() -> str:
    return datetime.now().strftime("%d.%m.%Y")


# ─────────────────────────────────────────────
# DEFAULT STRUKTUR
# ─────────────────────────────────────────────

def _default_user() -> dict:
    return {
        "bankroll": 0.0,
        "initial": 0.0,
        "bets": [],        # offene Wetten
        "history": [],     # abgeschlossene Wetten
    }


# ─────────────────────────────────────────────
# CACHE ZUGRIFF
# ─────────────────────────────────────────────

def get_user_data(user_id: int) -> dict:
    if user_id not in _cache:
        # Versuche aus Sheets laden
        try:
            from telegram_bot.bankroll_sheets import load_user
            data = load_user(user_id)
            _cache[user_id] = data if data else _default_user()
        except Exception:
            _cache[user_id] = _default_user()
    return _cache[user_id]


def save_user_data(user_id: int):
    try:
        from telegram_bot.bankroll_sheets import save_user
        save_user(user_id, _cache[user_id])
    except Exception as e:
        logger.warning(f"Sheets-Speicherung fehlgeschlagen: {e}")


# ─────────────────────────────────────────────
# BANKROLL OPERATIONEN
# ─────────────────────────────────────────────

def set_bankroll(user_id: int, amount: float) -> dict:
    data = get_user_data(user_id)
    data["bankroll"] = amount
    data["initial"] = amount
    data["bets"] = []
    data["history"] = []
    save_user_data(user_id)
    return data


def get_bankroll(user_id: int) -> float:
    return get_user_data(user_id)["bankroll"]


def kelly_stake(prob: float, odds: float, bankroll: float, fraction: float = 0.25) -> float:
    """
    Kelly Criterion (fractional) für Stake-Empfehlung
    fraction=0.25 = Quarter Kelly (konservativer)
    """
    try:
        p = prob / 100
        b = float(odds) - 1
        kelly = (b * p - (1 - p)) / b
        if kelly <= 0:
            return 0.0
        stake = bankroll * kelly * fraction
        return round(min(stake, bankroll * 0.1), 2)  # Max 10% der Bankroll
    except Exception:
        return 0.0


# ─────────────────────────────────────────────
# WETTEN
# ─────────────────────────────────────────────

def place_bet(user_id: int, match: str, bet_type: str, odds: float,
              stake: float, prob: float) -> dict:
    data = get_user_data(user_id)

    if data["bankroll"] <= 0:
        return {"error": "no_bankroll"}

    if stake > data["bankroll"]:
        return {"error": "insufficient_funds", "bankroll": data["bankroll"]}

    if stake <= 0:
        return {"error": "invalid_stake"}

    bet_id = len(data["bets"]) + len(data["history"]) + 1

    bet = {
        "id": bet_id,
        "match": match,
        "bet_type": bet_type,
        "odds": odds,
        "stake": stake,
        "prob": prob,
        "potential_win": round(stake * odds, 2),
        "date": _today(),
        "time": _now(),
        "status": "open",
    }

    data["bankroll"] = round(data["bankroll"] - stake, 2)
    data["bets"].append(bet)
    save_user_data(user_id)
    return {"success": True, "bet": bet, "bankroll": data["bankroll"]}


def get_open_bets(user_id: int) -> list:
    return get_user_data(user_id)["bets"]


def close_bet(user_id: int, bet_id: int, won: bool) -> dict:
    data = get_user_data(user_id)

    bet = next((b for b in data["bets"] if b["id"] == bet_id), None)
    if not bet:
        return {"error": "not_found"}

    if won:
        payout = bet["potential_win"]
        profit = round(payout - bet["stake"], 2)
        data["bankroll"] = round(data["bankroll"] + payout, 2)
    else:
        payout = 0.0
        profit = -bet["stake"]

    bet["status"] = "won" if won else "lost"
    bet["profit"] = profit
    bet["closed"] = _now()

    data["bets"] = [b for b in data["bets"] if b["id"] != bet_id]
    data["history"].append(bet)
    save_user_data(user_id)

    return {
        "success": True,
        "bet": bet,
        "profit": profit,
        "bankroll": data["bankroll"],
    }


# ─────────────────────────────────────────────
# STATISTIKEN
# ─────────────────────────────────────────────

def get_stats(user_id: int) -> dict:
    data = get_user_data(user_id)
    history = data["history"]
    open_bets = data["bets"]

    if not history:
        return {
            "total": 0, "won": 0, "lost": 0,
            "win_rate": 0.0, "total_staked": 0.0,
            "total_profit": 0.0, "roi": 0.0,
            "bankroll": data["bankroll"],
            "initial": data["initial"],
            "open": len(open_bets),
            "best_win": None, "worst_loss": None,
        }

    won = [b for b in history if b["status"] == "won"]
    lost = [b for b in history if b["status"] == "lost"]
    total_staked = sum(b["stake"] for b in history)
    total_profit = sum(b["profit"] for b in history)
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0.0

    best_win = max(history, key=lambda b: b.get("profit", 0)) if won else None
    worst_loss = min(history, key=lambda b: b.get("profit", 0)) if lost else None

    return {
        "total": len(history),
        "won": len(won),
        "lost": len(lost),
        "win_rate": len(won) / len(history) * 100 if history else 0,
        "total_staked": total_staked,
        "total_profit": total_profit,
        "roi": roi,
        "bankroll": data["bankroll"],
        "initial": data["initial"],
        "open": len(open_bets),
        "best_win": best_win,
        "worst_loss": worst_loss,
    }


# ─────────────────────────────────────────────
# STAKE EMPFEHLUNG (identisch mit Streamlit App)
# ─────────────────────────────────────────────

STAKE_PERCENTAGES = {
    1: 0.5,
    2: 1.0,
    3: 2.0,
    4: 3.5,
    5: 5.0,
}

RISK_PROFILES = {
    "sehr_konservativ": {"name": "Sehr konservativ", "adjustment": 0.7,  "max_stake_percent": 2.0},
    "konservativ":      {"name": "Konservativ",      "adjustment": 0.85, "max_stake_percent": 3.0},
    "moderat":          {"name": "Moderat",           "adjustment": 1.0,  "max_stake_percent": 5.0},
    "aggressiv":        {"name": "Aggressiv",         "adjustment": 1.15, "max_stake_percent": 7.0},
    "sehr_aggressiv":   {"name": "Sehr aggressiv",    "adjustment": 1.3,  "max_stake_percent": 10.0},
}

DEFAULT_PROFILE = "moderat"


def get_risk_profile(user_id: int) -> str:
    data = get_user_data(user_id)
    return data.get("risk_profile", DEFAULT_PROFILE)


def set_risk_profile(user_id: int, profile: str):
    if profile not in RISK_PROFILES:
        return False
    data = get_user_data(user_id)
    data["risk_profile"] = profile
    save_user_data(user_id)
    return True


def calculate_stake(user_id: int, risk_score: int, odds: float) -> dict:
    """
    Berechnet Einsatz-Empfehlung basierend auf Risiko-Score und Profil
    Identisch mit der Streamlit App Logik
    """
    data = get_user_data(user_id)
    bankroll = data["bankroll"]
    profile_key = data.get("risk_profile", DEFAULT_PROFILE)
    profile = RISK_PROFILES[profile_key]

    base_pct = STAKE_PERCENTAGES.get(risk_score, 2.0)
    adjusted_pct = base_pct * profile["adjustment"]
    final_pct = min(adjusted_pct, profile["max_stake_percent"])

    recommended = round(bankroll * (final_pct / 100), 2)
    half = round(recommended * 0.5, 2)
    double = round(min(recommended * 2, bankroll * profile["max_stake_percent"] / 100), 2)

    potential_win = round(recommended * (odds - 1), 2)

    return {
        "recommended": recommended,
        "half": half,
        "double": double,
        "percentage": round(final_pct, 2),
        "potential_win": potential_win,
        "profile_name": profile["name"],
        "bankroll": bankroll,
    }
