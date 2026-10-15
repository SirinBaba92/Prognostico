"""
Export-Funktionen für Google Sheets (Wettquoten Tipps)
"""

import time
import streamlit as st
from datetime import datetime
from googleapiclient.errors import HttpError
from data.google_sheets import connect_to_sheets
from config.constants import EXPORT_SHEET_ID

def _execute_with_retry(request, max_retries: int = 5, base_delay: float = 5.0):
    """
    Führt einen Google-API-Request aus und wiederholt ihn bei
    HTTP 429 (Quota exceeded) automatisch mit exponentiellem Backoff.
    """
    for attempt in range(max_retries):
        try:
            return request.execute()
        except HttpError as e:
            status = getattr(e, "status_code", None)
            if status is None:
                status = getattr(getattr(e, "resp", None), "status", None)
            is_rate_limit = status == 429
            if not is_rate_limit or attempt == max_retries - 1:
                raise
            delay = base_delay * (2**attempt)
            st.info(
                f"⏳ Google-API-Limit erreicht, warte {delay:.0f}s und versuche erneut "
                f"({attempt + 1}/{max_retries})..."
            )
            time.sleep(delay)

def export_analysis_to_sheets(result: dict, actual_score: str = None) -> bool:
    """
    Exportiert Analyse-Ergebnis zu Google Sheets (Wettquoten Tipps).

    Quoten-Spalten:
      D = Smart-Quote (immer geschrieben, passend zum Smart-Tipp)
      E = ML-Quote    (immer geschrieben, passend zum ML-Tipp)

    Beide Quoten werden UNABHÄNGIG voneinander geschrieben — auch bei
    Disagreement der Modelle. Das ist nötig, damit die Smart/ML-Performance-
    Analyse den ROI pro Modell auf seinen eigenen Tipps rechnen kann.
    """
    try:
        service = connect_to_sheets(readonly=False)
        if not service:
            st.error("❌ Keine Verbindung zu Google Sheets")
            return False

        match_date_str = result["match_info"]["date"]
        sheet_tab_name = match_date_str

        sheet_metadata = _execute_with_retry(
            service.spreadsheets().get(spreadsheetId=EXPORT_SHEET_ID)
        )
        sheets = sheet_metadata.get("sheets", [])
        sheet_titles = [s["properties"]["title"] for s in sheets]

        if sheet_tab_name not in sheet_titles:
            st.error(f"❌ Tabellenblatt '{sheet_tab_name}' existiert nicht!")
            st.info(f"💡 Verfügbare Blätter: {', '.join(sheet_titles[:5])}...")
            return False

        match_name = f"{result['match_info']['home']} vs {result['match_info']['away']}"

        if actual_score:
            next_row = find_match_row(service, sheet_tab_name, match_name)
            if next_row is None:
                next_row = find_next_free_row(service, sheet_tab_name)
        else:
            next_row = find_next_free_row(service, sheet_tab_name)

        if next_row is None:
            st.error("❌ Fehler beim Finden der passenden Zeile")
            return False

        # ===================================================================
        # SMART PREDICTIONS
        # ===================================================================
        predicted_score = result.get("predicted_score", "")
        if isinstance(predicted_score, str):
            predicted_score = predicted_score.replace(":", "-").strip()

        probs = result["probabilities"]

        prob_1x2_home = probs["home_win"]
        prob_1x2_draw = probs["draw"]
        prob_1x2_away = probs["away_win"]
        best_1x2_prob = max(prob_1x2_home, prob_1x2_draw, prob_1x2_away)

        prob_over = probs["over_25"]
        prob_under = probs["under_25"]
        best_ou_prob = max(prob_over, prob_under)

        prob_btts_yes = probs["btts_yes"]
        prob_btts_no = probs["btts_no"]
        best_btts_prob = max(prob_btts_yes, prob_btts_no)

        if best_1x2_prob == prob_1x2_home:
            smart_1x2_prediction = "HOME"
            smart_1x2_label = "1"
        elif best_1x2_prob == prob_1x2_draw:
            smart_1x2_prediction = "DRAW"
            smart_1x2_label = "X"
        else:
            smart_1x2_prediction = "AWAY"
            smart_1x2_label = "2"

        if best_ou_prob == prob_over:
            smart_ou_prediction = "OVER"
            smart_ou_label = "Over 2.5"
        else:
            smart_ou_prediction = "UNDER"
            smart_ou_label = "Under 2.5"

        if best_btts_prob == prob_btts_yes:
            smart_btts_prediction = "YES"
            smart_btts_label = "Yes"
        else:
            smart_btts_prediction = "NO"
            smart_btts_label = "No"

        # ===================================================================
        # ML PREDICTIONS
        # ===================================================================
        ml_1x2_prob = None
        ml_ou_prob = None
        ml_btts_prob = None
        ml_score = ""
        ml_1x2_prediction = None
        ml_ou_prediction = None
        ml_btts_prediction = None
        ml_1x2_label = ""
        ml_ou_label = ""
        ml_btts_label = ""

        try:
            from ml.football_ml_models import get_ml_models
            from ml.scoreline_predictor import ScorelinePredictor
            from ui.sheets_ml_integration import convert_match_data_to_features
            from data.supabase_client import get_full_match_bundle
            from data.supabase_mapper import map_bundle_to_match_data

            match_id = result.get('_match_id')

            if match_id:
                bundle = get_full_match_bundle(match_id)
                if bundle:
                    match_data = map_bundle_to_match_data(bundle)
                    features = convert_match_data_to_features(match_data)

                    ml_models = get_ml_models()
                    if ml_models.models_loaded:
                        predictions = ml_models.predict_all(features, use_odds=True)

                        if '1x2' in predictions:
                            ml_1x2_prob = predictions['1x2']['confidence']
                            ml_1x2_prediction = predictions['1x2']['prediction']
                            if 'HOME' in ml_1x2_prediction:
                                ml_1x2_label = "1"
                            elif 'DRAW' in ml_1x2_prediction:
                                ml_1x2_label = "X"
                            else:
                                ml_1x2_label = "2"

                        if 'over_under' in predictions:
                            ml_ou_prob = predictions['over_under']['confidence']
                            pred = predictions['over_under']['prediction']
                            ml_ou_prediction = "OVER" if "OVER" in pred else "UNDER"
                            ml_ou_label = "Over 2.5" if "OVER" in pred else "Under 2.5"

                        if 'btts' in predictions:
                            ml_btts_prob = predictions['btts']['confidence']
                            pred = predictions['btts']['prediction']
                            ml_btts_prediction = "YES" if "YES" in pred else "NO"
                            ml_btts_label = "Yes" if "YES" in pred else "No"

                        scoreline_pred = ScorelinePredictor()

                        home_xg = match_data.home_team.goals_scored_per_match if hasattr(match_data.home_team, 'goals_scored_per_match') else 1.5
                        away_xg = match_data.away_team.goals_scored_per_match if hasattr(match_data.away_team, 'goals_scored_per_match') else 1.3

                        all_scorelines = scoreline_pred.predict_scorelines(home_xg, away_xg, top_n=20)

                        x2_pred = ml_1x2_prediction.replace(' WIN', '').replace('DRAW', 'DRAW') if ml_1x2_prediction else 'HOME'
                        ou_pred = ml_ou_prediction if ml_ou_prediction else 'OVER'
                        btts_pred = ml_btts_prediction if ml_btts_prediction else 'NO'

                        best_scoreline = scoreline_pred.get_most_likely_scoreline_for_markets(
                            x2_pred, ou_pred, btts_pred, all_scorelines
                        )

                        if not best_scoreline and all_scorelines:
                            try:
                                from app import choose_consistent_predicted_score

                                ml_probs = {}
                                if '1x2' in predictions:
                                    pred = predictions['1x2']['prediction']
                                    conf = predictions['1x2']['confidence']
                                    if 'HOME' in pred:
                                        ml_probs['home_win'] = conf
                                        ml_probs['draw'] = (100 - conf) / 2
                                        ml_probs['away_win'] = (100 - conf) / 2
                                    elif 'DRAW' in pred:
                                        ml_probs['draw'] = conf
                                        ml_probs['home_win'] = (100 - conf) / 2
                                        ml_probs['away_win'] = (100 - conf) / 2
                                    else:
                                        ml_probs['away_win'] = conf
                                        ml_probs['home_win'] = (100 - conf) / 2
                                        ml_probs['draw'] = (100 - conf) / 2

                                if 'over_under' in predictions:
                                    pred = predictions['over_under']['prediction']
                                    conf = predictions['over_under']['confidence']
                                    if 'OVER' in pred:
                                        ml_probs['over_25'] = conf
                                        ml_probs['under_25'] = 100 - conf
                                    else:
                                        ml_probs['under_25'] = conf
                                        ml_probs['over_25'] = 100 - conf

                                if 'btts' in predictions:
                                    pred = predictions['btts']['prediction']
                                    conf = predictions['btts']['confidence']
                                    if 'YES' in pred:
                                        ml_probs['btts_yes'] = conf
                                        ml_probs['btts_no'] = 100 - conf
                                    else:
                                        ml_probs['btts_no'] = conf
                                        ml_probs['btts_yes'] = 100 - conf

                                temp_result = {
                                    'scorelines': [(s['scoreline'], s['probability']) for s in all_scorelines],
                                    'probabilities': ml_probs
                                }

                                temp_result = choose_consistent_predicted_score(temp_result)
                                consistent_score = temp_result.get('predicted_score', '')

                                if consistent_score:
                                    for s in all_scorelines:
                                        if s['scoreline'] == consistent_score:
                                            best_scoreline = s
                                            break
                                    if not best_scoreline:
                                        best_scoreline = {'scoreline': consistent_score}
                            except:
                                pass

                        if not best_scoreline and all_scorelines:
                            best_scoreline = all_scorelines[0]

                        if best_scoreline:
                            ml_score = best_scoreline['scoreline']

        except Exception:
            pass

        # ===================================================================
        # QUOTEN DER GETIPPTEN AUSWAHL (SMART + ML, unabhängig)
        # ===================================================================
        odds_1x2_full = result["odds"]["1x2"]
        odds_ou_full = result["odds"]["ou25"]
        odds_btts_full = result["odds"]["btts"]

        label_to_index_1x2 = {"1": 0, "X": 1, "2": 2}

        smart_1x2_odds = odds_1x2_full[label_to_index_1x2[smart_1x2_label]]
        ml_1x2_odds = (
            odds_1x2_full[label_to_index_1x2[ml_1x2_label]] if ml_1x2_label else ""
        )

        smart_ou_odds = odds_ou_full[0] if smart_ou_prediction == "OVER" else odds_ou_full[1]
        if ml_ou_prediction == "OVER":
            ml_ou_odds = odds_ou_full[0]
        elif ml_ou_prediction == "UNDER":
            ml_ou_odds = odds_ou_full[1]
        else:
            ml_ou_odds = ""

        smart_btts_odds = odds_btts_full[0] if smart_btts_prediction == "YES" else odds_btts_full[1]
        if ml_btts_prediction == "YES":
            ml_btts_odds = odds_btts_full[0]
        elif ml_btts_prediction == "NO":
            ml_btts_odds = odds_btts_full[1]
        else:
            ml_btts_odds = ""

        def _fmt(v):
            if v == "" or v is None:
                return ""
            try:
                return f"{float(v):.2f}"
            except (TypeError, ValueError):
                return ""

        # ===================================================================
        # UPDATES
        # ===================================================================
        updates = [
            {"range": f"{sheet_tab_name}!B{next_row}", "values": [[match_name]]},

            {"range": f"{sheet_tab_name}!B{next_row + 2}", "values": [[smart_1x2_label]]},
            {"range": f"{sheet_tab_name}!C{next_row + 2}", "values": [[ml_1x2_label]]},

            {"range": f"{sheet_tab_name}!B{next_row + 3}", "values": [[f"{best_1x2_prob:.1f}%"]]},
            {"range": f"{sheet_tab_name}!C{next_row + 3}", "values": [[f"{ml_1x2_prob:.1f}%" if ml_1x2_prob else ""]]},
            {"range": f"{sheet_tab_name}!D{next_row + 3}", "values": [[_fmt(smart_1x2_odds)]]},
            {"range": f"{sheet_tab_name}!E{next_row + 3}", "values": [[_fmt(ml_1x2_odds)]]},

            {"range": f"{sheet_tab_name}!B{next_row + 4}", "values": [[smart_ou_label]]},
            {"range": f"{sheet_tab_name}!C{next_row + 4}", "values": [[ml_ou_label]]},

            {"range": f"{sheet_tab_name}!B{next_row + 5}", "values": [[f"{best_ou_prob:.1f}%"]]},
            {"range": f"{sheet_tab_name}!C{next_row + 5}", "values": [[f"{ml_ou_prob:.1f}%" if ml_ou_prob else ""]]},
            {"range": f"{sheet_tab_name}!D{next_row + 5}", "values": [[_fmt(smart_ou_odds)]]},
            {"range": f"{sheet_tab_name}!E{next_row + 5}", "values": [[_fmt(ml_ou_odds)]]},

            {"range": f"{sheet_tab_name}!B{next_row + 6}", "values": [[smart_btts_label]]},
            {"range": f"{sheet_tab_name}!C{next_row + 6}", "values": [[ml_btts_label]]},

            {"range": f"{sheet_tab_name}!B{next_row + 7}", "values": [[f"{best_btts_prob:.1f}%"]]},
            {"range": f"{sheet_tab_name}!C{next_row + 7}", "values": [[f"{ml_btts_prob:.1f}%" if ml_btts_prob else ""]]},
            {"range": f"{sheet_tab_name}!D{next_row + 7}", "values": [[_fmt(smart_btts_odds)]]},
            {"range": f"{sheet_tab_name}!E{next_row + 7}", "values": [[_fmt(ml_btts_odds)]]},

            {"range": f"{sheet_tab_name}!B{next_row + 8}", "values": [[predicted_score]]},
            {"range": f"{sheet_tab_name}!C{next_row + 8}", "values": [[ml_score]]},
        ]

        if actual_score:
            updates.append({"range": f"{sheet_tab_name}!G{next_row}", "values": [[actual_score]]})

        body = {"valueInputOption": "USER_ENTERED", "data": updates}

        _execute_with_retry(
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=EXPORT_SHEET_ID, body=body
            )
        )

        st.success(f"✅ Export erfolgreich! Zeile {next_row} in '{sheet_tab_name}'")
        return True

    except Exception as e:
        st.error(f"❌ Export-Fehler: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False

def find_next_free_row(service, sheet_tab_name: str) -> int:
    """Findet die nächste freie Zeile im 10er-Intervall (1, 11, 21, 31...)."""
    try:
        max_row = 2000
        result = _execute_with_retry(
            service.spreadsheets()
            .values()
            .get(spreadsheetId=EXPORT_SHEET_ID, range=f"{sheet_tab_name}!B1:B{max_row}")
        )

        values = result.get("values", [])

        def cell_value(row_1_indexed: int) -> str:
            idx = row_1_indexed - 1
            if idx < len(values) and values[idx]:
                return str(values[idx][0]).strip()
            return ""

        for start in range(1, max_row + 1, 10):
            if cell_value(start) == "":
                return start

        return max_row + 1

    except Exception as e:
        st.error(f"Fehler beim Finden der freien Zeile: {e}")
        return None

def find_match_row(service, sheet_tab_name: str, match_name: str) -> int | None:
    """Findet den Blockstart (1, 11, 21, ...) für einen bereits exportierten Match."""
    try:
        max_row = 2000
        resp = _execute_with_retry(
            service.spreadsheets()
            .values()
            .get(spreadsheetId=EXPORT_SHEET_ID, range=f"{sheet_tab_name}!B1:B{max_row}")
        )
        values = resp.get("values", [])

        def cell_value(row_1_indexed: int) -> str:
            idx = row_1_indexed - 1
            if idx < len(values) and values[idx]:
                return str(values[idx][0]).strip()
            return ""

        target = (match_name or "").strip()
        if not target:
            return None

        for start in range(1, max_row + 1, 10):
            if cell_value(start) == target:
                return start

        return None
    except Exception as e:
        st.error(f"Fehler beim Finden der Match-Zeile: {e}")
        return None






