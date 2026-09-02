"""
Session State Initialisierung und Verwaltung
"""

import streamlit as st


def initialize_session_state():
    """
    Initialisiert alle Session State Variablen für die App
    """
    # Phase 1: Risiko-Management Session State
    if "alert_thresholds" not in st.session_state:
        st.session_state.alert_thresholds = {
            "mu_total_high": 4.5,
            "tki_high": 1.0,
            "ppg_diff_extreme": 1.5,
        }

    if "risk_management" not in st.session_state:
        st.session_state.risk_management = {
            "bankroll": 1000.0,
            "risk_profile": "moderat",
            "stake_history": [],
        }

    # Phase 3 & 4: ML-Modelle Session State
    if "position_ml_model" not in st.session_state:
        st.session_state.position_ml_model = None

    if "extended_ml_model" not in st.session_state:
        st.session_state.extended_ml_model = None

    # Demo-Modus
    if "enable_demo_mode" not in st.session_state:
        st.session_state.enable_demo_mode = False
