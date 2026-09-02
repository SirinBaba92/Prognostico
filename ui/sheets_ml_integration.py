"""
Match-Daten-Integration für ML Predictions
Lädt Match-Daten direkt aus Supabase und erstellt Predictions
"""

import streamlit as st
from typing import Dict, Optional
from data.supabase_client import get_full_match_bundle
from data.supabase_mapper import map_bundle_to_match_data
from ml.football_ml_models import get_ml_models
from ml.scoreline_predictor import ScorelinePredictor


def convert_match_data_to_features(match_data) -> Dict:
    """
    Konvertiert MatchData Objekt zu Feature Dictionary für ML Models
    
    Args:
        match_data: MatchData Objekt vom Parser
        
    Returns:
        Dictionary mit Features
    """
    features = {}
    
    # Home Team Features (direkt aus TeamStats, NICHT .overall!)
    if match_data.home_team:
        ht = match_data.home_team
        
        # Basic Stats
        features['home_position'] = ht.position if hasattr(ht, 'position') else 10
        features['home_points'] = ht.points if hasattr(ht, 'points') else 0
        features['home_goals_for'] = ht.goals_for if hasattr(ht, 'goals_for') else 0
        features['home_goals_against'] = ht.goals_against if hasattr(ht, 'goals_against') else 0
        features['home_wins'] = ht.wins if hasattr(ht, 'wins') else 0
        features['home_draws'] = ht.draws if hasattr(ht, 'draws') else 0
        features['home_losses'] = ht.losses if hasattr(ht, 'losses') else 0
        features['home_ppg_overall'] = ht.ppg_overall if hasattr(ht, 'ppg_overall') else 0
        features['home_goal_diff'] = ht.goal_diff if hasattr(ht, 'goal_diff') else 0
        
        # Home/Away Stats
        features['home_total_goals_for_ha'] = ht.ha_goals_for if hasattr(ht, 'ha_goals_for') else 0
        features['home_total_goals_against_ha'] = ht.ha_goals_against if hasattr(ht, 'ha_goals_against') else 0
        features['home_ppg_ha'] = ht.ppg_ha if hasattr(ht, 'ppg_ha') else 0
        
        # Form (Last 5)
        features['home_last5_points'] = ht.form_points if hasattr(ht, 'form_points') else 0
        features['home_last5_goals_for'] = ht.form_goals_for if hasattr(ht, 'form_goals_for') else 0
        features['home_last5_goals_against'] = ht.form_goals_against if hasattr(ht, 'form_goals_against') else 0
        features['home_last5_goal_diff'] = features['home_last5_goals_for'] - features['home_last5_goals_against']
        
        # Additional Stats
        features['home_avg_goals_scored_overall'] = ht.goals_scored_per_match if hasattr(ht, 'goals_scored_per_match') else 0
        features['home_avg_goals_conceded_overall'] = ht.goals_conceded_per_match if hasattr(ht, 'goals_conceded_per_match') else 0
        
    # Away Team Features (direkt aus TeamStats, NICHT .overall!)
    if match_data.away_team:
        at = match_data.away_team
        
        # Basic Stats
        features['away_position'] = at.position if hasattr(at, 'position') else 10
        features['away_points'] = at.points if hasattr(at, 'points') else 0
        features['away_goals_for'] = at.goals_for if hasattr(at, 'goals_for') else 0
        features['away_goals_against'] = at.goals_against if hasattr(at, 'goals_against') else 0
        features['away_wins'] = at.wins if hasattr(at, 'wins') else 0
        features['away_draws'] = at.draws if hasattr(at, 'draws') else 0
        features['away_losses'] = at.losses if hasattr(at, 'losses') else 0
        features['away_ppg_overall'] = at.ppg_overall if hasattr(at, 'ppg_overall') else 0
        features['away_goal_diff'] = at.goal_diff if hasattr(at, 'goal_diff') else 0
        
        # Home/Away Stats
        features['away_total_goals_for_ha'] = at.ha_goals_for if hasattr(at, 'ha_goals_for') else 0
        features['away_total_goals_against_ha'] = at.ha_goals_against if hasattr(at, 'ha_goals_against') else 0
        features['away_ppg_ha'] = at.ppg_ha if hasattr(at, 'ppg_ha') else 0
        
        # Form (Last 5)
        features['away_last5_points'] = at.form_points if hasattr(at, 'form_points') else 0
        features['away_last5_goals_for'] = at.form_goals_for if hasattr(at, 'form_goals_for') else 0
        features['away_last5_goals_against'] = at.form_goals_against if hasattr(at, 'form_goals_against') else 0
        features['away_last5_goal_diff'] = features['away_last5_goals_for'] - features['away_last5_goals_against']
        
        # Additional Stats
        features['away_avg_goals_scored_overall'] = at.goals_scored_per_match if hasattr(at, 'goals_scored_per_match') else 0
        features['away_avg_goals_conceded_overall'] = at.goals_conceded_per_match if hasattr(at, 'goals_conceded_per_match') else 0
    
    # Odds
    if match_data.odds_1x2:
        features['odds_home'] = match_data.odds_1x2[0]
        features['odds_draw'] = match_data.odds_1x2[1]
        features['odds_away'] = match_data.odds_1x2[2]
    
    if match_data.odds_ou25:
        features['odds_over25'] = match_data.odds_ou25[0]
        features['odds_under25'] = match_data.odds_ou25[1]
    
    if match_data.odds_btts:
        features['odds_btts_yes'] = match_data.odds_btts[0]
        features['odds_btts_no'] = match_data.odds_btts[1]
    
    return features


def show_sheets_ml_predictions(match_id: Optional[str]):
    """
    Zeigt ML Predictions basierend auf Supabase-Match-Daten

    Args:
        match_id: match_id (UUID) des ausgewählten Matches
    """

    if not match_id:
        st.info("⬅️ Bitte wähle erst ein Match aus der Liste links")
        return

    st.markdown("## 🤖 ML Predictions")

    # Lade Models
    ml_models = get_ml_models()

    if not ml_models.models_loaded:
        st.error("❌ ML-Models nicht gefunden!")
        st.info("""
        **Setup benötigt:**
        1. Models trainieren: `python3 scripts/train_and_save_models.py`
        2. Models in `models/` Ordner kopieren
        """)
        return

    # Lade Match-Daten
    try:
        with st.spinner("Lade Match-Daten..."):
            bundle = get_full_match_bundle(match_id)

            if not bundle:
                st.error("❌ Konnte Match-Daten nicht laden")
                return

            match_data = map_bundle_to_match_data(bundle)

            # Konvertiere zu Features
            features = convert_match_data_to_features(match_data)

    except Exception as e:
        st.error(f"❌ Fehler beim Laden: {e}")
        return
    
    # Match Info
    st.success(f"✅ Daten geladen: **{match_data.home_team.name} vs {match_data.away_team.name}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Datum", match_data.date or "N/A")
    with col2:
        st.metric("Liga", match_data.competition or "N/A")
    with col3:
        st.metric("Anstoß", match_data.kickoff or "N/A")
    
    st.markdown("---")
    
    # Version Auswahl (mit unique key um Tab 1 Rerun zu vermeiden)
    version_choice = st.radio(
        "Welche Model-Version?",
        ["🎲 MIT Quoten", "💎 OHNE Quoten (Echter Edge)", "📊 BEIDE Vergleichen"],
        horizontal=True,
        key="ml_version_choice"  # Unique key!
    )
    
    st.markdown("---")
    
    # Predictions
    if version_choice == "📊 BEIDE Vergleichen":
        # Beide Versionen anzeigen
        col_with, col_no = st.columns(2)
        
        with col_with:
            st.markdown("### 🎲 MIT Quoten")
            predictions_with = ml_models.predict_all(features, use_odds=True)
            display_compact_predictions(
                predictions_with, 
                match_data,
                ml_models
            )
        
        with col_no:
            st.markdown("### 💎 OHNE Quoten")
            predictions_no = ml_models.predict_all(features, use_odds=False)
            display_compact_predictions(
                predictions_no, 
                match_data,
                ml_models
            )
    
    elif version_choice == "🎲 MIT Quoten":
        predictions = ml_models.predict_all(features, use_odds=True)
        display_full_predictions(predictions, match_data, ml_models)
    
    else:  # OHNE Quoten
        predictions = ml_models.predict_all(features, use_odds=False)
        display_full_predictions(predictions, match_data, ml_models)


def display_compact_predictions(predictions: Dict, match_data, ml_models):
    """Kompakte Darstellung für Vergleich"""
    
    # Over/Under
    if predictions.get('over_under'):
        ou = predictions['over_under']
        st.markdown(f"**Over/Under 2.5**")
        st.write(f"{ou['prediction']} ({ou['confidence']:.1f}%)")
        
        if match_data.odds_ou25:
            odds = match_data.odds_ou25[0] if ou['prediction'] == 'OVER 2.5' else match_data.odds_ou25[1]
            value = ml_models.analyze_value(ou, odds)
            if value['has_value']:
                st.success(f"💰 VALUE! +{value['expected_value']:.1f}%")
    
    st.markdown("---")
    
    # 1X2
    if predictions.get('1x2'):
        x2 = predictions['1x2']
        st.markdown(f"**1X2**")
        st.write(f"{x2['prediction']} ({x2['confidence']:.1f}%)")
        
        if match_data.odds_1x2:
            if x2['prediction'] == 'HOME WIN':
                odds = match_data.odds_1x2[0]
            elif x2['prediction'] == 'DRAW':
                odds = match_data.odds_1x2[1]
            else:
                odds = match_data.odds_1x2[2]
            
            value = ml_models.analyze_value(x2, odds)
            if value['has_value']:
                st.success(f"💰 VALUE! +{value['expected_value']:.1f}%")
    
    st.markdown("---")
    
    # BTTS
    if predictions.get('btts'):
        btts = predictions['btts']
        st.markdown(f"**BTTS**")
        st.write(f"{btts['prediction']} ({btts['confidence']:.1f}%)")
        
        if match_data.odds_btts:
            odds = match_data.odds_btts[0] if btts['prediction'] == 'BTTS YES' else match_data.odds_btts[1]
            value = ml_models.analyze_value(btts, odds)
            if value['has_value']:
                st.success(f"💰 VALUE! +{value['expected_value']:.1f}%")


def display_full_predictions(predictions: Dict, match_data, ml_models):
    """Vollständige Darstellung mit Details und Scoreline Prediction"""
    
    # Erstelle Scoreline Predictor
    scoreline_pred = ScorelinePredictor()
    
    # Berechne Expected Goals aus Match-Daten
    home_xg = match_data.home_team.goals_scored_per_match if hasattr(match_data.home_team, 'goals_scored_per_match') else 1.5
    away_xg = match_data.away_team.goals_scored_per_match if hasattr(match_data.away_team, 'goals_scored_per_match') else 1.3
    
    # Generiere alle Scorelines
    all_scorelines = scoreline_pred.predict_scorelines(home_xg, away_xg, top_n=20)
    top_scorelines = all_scorelines[:5]
    
    # Leite Markt-Wahrscheinlichkeiten ab
    derived_probs = scoreline_pred.derive_market_probabilities(all_scorelines)
    
    # SCORELINE PREDICTIONS ZUERST
    st.markdown("### 🎯 Wahrscheinlichste Scorelines (Poisson)")
    st.info("💡 Diese Scorelines sind **mathematisch konsistent** über alle Märkte!")
    
    # Top 5 Scorelines
    cols = st.columns(5)
    for i, scoreline in enumerate(top_scorelines):
        with cols[i]:
            st.metric(
                f"#{i+1}: {scoreline['scoreline']}", 
                f"{scoreline['probability']:.1f}%"
            )
            st.caption(f"{scoreline['result']}")
            st.caption(f"{scoreline['over_under']}")
            st.caption(f"BTTS: {scoreline['btts']}")
    
    st.markdown("---")
    
    # Consistency Check
    if predictions.get('1x2') and predictions.get('over_under') and predictions.get('btts'):
        x2_pred = predictions['1x2']['prediction'].replace(' WIN', '').replace('DRAW', 'DRAW')
        ou_pred = 'OVER' if 'OVER' in predictions['over_under']['prediction'] else 'UNDER'
        btts_pred = 'YES' if 'YES' in predictions['btts']['prediction'] else 'NO'
        
        consistency = scoreline_pred.check_consistency(x2_pred, ou_pred, btts_pred)
        
        if consistency['is_consistent']:
            st.success(f"✅ ML Predictions sind konsistent! Mögliche Scorelines: {', '.join(consistency['possible_scorelines'][:3])}")
            
            # Zeige wahrscheinlichste passende Scoreline
            best_match = scoreline_pred.get_most_likely_scoreline_for_markets(
                x2_pred, ou_pred, btts_pred, all_scorelines
            )
            if best_match:
                st.info(f"🎯 Wahrscheinlichste passende Scoreline: **{best_match['scoreline']}** ({best_match['probability']:.1f}%)")
        else:
            st.warning(f"⚠️ ML Predictions sind INKONSISTENT! Keine mögliche Scoreline passt zu allen 3 Märkten.")
            st.info("💡 Nutze die Scoreline-Predictions oben für konsistente Vorhersagen!")
    
    st.markdown("---")
    
    # ML Model Predictions
    st.markdown("### 🤖 ML Model Predictions")
    
    # Over/Under
    if predictions.get('over_under'):
        ou = predictions['over_under']
        st.markdown("### ⚽ Over/Under 2.5")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Prediction", ou['prediction'])
        with col2:
            st.metric("Confidence", f"{ou['confidence']:.1f}%")
        with col3:
            if match_data.odds_ou25:
                odds = match_data.odds_ou25[0] if ou['prediction'] == 'OVER 2.5' else match_data.odds_ou25[1]
                st.metric("Quote", f"{odds:.2f}")
                
                value = ml_models.analyze_value(ou, odds)
                if value['has_value']:
                    st.success(f"💰 VALUE! EV: +{value['expected_value']:.1f}%")
                else:
                    st.warning("⚠️ Kein Value")
        
        st.progress(ou['prob_over'] / 100, text=f"Over: {ou['prob_over']:.1f}%")
        st.progress(ou['prob_under'] / 100, text=f"Under: {ou['prob_under']:.1f}%")
    
    st.markdown("---")
    
    # 1X2
    if predictions.get('1x2'):
        x2 = predictions['1x2']
        st.markdown("### 🎯 1X2")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Prediction", x2['prediction'])
        with col2:
            st.metric("Confidence", f"{x2['confidence']:.1f}%")
        with col3:
            if match_data.odds_1x2:
                if x2['prediction'] == 'HOME WIN':
                    odds = match_data.odds_1x2[0]
                elif x2['prediction'] == 'DRAW':
                    odds = match_data.odds_1x2[1]
                else:
                    odds = match_data.odds_1x2[2]
                
                st.metric("Quote", f"{odds:.2f}")
                
                value = ml_models.analyze_value(x2, odds)
                if value['has_value']:
                    st.success(f"💰 VALUE! EV: +{value['expected_value']:.1f}%")
                else:
                    st.warning("⚠️ Kein Value")
        
        st.progress(x2['prob_home'] / 100, text=f"Home: {x2['prob_home']:.1f}%")
        st.progress(x2['prob_draw'] / 100, text=f"Draw: {x2['prob_draw']:.1f}%")
        st.progress(x2['prob_away'] / 100, text=f"Away: {x2['prob_away']:.1f}%")
    
    st.markdown("---")
    
    # BTTS
    if predictions.get('btts'):
        btts = predictions['btts']
        st.markdown("### 🔥 BTTS")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Prediction", btts['prediction'])
        with col2:
            st.metric("Confidence", f"{btts['confidence']:.1f}%")
        with col3:
            if match_data.odds_btts:
                odds = match_data.odds_btts[0] if btts['prediction'] == 'BTTS YES' else match_data.odds_btts[1]
                st.metric("Quote", f"{odds:.2f}")
                
                value = ml_models.analyze_value(btts, odds)
                if value['has_value']:
                    st.success(f"💰 VALUE! EV: +{value['expected_value']:.1f}%")
                else:
                    st.warning("⚠️ Kein Value")
        
        st.progress(btts['prob_yes'] / 100, text=f"Yes: {btts['prob_yes']:.1f}%")
        st.progress(btts['prob_no'] / 100, text=f"No: {btts['prob_no']:.1f}%")
