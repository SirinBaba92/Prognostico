"""
UI für ML Predictions
Zeigt XGBoost/RandomForest Predictions mit Sheets-Integration
"""
import os
import streamlit as st
from typing import Dict, Optional
from ml.football_ml_models import get_ml_models
from ui.sheets_ml_integration import show_sheets_ml_predictions
# DEBUG - ZEIGE PFAD
st.write("🔍 DEBUG INFO:")
st.write("Current Dir:", os.getcwd())
st.write("Models folder exists?", os.path.exists("models"))
if os.path.exists("models"):
    st.write("Files in models/:", os.listdir("models"))

def show_ml_predictions_tab(match_id: str = None):
    """
    Zeigt ML Predictions Tab
    Kann entweder mit Supabase-Daten oder manueller Eingabe arbeiten
    """
    st.markdown("## 🤖 ML Predictions (XGBoost & Random Forest)")
    
    st.markdown("""
    **Professionelle ML-Models basierend auf 344+ Matches**
    
    - ✅ Over/Under 2.5 (XGBoost - 64.4% Accuracy)
    - ✅ 1X2 (Random Forest - 52.9% Accuracy)
    - ✅ BTTS (Random Forest - 60.6% Accuracy)
    
    **Zwei Versionen verfügbar:**
    - 🎲 MIT Quoten (höhere Accuracy, nutzt Markt-Information)
    - 💎 OHNE Quoten (echter Edge, unabhängig vom Markt)
    """)
    
    # Lade ML Models
    ml_models = get_ml_models()
    
    if not ml_models.models_loaded:
        st.error("❌ ML-Models nicht gefunden! Bitte erst trainieren.")
        st.info("""
        **Setup:**
        1. `python3 scripts/train_and_save_models.py` ausführen
        2. Models in `models/` Ordner kopieren
        """)
        return
    
    st.success(f"✅ {len(ml_models.models_with_odds) + len(ml_models.models_no_odds)} Models geladen")
    
    st.markdown("---")
    
    # Input-Methode wählen
    input_method = st.radio(
        "📊 Datenquelle:",
        ["🔗 Automatisch (ausgewähltes Match)", "✍️ Manuelle Eingabe"],
        horizontal=True,
        help="Nutzt das in Tab 1 aktuell ausgewählte Match aus der Datenbank"
    )
    
    if input_method == "🔗 Automatisch (ausgewähltes Match)":
        if match_id:
            show_sheets_ml_predictions(match_id)
        else:
            st.warning("⚠️ Kein Match ausgewählt! Bitte wähle erst ein Match aus Tab 1.")
    
    else:
        # Manuelle Eingabe (alte Version)
        show_manual_input_predictions(ml_models)


def show_manual_input_predictions(ml_models):
    """Manuelle Dateneingabe für ML Predictions"""
    
    st.markdown("### 📊 Match-Daten manuell eingeben")
    
    col1, col2 = st.columns(2)
    
    with col1:
        home_team = st.text_input("Heimteam", "FC Bayern München")
        home_position = st.number_input("Heimteam Position", 1, 20, 1)
        home_points = st.number_input("Heimteam Punkte", 0, 100, 50)
        home_goals_for = st.number_input("Heimteam Tore (gesamt)", 0, 200, 45)
    
    with col2:
        away_team = st.text_input("Auswärtsteam", "Borussia Dortmund")
        away_position = st.number_input("Auswärtsteam Position", 1, 20, 5)
        away_points = st.number_input("Auswärtsteam Punkte", 0, 100, 38)
        away_goals_for = st.number_input("Auswärtsteam Tore (gesamt)", 0, 200, 38)
    
    st.markdown("### 💰 Wettquoten (Optional)")
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        st.markdown("**Over/Under 2.5**")
        odds_over = st.number_input("Over 2.5", 1.0, 10.0, 1.90, 0.05)
        odds_under = st.number_input("Under 2.5", 1.0, 10.0, 1.90, 0.05)
    
    with col4:
        st.markdown("**1X2**")
        odds_home = st.number_input("Heimsieg", 1.0, 20.0, 2.05, 0.05)
        odds_draw = st.number_input("Unentschieden", 1.0, 20.0, 3.00, 0.05)
        odds_away = st.number_input("Auswärtssieg", 1.0, 20.0, 3.80, 0.05)
    
    with col5:
        st.markdown("**BTTS**")
        odds_btts_yes = st.number_input("BTTS Ja", 1.0, 10.0, 1.91, 0.05)
        odds_btts_no = st.number_input("BTTS Nein", 1.0, 10.0, 1.91, 0.05)
    
    # Erstelle Match Data Dictionary
    match_data = {
        'home_position': home_position,
        'away_position': away_position,
        'home_points': home_points,
        'away_points': away_points,
        'home_goals_for': home_goals_for,
        'away_goals_for': away_goals_for,
        'odds_over25': odds_over,
        'odds_under25': odds_under,
        'odds_home': odds_home,
        'odds_draw': odds_draw,
        'odds_away': odds_away,
        'odds_btts_yes': odds_btts_yes,
        'odds_btts_no': odds_btts_no,
    }
    
    st.markdown("---")
    
    # Prediction Button
    if st.button("🎯 PREDICTIONS ERSTELLEN", type="primary", use_container_width=True):
        
        st.markdown("## 🎯 PREDICTIONS")
        st.markdown(f"### {home_team} vs {away_team}")
        
        # Tab für beide Versionen
        tab1, tab2, tab3 = st.tabs([
            "🎲 MIT Quoten", 
            "💎 OHNE Quoten (Echter Edge)",
            "📊 Vergleich"
        ])
        
        # VERSION 1: MIT QUOTEN
        with tab1:
            st.markdown("### 🎲 Predictions MIT Quoten")
            st.info("💡 Nutzt Markt-Information (Quoten) für höhere Accuracy")
            
            predictions_with = ml_models.predict_all(match_data, use_odds=True)
            
            display_predictions(
                predictions_with, 
                home_team, 
                away_team,
                {
                    'over': odds_over,
                    'under': odds_under,
                    'home': odds_home,
                    'draw': odds_draw,
                    'away': odds_away,
                    'btts_yes': odds_btts_yes,
                    'btts_no': odds_btts_no
                },
                ml_models
            )
        
        # VERSION 2: OHNE QUOTEN
        with tab2:
            st.markdown("### 💎 Predictions OHNE Quoten (Echter Edge)")
            st.success("✅ Unabhängig vom Markt - echter statistischer Edge!")
            
            predictions_no = ml_models.predict_all(match_data, use_odds=False)
            
            display_predictions(
                predictions_no, 
                home_team, 
                away_team,
                {
                    'over': odds_over,
                    'under': odds_under,
                    'home': odds_home,
                    'draw': odds_draw,
                    'away': odds_away,
                    'btts_yes': odds_btts_yes,
                    'btts_no': odds_btts_no
                },
                ml_models
            )
        
        # VERGLEICH
        with tab3:
            st.markdown("### 📊 Vergleich: MIT vs. OHNE Quoten")
            
            compare_predictions(predictions_with, predictions_no)


def display_predictions(
    predictions: Dict, 
    home_team: str, 
    away_team: str,
    odds: Dict,
    ml_models
):
    """
    Zeigt Predictions mit Value-Analyse an
    """
    
    # OVER/UNDER 2.5
    if predictions.get('over_under'):
        ou = predictions['over_under']
        
        st.markdown("#### ⚽ Over/Under 2.5")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Prediction", ou['prediction'])
        with col2:
            st.metric("Confidence", f"{ou['confidence']:.1f}%")
        with col3:
            # Value-Analyse
            if ou['prediction'] == 'OVER 2.5':
                value = ml_models.analyze_value(ou, odds['over'])
                if value['has_value']:
                    st.success(f"💰 VALUE! EV: +{value['expected_value']:.1f}%")
                else:
                    st.warning("⚠️ Kein Value")
            else:
                value = ml_models.analyze_value(ou, odds['under'])
                if value['has_value']:
                    st.success(f"💰 VALUE! EV: +{value['expected_value']:.1f}%")
                else:
                    st.warning("⚠️ Kein Value")
        
        # Progress Bars
        st.progress(ou['prob_over'] / 100, text=f"Over 2.5: {ou['prob_over']:.1f}%")
        st.progress(ou['prob_under'] / 100, text=f"Under 2.5: {ou['prob_under']:.1f}%")
    
    st.markdown("---")
    
    # 1X2
    if predictions.get('1x2'):
        x2 = predictions['1x2']
        
        st.markdown("#### 🎯 1X2 (Ergebnis)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Prediction", x2['prediction'])
        with col2:
            st.metric("Confidence", f"{x2['confidence']:.1f}%")
        with col3:
            # Value-Analyse
            if x2['prediction'] == 'HOME WIN':
                value = ml_models.analyze_value(x2, odds['home'])
            elif x2['prediction'] == 'DRAW':
                value = ml_models.analyze_value(x2, odds['draw'])
            else:
                value = ml_models.analyze_value(x2, odds['away'])
            
            if value['has_value']:
                st.success(f"💰 VALUE! EV: +{value['expected_value']:.1f}%")
            else:
                st.warning("⚠️ Kein Value")
        
        # Progress Bars
        st.progress(x2['prob_home'] / 100, text=f"{home_team}: {x2['prob_home']:.1f}%")
        st.progress(x2['prob_draw'] / 100, text=f"Draw: {x2['prob_draw']:.1f}%")
        st.progress(x2['prob_away'] / 100, text=f"{away_team}: {x2['prob_away']:.1f}%")
    
    st.markdown("---")
    
    # BTTS
    if predictions.get('btts'):
        btts = predictions['btts']
        
        st.markdown("#### 🔥 BTTS (Both Teams To Score)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Prediction", btts['prediction'])
        with col2:
            st.metric("Confidence", f"{btts['confidence']:.1f}%")
        with col3:
            # Value-Analyse
            if btts['prediction'] == 'BTTS YES':
                value = ml_models.analyze_value(btts, odds['btts_yes'])
            else:
                value = ml_models.analyze_value(btts, odds['btts_no'])
            
            if value['has_value']:
                st.success(f"💰 VALUE! EV: +{value['expected_value']:.1f}%")
            else:
                st.warning("⚠️ Kein Value")
        
        # Progress Bars
        st.progress(btts['prob_yes'] / 100, text=f"BTTS Yes: {btts['prob_yes']:.1f}%")
        st.progress(btts['prob_no'] / 100, text=f"BTTS No: {btts['prob_no']:.1f}%")


def compare_predictions(predictions_with: Dict, predictions_no: Dict):
    """
    Vergleicht Predictions mit und ohne Quoten
    """
    
    st.markdown("#### ⚖️ Over/Under 2.5")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**MIT Quoten**")
        if predictions_with.get('over_under'):
            ou_with = predictions_with['over_under']
            st.write(f"Prediction: {ou_with['prediction']}")
            st.write(f"Confidence: {ou_with['confidence']:.1f}%")
    
    with col2:
        st.markdown("**OHNE Quoten**")
        if predictions_no.get('over_under'):
            ou_no = predictions_no['over_under']
            st.write(f"Prediction: {ou_no['prediction']}")
            st.write(f"Confidence: {ou_no['confidence']:.1f}%")
    
    st.markdown("---")
    
    st.markdown("#### ⚖️ 1X2")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**MIT Quoten**")
        if predictions_with.get('1x2'):
            x2_with = predictions_with['1x2']
            st.write(f"Prediction: {x2_with['prediction']}")
            st.write(f"Confidence: {x2_with['confidence']:.1f}%")
    
    with col2:
        st.markdown("**OHNE Quoten**")
        if predictions_no.get('1x2'):
            x2_no = predictions_no['1x2']
            st.write(f"Prediction: {x2_no['prediction']}")
            st.write(f"Confidence: {x2_no['confidence']:.1f}%")
    
    st.markdown("---")
    
    st.markdown("#### ⚖️ BTTS")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**MIT Quoten**")
        if predictions_with.get('btts'):
            btts_with = predictions_with['btts']
            st.write(f"Prediction: {btts_with['prediction']}")
            st.write(f"Confidence: {btts_with['confidence']:.1f}%")
    
    with col2:
        st.markdown("**OHNE Quoten**")
        if predictions_no.get('btts'):
            btts_no = predictions_no['btts']
            st.write(f"Prediction: {btts_no['prediction']}")
            st.write(f"Confidence: {btts_no['confidence']:.1f}%")
