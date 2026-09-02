"""
Risk Management und Bankroll Management Funktionen
"""

import streamlit as st
from datetime import datetime
from typing import Dict
from config.constants import RISK_PROFILES, STAKE_PERCENTAGES


def calculate_stake_recommendation(
    risk_score: int, odds: float, market: str = "1x2", match_info: str = ""
) -> Dict:
    """
    Berechnet Einsatz-Empfehlung basierend auf Risiko-Score und Bankroll
    
    Args:
        risk_score: Risiko-Score 1-5
        odds: Wett-Quote
        market: Wett-Market (für Tracking)
        match_info: Match-Information (für Tracking)
        
    Returns:
        Dictionary mit Einsatz-Empfehlungen
    """
    bankroll = st.session_state.risk_management["bankroll"]
    risk_profile = st.session_state.risk_management["risk_profile"]
    profile_data = RISK_PROFILES[risk_profile]

    base_percentage = STAKE_PERCENTAGES.get(risk_score, 2.0)
    adjusted_percentage = base_percentage * profile_data["adjustment"]
    max_percentage = profile_data["max_stake_percent"]
    final_percentage = min(adjusted_percentage, max_percentage)

    recommended_stake = bankroll * (final_percentage / 100)
    min_stake = max(10.0, recommended_stake * 0.5)
    max_stake = min(bankroll * 0.25, recommended_stake * 1.5)

    potential_win = recommended_stake * (odds - 1)
    potential_loss = recommended_stake

    return {
        "risk_score": risk_score,
        "risk_profile": risk_profile,
        "base_percentage": base_percentage,
        "adjusted_percentage": round(final_percentage, 2),
        "recommended_stake": round(recommended_stake, 2),
        "min_stake": round(min_stake, 2),
        "max_stake": round(max_stake, 2),
        "potential_win": round(potential_win, 2),
        "potential_loss": round(potential_loss, 2),
        "new_bankroll_win": round(bankroll + potential_win, 2),
        "new_bankroll_loss": round(bankroll - potential_loss, 2),
    }


def add_to_stake_history(match_info: str, stake: float, profit: float, market: str):
    """
    Fügt eine Wette zur Historie hinzu und aktualisiert Bankroll
    
    Args:
        match_info: Match-Information
        stake: Einsatz
        profit: Gewinn/Verlust
        market: Wett-Market
    """
    if "stake_history" not in st.session_state.risk_management:
        st.session_state.risk_management["stake_history"] = []

    # Speichere aktuelle Bankroll BEVOR die Änderung
    bankroll_before = st.session_state.risk_management["bankroll"]

    history_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "match": match_info,
        "stake": stake,
        "profit": profit,
        "market": market,
        "bankroll_before": bankroll_before,
    }

    st.session_state.risk_management["stake_history"].append(history_entry)

    # Limitiere Historie auf 100 Einträge
    if len(st.session_state.risk_management["stake_history"]) > 100:
        st.session_state.risk_management["stake_history"] = (
            st.session_state.risk_management["stake_history"][-100:]
        )

    # Aktualisiere Bankroll
    st.session_state.risk_management["bankroll"] += profit
