"""
Historical Data Management UI
"""

import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from data.models import TeamStats
from models.tracking import (
    save_historical_match,
    load_historical_matches_from_sheets,
    get_tracking_sheet_id,
    connect_to_sheets,
    create_historical_sheet,
)


def create_demo_historical_data():
    """
    Erstellt 30 Demo-historische Matches für Testing
    """
    demo_matches = []
    team_names = [
        "Bayern München",
        "Borussia Dortmund",
        "RB Leipzig",
        "Bayer Leverkusen",
        "Union Berlin",
        "SC Freiburg",
        "Eintracht Frankfurt",
        "VfL Wolfsburg",
        "Borussia Mönchengladbach",
        "FC Augsburg",
        "VfB Stuttgart",
        "Werder Bremen",
        "TSG Hoffenheim",
        "1. FC Köln",
        "Mainz 05",
        "Hertha BSC",
        "VfL Bochum",
        "FC Schalke 04",
    ]

    for i in range(30):
        home_idx = random.randint(0, len(team_names) - 1)
        away_idx = random.randint(0, len(team_names) - 1)
        while away_idx == home_idx:
            away_idx = random.randint(0, len(team_names) - 1)

        home_position = random.randint(1, 18)
        away_position = random.randint(1, 18)

        home_games = random.randint(15, 30)
        away_games = random.randint(15, 30)

        home_points = random.randint(10, min(home_games * 3, 70))
        away_points = random.randint(10, min(away_games * 3, 70))

        predicted_mu_home = round(random.uniform(0.8, 2.5), 2)
        predicted_mu_away = round(random.uniform(0.8, 2.5), 2)

        actual_home_goals = random.randint(0, 4)
        actual_away_goals = random.randint(0, 4)

        actual_mu_home = float(actual_home_goals)
        actual_mu_away = float(actual_away_goals)

        match_date = (datetime.now() - timedelta(days=random.randint(1, 180))).strftime(
            "%Y-%m-%d"
        )

        home_team = TeamStats(
            name=team_names[home_idx],
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
            name=team_names[away_idx],
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

        match_data = {
            "home_team": home_team,
            "away_team": away_team,
            "predicted_mu_home": predicted_mu_home,
            "predicted_mu_away": predicted_mu_away,
            "actual_mu_home": actual_mu_home,
            "actual_mu_away": actual_mu_away,
            "actual_score": f"{actual_home_goals}:{actual_away_goals}",
            "competition": "Bundesliga",
            "date": match_date,
        }

        demo_matches.append(match_data)

    return demo_matches


def auto_create_historical_from_predictions():
    """
    Konvertiert COMPLETED Predictions zu Historical Data
    """
    sheet_id = get_tracking_sheet_id()
    if not sheet_id:
        st.error("❌ Google Sheets nicht konfiguriert")
        return 0

    service = connect_to_sheets(readonly=True)
    if not service:
        return 0

    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range="PREDICTIONS!A:W")
            .execute()
        )

        values = result.get("values", [])
        converted_count = 0

        for i, row in enumerate(values):
            if i == 0:
                continue

            if len(row) > 17 and row[16] == "COMPLETED":
                pass

        st.info(
            f"ℹ️ Diese Funktion ist noch in Entwicklung. Bitte manuell historische Daten eingeben."
        )
        return 0

    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        return 0


def check_historical_sheet():
    """
    Prüft ob HISTORICAL_DATA Sheet existiert und zeigt Status
    """
    sheet_id = get_tracking_sheet_id()
    if not sheet_id:
        return False

    service = connect_to_sheets(readonly=True)
    if not service:
        return False

    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range="HISTORICAL_DATA!A:A")
            .execute()
        )

        row_count = len(result.get("values", [])) - 1
        st.success(f"✅ HISTORICAL_DATA Sheet existiert ({row_count} Einträge)")
        return True

    except:
        st.warning("⚠️ HISTORICAL_DATA Sheet existiert noch nicht")

        if st.button("🔧 Sheet jetzt erstellen"):
            if create_historical_sheet(service, sheet_id):
                st.success("✅ Sheet erstellt!")
                st.rerun()
            else:
                st.error("❌ Fehler beim Erstellen")

        return False


def add_historical_match_ui():
    """
    UI für das Hinzufügen historischer Match-Daten
    """
    st.subheader("📚 Historische Trainings-Daten")

    # Quick Start Buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🎲 30 Demo-Daten erstellen", use_container_width=True):
            with st.spinner("Erstelle Demo-Daten..."):
                demo_matches = create_demo_historical_data()

                success_count = 0
                for match in demo_matches:
                    if save_historical_match(match):
                        success_count += 1

                st.success(f"✅ {success_count}/30 Demo-Matches gespeichert!")
                st.balloons()

    with col2:
        if st.button("🔄 Auto-Create from PREDICTIONS", use_container_width=True):
            count = auto_create_historical_from_predictions()
            if count > 0:
                st.success(f"✅ {count} Matches konvertiert!")

    with col3:
        if st.button("🔍 Sheet Status prüfen", use_container_width=True):
            check_historical_sheet()

    st.markdown("---")

    # Manuelle Eingabe
    st.markdown("### ✏️ Manuell historisches Match hinzufügen")

    with st.form("add_historical_match"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Heimteam**")
            home_name = st.text_input("Name", key="home_name")
            home_position = st.number_input("Position", 1, 18, 5, key="home_pos")
            home_points = st.number_input("Punkte", 0, 102, 30, key="home_points")
            home_games = st.number_input("Spiele", 1, 34, 20, key="home_games")
            actual_home_goals = st.number_input("Tatsächliche Tore", 0, 10, 2, key="home_goals")

        with col2:
            st.markdown("**Auswärtsteam**")
            away_name = st.text_input("Name", key="away_name")
            away_position = st.number_input("Position", 1, 18, 10, key="away_pos")
            away_points = st.number_input("Punkte", 0, 102, 25, key="away_points")
            away_games = st.number_input("Spiele", 1, 34, 20, key="away_games")
            actual_away_goals = st.number_input("Tatsächliche Tore", 0, 10, 1, key="away_goals")

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            match_date = st.date_input("Match-Datum")
            competition = st.text_input("Wettbewerb", value="Bundesliga")

        with col_b:
            predicted_mu_home = st.number_input(
                "Vorhergesagter μ Heim", 0.0, 5.0, 1.8, step=0.1
            )
            predicted_mu_away = st.number_input(
                "Vorhergesagter μ Auswärts", 0.0, 5.0, 1.2, step=0.1
            )

        # Auto-fill actual μ
        actual_mu_home = float(actual_home_goals)
        actual_mu_away = float(actual_away_goals)

        st.caption(f"Tatsächliche μ werden automatisch gesetzt: Heim={actual_mu_home}, Auswärts={actual_mu_away}")

        # Berechne Korrektur-Faktoren
        home_correction = actual_mu_home / predicted_mu_home if predicted_mu_home > 0 else 1.0
        away_correction = actual_mu_away / predicted_mu_away if predicted_mu_away > 0 else 1.0

        st.info(f"📊 Korrektur-Faktoren: Heim={home_correction:.3f}, Auswärts={away_correction:.3f}")

        submitted = st.form_submit_button("💾 Historisches Match speichern", use_container_width=True)

        if submitted:
            if not home_name or not away_name:
                st.error("❌ Bitte beide Team-Namen eingeben!")
            else:
                home_team = TeamStats(
                    name=home_name,
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
                    name=away_name,
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

                match_data = {
                    "home_team": home_team,
                    "away_team": away_team,
                    "predicted_mu_home": predicted_mu_home,
                    "predicted_mu_away": predicted_mu_away,
                    "actual_mu_home": actual_mu_home,
                    "actual_mu_away": actual_mu_away,
                    "actual_score": f"{actual_home_goals}:{actual_away_goals}",
                    "competition": competition,
                    "date": match_date.strftime("%Y-%m-%d"),
                }

                if save_historical_match(match_data):
                    st.success(f"✅ {home_name} vs {away_name} gespeichert!")
                    st.balloons()
                else:
                    st.error("❌ Fehler beim Speichern")

    # Zeige existierende Daten
    st.markdown("---")
    st.markdown("### 📋 Existierende historische Daten")

    historical_matches = load_historical_matches_from_sheets()

    if historical_matches:
        st.info(f"📊 {len(historical_matches)} historische Matches geladen")

        # Zeige erste 20
        display_matches = historical_matches[:20]

        data = []
        for match in display_matches:
            home_team = match.get("home_team")
            away_team = match.get("away_team")

            # Sicherer Zugriff auf Namen
            if hasattr(home_team, "name"):
                home_name = home_team.name
            elif isinstance(home_team, dict):
                home_name = home_team.get("name", "Unknown")
            else:
                home_name = "Unknown"

            if hasattr(away_team, "name"):
                away_name = away_team.name
            elif isinstance(away_team, dict):
                away_name = away_team.get("name", "Unknown")
            else:
                away_name = "Unknown"

            data.append(
                {
                    "Match": f"{home_name} vs {away_name}",
                    "Datum": match.get("date", ""),
                    "Score": match.get("actual_score", ""),
                    "Pred μ H": match.get("predicted_mu_home", 0),
                    "Pred μ A": match.get("predicted_mu_away", 0),
                    "Act μ H": match.get("actual_mu_home", 0),
                    "Act μ A": match.get("actual_mu_away", 0),
                }
            )

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        if len(historical_matches) > 20:
            st.caption(f"Zeige erste 20 von {len(historical_matches)} Matches")

    else:
        st.info("Noch keine historischen Daten vorhanden")
