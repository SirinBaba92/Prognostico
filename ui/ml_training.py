"""
ML Training UI-Komponente
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ml.position_ml import TablePositionML
from ml.extended_ml import ExtendedMatchML
from models.tracking import load_historical_matches_from_sheets


def show_ml_training_ui():
    """
    Zeigt die ML-Training UI mit Modell-Status und Training-Funktionen
    """
    st.subheader("🤖 ML-Modell Training (Phase 3: Position)")

    # Lade historische Daten
    historical_matches = load_historical_matches_from_sheets()

    st.info(f"📊 {len(historical_matches)} historische Matches verfügbar")

    # Position ML Model Status
    if st.session_state.position_ml_model is None:
        st.session_state.position_ml_model = TablePositionML()

    model = st.session_state.position_ml_model
    model_info = model.get_model_info()

    col1, col2, col3 = st.columns(3)

    with col1:
        status = "✅ Trainiert" if model_info["is_trained"] else "❌ Nicht trainiert"
        st.metric("Status", status)

    with col2:
        st.metric("Training-Daten", model_info["training_data_size"])

    with col3:
        st.metric("Letzes Training", model_info["last_trained"])

    # Training Button
    st.markdown("---")

    if len(historical_matches) < 30:
        st.warning(
            f"⚠️ Mindestens 30 Matches benötigt (aktuell: {len(historical_matches)})"
        )
        st.info(
            "💡 Gehe zu Tab 'Training Data' um historische Matches hinzuzufügen"
        )
    else:
        if st.button(
            f"🚀 ML-Modell trainieren ({len(historical_matches)} Matches)",
            use_container_width=True,
        ):
            with st.spinner("Training läuft..."):
                result = model.train(historical_matches, min_matches=30)

                if result["success"]:
                    st.success(f"✅ {result['message']}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")

    # Feature Importance (wenn trainiert)
    if model_info["is_trained"] and model_info["feature_importance"]:
        st.markdown("---")
        st.subheader("📊 Feature Importance")

        feature_importance = model_info["feature_importance"]

        # Top 15 Features
        sorted_features = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )[:15]

        df = pd.DataFrame(sorted_features, columns=["Feature", "Importance"])

        fig = go.Figure(
            data=[
                go.Bar(
                    x=df["Importance"],
                    y=df["Feature"],
                    orientation="h",
                    marker_color="lightblue",
                )
            ]
        )

        fig.update_layout(
            title="Top 15 wichtigste Features",
            xaxis_title="Importance",
            yaxis_title="Feature",
            height=500,
        )

        st.plotly_chart(fig, use_container_width=True)

    # Live ML Correction Test
    if model_info["is_trained"]:
        st.markdown("---")
        st.subheader("🧪 Live ML-Korrektur Test")

        with st.expander("Test mit eigenen Werten"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Heimteam**")
                home_position = st.number_input(
                    "Position", 1, 18, 5, key="test_home_pos"
                )
                home_games = st.number_input("Spiele", 1, 34, 20, key="test_home_games")
                home_points = st.number_input(
                    "Punkte", 0, 102, 35, key="test_home_points"
                )

            with col2:
                st.markdown("**Auswärtsteam**")
                away_position = st.number_input(
                    "Position", 1, 18, 12, key="test_away_pos"
                )
                away_games = st.number_input("Spiele", 1, 34, 20, key="test_away_games")
                away_points = st.number_input(
                    "Punkte", 0, 102, 20, key="test_away_points"
                )

            if st.button("🔬 Korrektur berechnen"):
                from data.models import TeamStats

                # Erstelle dummy TeamStats
                home_team = TeamStats(
                    name="Test Heim",
                    position=home_position,
                    games=home_games,
                    points=home_points,
                    wins=0,
                    draws=0,
                    losses=0,
                    goals_for=0,
                    goals_against=0,
                    goal_diff=0,
                    form_points=0,
                    form_goals_for=0,
                    form_goals_against=0,
                    ha_points=0,
                    ha_goals_for=0,
                    ha_goals_against=0,
                    ppg_overall=home_points / home_games,
                    ppg_ha=0,
                    avg_goals_match=0,
                    avg_goals_match_ha=0,
                    goals_scored_per_match=0,
                    goals_conceded_per_match=0,
                    goals_scored_per_match_ha=0,
                    goals_conceded_per_match_ha=0,
                    btts_yes_overall=0,
                    btts_yes_ha=0,
                    cs_yes_overall=0,
                    cs_yes_ha=0,
                    fts_yes_overall=0,
                    fts_yes_ha=0,
                    xg_for=0,
                    xg_against=0,
                    xg_for_ha=0,
                    xg_against_ha=0,
                    shots_per_match=0,
                    shots_on_target=0,
                    conversion_rate=0,
                    possession=0,
                )

                away_team = TeamStats(
                    name="Test Auswärts",
                    position=away_position,
                    games=away_games,
                    points=away_points,
                    wins=0,
                    draws=0,
                    losses=0,
                    goals_for=0,
                    goals_against=0,
                    goal_diff=0,
                    form_points=0,
                    form_goals_for=0,
                    form_goals_against=0,
                    ha_points=0,
                    ha_goals_for=0,
                    ha_goals_against=0,
                    ppg_overall=away_points / away_games,
                    ppg_ha=0,
                    avg_goals_match=0,
                    avg_goals_match_ha=0,
                    goals_scored_per_match=0,
                    goals_conceded_per_match=0,
                    goals_scored_per_match_ha=0,
                    goals_conceded_per_match_ha=0,
                    btts_yes_overall=0,
                    btts_yes_ha=0,
                    cs_yes_overall=0,
                    cs_yes_ha=0,
                    fts_yes_overall=0,
                    fts_yes_ha=0,
                    xg_for=0,
                    xg_against=0,
                    xg_for_ha=0,
                    xg_against_ha=0,
                    shots_per_match=0,
                    shots_on_target=0,
                    conversion_rate=0,
                    possession=0,
                )

                correction = model.predict_correction(home_team, away_team, "2024-01-15")

                if correction["is_trained"]:
                    col_a, col_b, col_c = st.columns(3)

                    col_a.metric(
                        "Heim-Korrektur", f"{correction['home_correction']:.3f}"
                    )
                    col_b.metric(
                        "Auswärts-Korrektur", f"{correction['away_correction']:.3f}"
                    )
                    col_c.metric("Konfidenz", f"{correction['confidence']:.1%}")

                    st.success(f"✅ {correction['message']}")

                    # Beispiel
                    st.markdown("---")
                    st.markdown("**Beispiel-Anwendung:**")
                    st.caption(
                        f"Wenn μ_home vorher 1.8 war → nach ML: {1.8 * correction['home_correction']:.2f}"
                    )
                    st.caption(
                        f"Wenn μ_away vorher 1.2 war → nach ML: {1.2 * correction['away_correction']:.2f}"
                    )

                else:
                    st.error(correction["message"])
