"""
Tracking-Funktionen für Google Sheets (Predictions, Historical Data, Extended Data)
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional
from data.google_sheets import connect_to_sheets, get_tracking_sheet_id
from data.models import MatchData, ExtendedMatchData, TeamStats


def save_prediction_to_sheets(
    match_info: Dict,
    probabilities: Dict,
    odds: Dict,
    risk_score: Dict,
    predicted_score: str,
    mu_info: Dict,
) -> bool:
    """
    Speichert eine Vorhersage in PREDICTIONS Sheet

    Args:
        match_info: Match-Informationen
        probabilities: Berechnete Wahrscheinlichkeiten
        odds: Wett-Quoten
        risk_score: Risiko-Score Informationen
        predicted_score: Vorhergesagtes Ergebnis
        mu_info: μ-Werte Informationen

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        if "tracking" not in st.secrets:
            st.warning("⚠️ Tracking nicht konfiguriert")
            return False

        sheet_id = get_tracking_sheet_id()
        if not sheet_id:
            st.warning("⚠️ sheet_id nicht gefunden")
            return False

        service = connect_to_sheets(readonly=False)
        if service is None:
            return False

        best_over_under = (
            "Over 2.5"
            if probabilities["over_25"] >= (100 - probabilities["over_25"])
            else "Under 2.5"
        )
        prob_over_under = max(probabilities["over_25"], 100 - probabilities["over_25"])
        odds_over_under = (
            odds["ou25"][0] if best_over_under == "Over 2.5" else odds["ou25"][1]
        )

        best_btts = (
            "BTTS Yes"
            if probabilities["btts_yes"] >= probabilities["btts_no"]
            else "BTTS No"
        )
        prob_btts = max(probabilities["btts_yes"], probabilities["btts_no"])
        odds_btts = odds["btts"][0] if best_btts == "BTTS Yes" else odds["btts"][1]

        probs_1x2 = [
            probabilities["home_win"],
            probabilities["draw"],
            probabilities["away_win"],
        ]
        markets_1x2 = ["Heimsieg", "Unentschieden", "Auswärtssieg"]
        best_idx = probs_1x2.index(max(probs_1x2))
        best_1x2 = markets_1x2[best_idx]
        prob_1x2 = probs_1x2[best_idx]
        odds_1x2_value = odds["1x2"][best_idx]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        match_str = f"{match_info['home']} vs {match_info['away']}"
        mu_total = mu_info.get("total", 0.0)

        version = "v6.0"  # Aktuelle Version

        values = [
            [
                timestamp,  # A: Timestamp
                version,  # B: Version
                match_str,  # C: Match
                predicted_score,  # D: Predicted_Score
                best_1x2,  # E: Predicted_1X2
                f"{prob_1x2:.1f}%",  # F: Probability_1X2
                best_over_under,  # G: Best_OverUnder
                f"{prob_over_under:.1f}%",  # H: Probability_OverUnder
                f"{odds_over_under:.2f}",  # I: Odds_OverUnder
                best_btts,  # J: Best_BTTS
                f"{prob_btts:.1f}%",  # K: Probability_BTTS
                f"{odds_btts:.2f}",  # L: Odds_BTTS
                f"{odds_1x2_value:.2f}",  # M: Odds_1X2
                str(risk_score["score"]),  # N: Risk_Score (1-5)
                risk_score["category"],  # O: Risk_Category
                f"{mu_total:.2f}",  # P: μ_Total
                "PENDING",  # Q: Status
                "",  # R: Actual_Score
                "",  # S: Actual_Home
                "",  # T: Actual_Away
                "",  # U: Goals_Total
                "",  # V: BTTS_Actual
                "",  # W: Over25_Actual
            ]
        ]

        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=sheet_id,
                range="PREDICTIONS!A:W",
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )

        st.success(f"✅ Vorhersage ({version}) gespeichert!")
        return True

    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {str(e)}")
        return False


def update_match_result_in_sheets(match_str: str, actual_score: str) -> bool:
    """
    Aktualisiert das tatsächliche Ergebnis in PREDICTIONS Sheet

    Args:
        match_str: Match-String (z.B. "Bayern vs Dortmund")
        actual_score: Tatsächliches Ergebnis (z.B. "2:1")

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        service = connect_to_sheets(readonly=False)
        if service is None:
            return False

        home_goals, away_goals = map(int, actual_score.split(":"))
        goals_total = home_goals + away_goals
        btts_actual = "TRUE" if home_goals > 0 and away_goals > 0 else "FALSE"
        over25_actual = "TRUE" if goals_total > 2.5 else "FALSE"

        sheet_id = get_tracking_sheet_id()
        if not sheet_id:
            return False

        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range="PREDICTIONS!A:W")
            .execute()
        )

        values = result.get("values", [])

        for i, row in enumerate(values):
            if i == 0:
                continue

            if len(row) > 2 and match_str in row[2]:
                update_range = f"PREDICTIONS!R{i + 1}:W{i + 1}"
                update_values = [
                    [
                        actual_score,
                        str(home_goals),
                        str(away_goals),
                        str(goals_total),
                        btts_actual,
                        over25_actual,
                    ]
                ]

                body = {"values": update_values}
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=update_range,
                    valueInputOption="USER_ENTERED",
                    body=body,
                ).execute()

                status_range = f"PREDICTIONS!Q{i + 1}"
                status_body = {"values": [["COMPLETED"]]}
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=status_range,
                    valueInputOption="USER_ENTERED",
                    body=status_body,
                ).execute()

                return True

        return False

    except Exception as e:
        st.error(f"❌ Fehler beim Eintragen des Ergebnisses: {str(e)}")
        return False


def get_match_info_by_id(match_id: str) -> Optional[Dict]:
    """
    Holt Match-Informationen aus PREDICTIONS Sheet

    Args:
        match_id: Match-ID (Match-String oder Timestamp_Match)

    Returns:
        Dictionary mit Match-Informationen oder None
    """
    try:
        sheet_id = get_tracking_sheet_id()
        if not sheet_id:
            return None

        service = connect_to_sheets(readonly=True)
        if service is None:
            return None

        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range="PREDICTIONS!A:W")
            .execute()
        )

        values = result.get("values", [])

        for i, row in enumerate(values):
            if i == 0:
                continue

            if len(row) > 2 and row[2] == match_id:
                return {
                    "match": row[2],
                    "predicted_score": row[3] if len(row) > 3 else "",
                    "date": row[0] if len(row) > 0 else "",
                    "risk_score": row[13] if len(row) > 13 else "",
                }

            row_id = f"{row[0]}_{row[2]}" if len(row) > 2 else ""
            if row_id == match_id:
                return {
                    "match": row[2],
                    "predicted_score": row[3] if len(row) > 3 else "",
                    "date": row[0],
                    "risk_score": row[13] if len(row) > 13 else "",
                }

        return None

    except Exception as e:
        st.error(f"❌ Fehler beim Laden der Match-Info: {e}")
        return None


def save_historical_match(historical_match: Dict) -> bool:
    """
    Speichert ein historisches Match in HISTORICAL_DATA Sheet

    Args:
        historical_match: Dictionary mit historischen Match-Daten

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        if "tracking" not in st.secrets:
            st.warning("⚠️ Tracking nicht konfiguriert")
            return False

        sheet_id = get_tracking_sheet_id()
        if not sheet_id:
            st.error("❌ Keine Google Sheets ID gefunden")
            return False

        service = connect_to_sheets(readonly=False)
        if service is None:
            st.error("❌ Keine Verbindung zu Google Sheets")
            return False

        # Extrahiere Daten
        home_team = historical_match.get("home_team")
        away_team = historical_match.get("away_team")

        # Hole Namen - sicher für TeamStats Objekte und Dictionaries
        if hasattr(home_team, "name"):
            home_name = home_team.name
        elif isinstance(home_team, dict):
            home_name = home_team.get("name", "Unbekannt")
        else:
            home_name = "Unbekannt"

        if hasattr(away_team, "name"):
            away_name = away_team.name
        elif isinstance(away_team, dict):
            away_name = away_team.get("name", "Unbekannt")
        else:
            away_name = "Unbekannt"

        # Hole weitere Attribute
        if hasattr(home_team, "position"):
            home_position = home_team.position
            home_games = home_team.games
            home_points = home_team.points
        elif isinstance(home_team, dict):
            home_position = home_team.get("position", 10)
            home_games = home_team.get("games", 20)
            home_points = home_team.get("points", 30)
        else:
            home_position = 10
            home_games = 20
            home_points = 30

        if hasattr(away_team, "position"):
            away_position = away_team.position
            away_games = away_team.games
            away_points = away_team.points
        elif isinstance(away_team, dict):
            away_position = away_team.get("position", 15)
            away_games = away_team.get("games", 20)
            away_points = away_team.get("points", 25)
        else:
            away_position = 15
            away_games = 20
            away_points = 25

        predicted_mu_home = historical_match.get("predicted_mu_home", 1.8)
        predicted_mu_away = historical_match.get("predicted_mu_away", 1.2)
        actual_mu_home = historical_match.get("actual_mu_home", 2.0)
        actual_mu_away = historical_match.get("actual_mu_away", 1.0)
        actual_score = historical_match.get("actual_score", "0:0")
        competition = historical_match.get("competition", "Unbekannt")
        match_date = historical_match.get("date", datetime.now().strftime("%Y-%m-%d"))

        # Berechnungen
        home_ppg = home_points / home_games if home_games > 0 else 0
        away_ppg = away_points / away_games if away_games > 0 else 0

        home_correction = (
            actual_mu_home / predicted_mu_home if predicted_mu_home > 0 else 1.0
        )
        away_correction = (
            actual_mu_away / predicted_mu_away if predicted_mu_away > 0 else 1.0
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Prüfe ob HISTORICAL_DATA Sheet existiert
        try:
            service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range="HISTORICAL_DATA!A:A"
            ).execute()
        except:
            # Sheet existiert nicht, erstelle es
            create_historical_sheet(service, sheet_id)

        # Erstelle Datenzeile
        values = [
            [
                timestamp,
                str(match_date),
                home_name,
                away_name,
                competition,
                str(home_position),
                str(away_position),
                str(home_games),
                str(away_games),
                str(home_points),
                str(away_points),
                f"{home_ppg:.3f}",
                f"{away_ppg:.3f}",
                f"{predicted_mu_home:.3f}",
                f"{predicted_mu_away:.3f}",
                f"{actual_mu_home:.3f}",
                f"{actual_mu_away:.3f}",
                f"{home_correction:.3f}",
                f"{away_correction:.3f}",
                actual_score,
                "",  # Notes
            ]
        ]

        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=sheet_id,
                range="HISTORICAL_DATA!A:U",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )

        st.success(f"✅ {home_name} vs {away_name} gespeichert!")
        return True

    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {str(e)}")
        return False


def create_historical_sheet(service, sheet_id: str) -> bool:
    """
    Erstellt das HISTORICAL_DATA Sheet mit Headern

    Args:
        service: Google Sheets Service
        sheet_id: Sheet ID

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        # Sheet hinzufügen
        body = {
            "requests": [{"addSheet": {"properties": {"title": "HISTORICAL_DATA"}}}]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()

        # Header hinzufügen
        headers = [
            "Timestamp",
            "Date",
            "Home_Team",
            "Away_Team",
            "Competition",
            "Home_Position",
            "Away_Position",
            "Home_Games",
            "Away_Games",
            "Home_Points",
            "Away_Points",
            "Home_PPG",
            "Away_PPG",
            "Predicted_MU_Home",
            "Predicted_MU_Away",
            "Actual_MU_Home",
            "Actual_MU_Away",
            "Home_Correction",
            "Away_Correction",
            "Actual_Score",
            "Notes",
        ]

        body = {"values": [headers]}
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="HISTORICAL_DATA!A:U",
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()

        return True
    except Exception as e:
        st.error(f"❌ Fehler beim Erstellen des HISTORICAL_DATA Sheets: {e}")
        return False


def save_historical_directly(
    match_data: MatchData,
    actual_home_goals: int,
    actual_away_goals: int,
    predicted_mu_home: float,
    predicted_mu_away: float,
) -> bool:
    """
    Speichert historische Daten direkt nach der Analyse

    Args:
        match_data: MatchData Objekt
        actual_home_goals: Tatsächliche Heimtore
        actual_away_goals: Tatsächliche Auswärtstore
        predicted_mu_home: Vorhergesagter μ-Wert Heim
        predicted_mu_away: Vorhergesagter μ-Wert Auswärts

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        if "tracking" not in st.secrets:
            st.warning("⚠️ Tracking nicht konfiguriert")
            return False

        sheet_id = get_tracking_sheet_id()
        if not sheet_id:
            st.error("❌ Keine Google Sheets ID gefunden")
            return False

        service = connect_to_sheets(readonly=False)
        if service is None:
            st.error("❌ Keine Verbindung zu Google Sheets")
            return False

        # Historische Daten speichern
        actual_mu_home = float(actual_home_goals)
        actual_mu_away = float(actual_away_goals)

        home_correction = (
            actual_mu_home / predicted_mu_home if predicted_mu_home > 0 else 1.0
        )
        away_correction = (
            actual_mu_away / predicted_mu_away if predicted_mu_away > 0 else 1.0
        )

        home_ppg = match_data.home_team.points / max(match_data.home_team.games, 1)
        away_ppg = match_data.away_team.points / max(match_data.away_team.games, 1)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        actual_score = f"{actual_home_goals}:{actual_away_goals}"

        # Prüfe ob HISTORICAL_DATA Sheet existiert
        try:
            service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range="HISTORICAL_DATA!A:A"
            ).execute()
        except:
            create_historical_sheet(service, sheet_id)

        values = [
            [
                timestamp,
                str(match_data.date),
                match_data.home_team.name,
                match_data.away_team.name,
                match_data.competition,
                int(match_data.home_team.position),
                int(match_data.away_team.position),
                int(match_data.home_team.games),
                int(match_data.away_team.games),
                int(match_data.home_team.points),
                int(match_data.away_team.points),
                round(home_ppg, 3),
                round(away_ppg, 3),
                round(predicted_mu_home, 3),
                round(predicted_mu_away, 3),
                round(actual_mu_home, 3),
                round(actual_mu_away, 3),
                round(home_correction, 3),
                round(away_correction, 3),
                actual_score,
                "Direkt nach Analyse gespeichert",
            ]
        ]

        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=sheet_id,
                range="HISTORICAL_DATA!A:U",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )

        # Auch PREDICTIONS als COMPLETED markieren
        match_str = f"{match_data.home_team.name} vs {match_data.away_team.name}"
        update_match_result_in_sheets(match_str, actual_score)

        st.success(
            f"✅ Historische Daten für {match_data.home_team.name} vs {match_data.away_team.name} gespeichert!"
        )
        return True

    except Exception as e:
        st.error(f"❌ Fehler beim direkten Speichern: {str(e)}")
        return False


def load_historical_matches_from_sheets() -> List[Dict]:
    """
    Lädt historische Matches für ML-Training

    Returns:
        Liste von historischen Match-Dictionaries
    """
    try:
        sheet_id = get_tracking_sheet_id()
        if not sheet_id:
            return []

        service = connect_to_sheets(readonly=True)
        if service is None:
            return []

        # Versuche von HISTORICAL_DATA zu laden
        try:
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheet_id, range="HISTORICAL_DATA!A:T")
                .execute()
            )
        except:
            # Fallback: Lade von PREDICTIONS mit COMPLETED Status
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheet_id, range="PREDICTIONS!A:W")
                .execute()
            )

        values = result.get("values", [])
        if len(values) <= 1:
            return []

        historical_matches = []
        headers = values[0] if values else []

        for i, row in enumerate(values):
            if i == 0:
                continue

            try:
                if "HISTORICAL_DATA" in result.get("range", ""):
                    if len(row) >= 20:
                        home_team = TeamStats(
                            name=row[2],
                            position=int(row[5]),
                            games=int(row[7]),
                            points=int(row[9]),
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
                            ppg_overall=float(row[11]),
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
                            name=row[3],
                            position=int(row[6]),
                            games=int(row[8]),
                            points=int(row[10]),
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
                            ppg_overall=float(row[12]),
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
                            "date": row[1],
                            "predicted_mu_home": float(row[13]),
                            "predicted_mu_away": float(row[14]),
                            "actual_mu_home": float(row[15]),
                            "actual_mu_away": float(row[16]),
                            "home_correction": float(row[17]),
                            "away_correction": float(row[18]),
                            "actual_score": row[19] if len(row) > 19 else "",
                        }

                        historical_matches.append(match_data)

            except Exception as e:
                continue

        return historical_matches

    except Exception as e:
        st.error(f"Fehler beim Laden historischer Daten: {e}")
        return []
