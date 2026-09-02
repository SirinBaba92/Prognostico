"""
Export-Funktionen für Google Sheets (Wettquoten Tipps)
"""

import streamlit as st
from datetime import datetime
from data.google_sheets import connect_to_sheets
from config.constants import EXPORT_SHEET_ID


def export_analysis_to_sheets(result: dict, actual_score: str = None) -> bool:
    """
    Exportiert Analyse-Ergebnis zu Google Sheets (Wettquoten Tipps)
    Jetzt MIT ML Predictions und Konsens-Quoten!

    Args:
        result: Analyse-Ergebnis Dictionary
        actual_score: Tatsächliches Ergebnis falls bekannt (z.B. "2:1")

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        # Google Sheets Verbindung herstellen
        service = connect_to_sheets(readonly=False)
        if not service:
            st.error("❌ Keine Verbindung zu Google Sheets")
            return False

        # Match-Datum extrahieren
        match_date_str = result["match_info"]["date"]  # Format: "dd.mm.yyyy"

        # Konvertiere zu Sheet-Tab Format (dd.mm.yyyy bleibt gleich)
        sheet_tab_name = match_date_str

        # Prüfe ob Tab existiert
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=EXPORT_SHEET_ID).execute()
        )
        sheets = sheet_metadata.get("sheets", [])
        sheet_titles = [s["properties"]["title"] for s in sheets]

        if sheet_tab_name not in sheet_titles:
            st.error(f"❌ Tabellenblatt '{sheet_tab_name}' existiert nicht!")
            st.info(f"💡 Verfügbare Blätter: {', '.join(sheet_titles[:5])}...")
            return False

        # Bereite Daten vor
        match_name = f"{result['match_info']['home']} vs {result['match_info']['away']}"

        # Wenn ein tatsächliches Ergebnis übergeben wird, soll *dieselbe Match-Zeile*
        # (Blockstart B1/B11/B21/...) aktualisiert werden.
        # Falls der Match-Block noch nicht existiert, fällt es auf den nächsten freien Block zurück.
        if actual_score:
            next_row = find_match_row(service, sheet_tab_name, match_name)
            if next_row is None:
                next_row = find_next_free_row(service, sheet_tab_name)
        else:
            # Standard: nächsten freien Block nehmen
            next_row = find_next_free_row(service, sheet_tab_name)

        if next_row is None:
            st.error("❌ Fehler beim Finden der passenden Zeile")
            return False

        # ===================================================================
        # ALTE PREDICTIONS (SMART-PRECISION)
        # ===================================================================
        predicted_score = result.get("predicted_score", "")
        # Gewünschtes Format im Sheet: "1-0" statt "1:0"
        if isinstance(predicted_score, str):
            predicted_score = predicted_score.replace(":", "-").strip()

        probs = result["probabilities"]

        # Hole beste Predictions (IMMER, auch wenn unter Schwellenwert!)
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

        # Bestimme welche Prediction (für Quote-Matching UND Labels)
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

        # Versuche ML Predictions zu laden
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

                        # 1X2
                        if '1x2' in predictions:
                            ml_1x2_prob = predictions['1x2']['confidence']
                            ml_1x2_prediction = predictions['1x2']['prediction']  # HOME WIN, DRAW, AWAY WIN
                            # Label erstellen
                            if 'HOME' in ml_1x2_prediction:
                                ml_1x2_label = "1"
                            elif 'DRAW' in ml_1x2_prediction:
                                ml_1x2_label = "X"
                            else:
                                ml_1x2_label = "2"

                        # Over/Under
                        if 'over_under' in predictions:
                            ml_ou_prob = predictions['over_under']['confidence']
                            pred = predictions['over_under']['prediction']
                            ml_ou_prediction = "OVER" if "OVER" in pred else "UNDER"
                            # Label erstellen
                            ml_ou_label = "Over 2.5" if "OVER" in pred else "Under 2.5"

                        # BTTS
                        if 'btts' in predictions:
                            ml_btts_prob = predictions['btts']['confidence']
                            pred = predictions['btts']['prediction']
                            ml_btts_prediction = "YES" if "YES" in pred else "NO"
                            # Label erstellen
                            ml_btts_label = "Yes" if "YES" in pred else "No"

                        # Score - GLEICHE Logik wie Tab 1!
                        scoreline_pred = ScorelinePredictor()
                        
                        # xG aus match_data (wie Tab 6)
                        home_xg = match_data.home_team.goals_scored_per_match if hasattr(match_data.home_team, 'goals_scored_per_match') else 1.5
                        away_xg = match_data.away_team.goals_scored_per_match if hasattr(match_data.away_team, 'goals_scored_per_match') else 1.3
                        
                        # Generiere Scorelines
                        all_scorelines = scoreline_pred.predict_scorelines(home_xg, away_xg, top_n=20)
                        
                        # Bestimme ML Markets für Scoreline Match
                        x2_pred = ml_1x2_prediction.replace(' WIN', '').replace('DRAW', 'DRAW') if ml_1x2_prediction else 'HOME'
                        ou_pred = ml_ou_prediction if ml_ou_prediction else 'OVER'
                        btts_pred = ml_btts_prediction if ml_btts_prediction else 'NO'
                        
                        # Finde passendes Scoreline (wie Tab 1/6)
                        best_scoreline = scoreline_pred.get_most_likely_scoreline_for_markets(
                            x2_pred, ou_pred, btts_pred, all_scorelines
                        )
                        
                        # Fallback wenn kein Match
                        if not best_scoreline and all_scorelines:
                            # Nutze choose_consistent_predicted_score
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
                        
                        # Final Fallback
                        if not best_scoreline and all_scorelines:
                            best_scoreline = all_scorelines[0]
                        
                        # Setze ml_score
                        if best_scoreline:
                            ml_score = best_scoreline['scoreline']

        except Exception as e:
            # Silent fail - ML Predictions optional
            pass

        # ===================================================================
        # KONSENS-QUOTEN (nur wenn Schwellenwerte erreicht!)
        # ===================================================================
        # Hole Quoten aus extended_risk
        odds_1x2 = result["extended_risk"]["1x2"].get("odds", 0.0)
        odds_ou = result["extended_risk"]["over_under"]
        odds_btts = result["extended_risk"]["btts"]

        consensus_1x2_odds = ""
        consensus_ou_odds = ""
        consensus_btts_odds = ""

        # 1X2: Konsens wenn ALTE ≥50% UND Predictions matchen
        if best_1x2_prob >= 50 and ml_1x2_prediction:
            # Normalisiere ML Prediction
            ml_1x2_norm = ml_1x2_prediction.replace(" WIN", "").strip()
            if smart_1x2_prediction == ml_1x2_norm:
                consensus_1x2_odds = f"{odds_1x2:.2f}"

        # Over/Under: Konsens wenn ALTE ≥60% UND Predictions matchen
        if best_ou_prob >= 60 and ml_ou_prediction:
            if smart_ou_prediction == ml_ou_prediction:
                if smart_ou_prediction == "OVER":
                    consensus_ou_odds = f"{odds_ou.get('over', {}).get('odds', 0.0):.2f}"
                else:
                    consensus_ou_odds = f"{odds_ou.get('under', {}).get('odds', 0.0):.2f}"

        # BTTS: Konsens wenn ALTE ≥60% UND Predictions matchen
        if best_btts_prob >= 60 and ml_btts_prediction:
            if smart_btts_prediction == ml_btts_prediction:
                if smart_btts_prediction == "YES":
                    consensus_btts_odds = f"{odds_btts.get('yes', {}).get('odds', 0.0):.2f}"
                else:
                    consensus_btts_odds = f"{odds_btts.get('no', {}).get('odds', 0.0):.2f}"

        # ===================================================================
        # ERSTELLE UPDATES MIT LABELS
        # ===================================================================
        updates = [
            # Match Name
            {"range": f"{sheet_tab_name}!B{next_row}", "values": [[match_name]]},
            
            # ZEILE 3: 1X2 Labels
            {"range": f"{sheet_tab_name}!B{next_row + 2}", "values": [[smart_1x2_label]]},  # Alte Label
            {"range": f"{sheet_tab_name}!C{next_row + 2}", "values": [[ml_1x2_label]]},  # ML Label
            
            # ZEILE 4: 1X2 Percentages & Quote
            {"range": f"{sheet_tab_name}!B{next_row + 3}", "values": [[f"{best_1x2_prob:.1f}%"]]},  # Alte %
            {"range": f"{sheet_tab_name}!C{next_row + 3}", "values": [[f"{ml_1x2_prob:.1f}%" if ml_1x2_prob else ""]]},  # ML %
            {"range": f"{sheet_tab_name}!E{next_row + 3}", "values": [[consensus_1x2_odds]]},  # Konsens Quote
            
            # ZEILE 5: Over/Under Labels
            {"range": f"{sheet_tab_name}!B{next_row + 4}", "values": [[smart_ou_label]]},  # Alte Label
            {"range": f"{sheet_tab_name}!C{next_row + 4}", "values": [[ml_ou_label]]},  # ML Label
            
            # ZEILE 6: Over/Under Percentages & Quote
            {"range": f"{sheet_tab_name}!B{next_row + 5}", "values": [[f"{best_ou_prob:.1f}%"]]},  # Alte %
            {"range": f"{sheet_tab_name}!C{next_row + 5}", "values": [[f"{ml_ou_prob:.1f}%" if ml_ou_prob else ""]]},  # ML %
            {"range": f"{sheet_tab_name}!E{next_row + 5}", "values": [[consensus_ou_odds]]},  # Konsens Quote
            
            # ZEILE 7: BTTS Labels
            {"range": f"{sheet_tab_name}!B{next_row + 6}", "values": [[smart_btts_label]]},  # Alte Label
            {"range": f"{sheet_tab_name}!C{next_row + 6}", "values": [[ml_btts_label]]},  # ML Label
            
            # ZEILE 8: BTTS Percentages & Quote
            {"range": f"{sheet_tab_name}!B{next_row + 7}", "values": [[f"{best_btts_prob:.1f}%"]]},  # Alte %
            {"range": f"{sheet_tab_name}!C{next_row + 7}", "values": [[f"{ml_btts_prob:.1f}%" if ml_btts_prob else ""]]},  # ML %
            {"range": f"{sheet_tab_name}!E{next_row + 7}", "values": [[consensus_btts_odds]]},  # Konsens Quote
            
            # ZEILE 9: Scores
            {"range": f"{sheet_tab_name}!B{next_row + 8}", "values": [[predicted_score]]},  # Alte
            {"range": f"{sheet_tab_name}!C{next_row + 8}", "values": [[ml_score]]},  # ML
        ]

        # Tatsächliches Ergebnis (optional)
        if actual_score:
            updates.append({"range": f"{sheet_tab_name}!G{next_row}", "values": [[actual_score]]})

        # Batch Update durchführen
        body = {"valueInputOption": "USER_ENTERED", "data": updates}

        service.spreadsheets().values().batchUpdate(
            spreadsheetId=EXPORT_SHEET_ID, body=body
        ).execute()

        st.success(f"✅ Export erfolgreich! Zeile {next_row} in '{sheet_tab_name}'")
        return True

    except Exception as e:
        st.error(f"❌ Export-Fehler: {str(e)}")
        import traceback

        st.error(traceback.format_exc())
        return False


def find_next_free_row(service, sheet_tab_name: str) -> int:
    """
    Findet die nächste freie Zeile im 10er-Intervall (1, 11, 21, 31...)

    Args:
        service: Google Sheets Service
        sheet_tab_name: Name des Tabellenblatts

    Returns:
        Nächste freie Zeile oder None bei Fehler
    """
    try:
        # Wir prüfen die Block-Startzellen B1, B11, B21, ...
        # Ein Block ist "frei", wenn die Match-Name-Zelle (B{start}) leer ist.
        max_row = 2000
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=EXPORT_SHEET_ID, range=f"{sheet_tab_name}!B1:B{max_row}")
            .execute()
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

        # Falls alles belegt ist, hänge am Ende einen neuen Block an
        return max_row + 1

    except Exception as e:
        st.error(f"Fehler beim Finden der freien Zeile: {e}")
        return None


def find_match_row(service, sheet_tab_name: str, match_name: str) -> int | None:
    """Findet den Blockstart (1, 11, 21, ...) für einen bereits exportierten Match.

    Gesucht wird in Spalte B nur an den Block-Start-Zeilen (B1/B11/B21/...).
    Gibt die Startzeile zurück, wenn der Matchname exakt übereinstimmt.
    """
    try:
        max_row = 2000
        resp = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=EXPORT_SHEET_ID, range=f"{sheet_tab_name}!B1:B{max_row}")
            .execute()
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
