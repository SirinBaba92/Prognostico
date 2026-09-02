"""
UI-Komponenten für Ergebnis-Anzeige
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List
from collections import Counter
from models.risk_management import calculate_stake_recommendation
from analysis.validation import check_alerts


def _display_ml_predictions_inline(result: Dict):
    """
    Zeigt ML Predictions im gleichen Format wie Score-Vorhersage
    Nutzt die GLEICHEN Match-Daten wie Tab 6!

    Args:
        result: Analyse-Ergebnis Dictionary (enthält _match_id)
    """
    try:
        # Importiere benötigte Module
        from ml.football_ml_models import get_ml_models
        from ml.scoreline_predictor import ScorelinePredictor
        from ui.sheets_ml_integration import convert_match_data_to_features
        from data.supabase_client import get_full_match_bundle
        from data.supabase_mapper import map_bundle_to_match_data

        st.subheader("🤖 Machine Learning Prognose")

        # Lade Models
        ml_models = get_ml_models()

        if not ml_models.models_loaded:
            st.info(
                "💡 ML Models nicht verfügbar. Nutze Tab 6 für manuelle ML Predictions."
            )
            return

        # Hole match_id aus result (wurde in app.py gespeichert!)
        match_id = result.get("_match_id")

        if not match_id:
            st.info("""
            💡 **Für ML Predictions:**
            → Nutze Tab 6 "ML Predictions" für vollständige Analyse
            """)
            return

        # Lade Match-Daten DIREKT aus Supabase (wie Tab 6!)
        try:
            with st.spinner("Lade Match-Daten für ML..."):
                bundle = get_full_match_bundle(match_id)

                if not bundle:
                    st.warning("⚠️ Konnte Match-Daten nicht laden")
                    return

                match_data = map_bundle_to_match_data(bundle)

        except Exception as e:
            st.info(f"""
            💡 **ML Predictions nicht verfügbar**
            
            Fehler beim Laden: {str(e)}
            
            → Nutze Tab 6 "ML Predictions" für vollständige Analyse
            """)
            return

        # Konvertiere zu Features (GLEICHE Funktion wie Tab 6!)
        features = convert_match_data_to_features(match_data)

        # Hole Predictions (MIT Quoten)
        predictions = ml_models.predict_all(features, use_odds=True)

        # Erstelle Scoreline Predictor
        scoreline_pred = ScorelinePredictor()

        # Berechne xG aus Match-Daten (wie Tab 6)
        home_xg = (
            match_data.home_team.goals_scored_per_match
            if hasattr(match_data.home_team, "goals_scored_per_match")
            else 1.5
        )
        away_xg = (
            match_data.away_team.goals_scored_per_match
            if hasattr(match_data.away_team, "goals_scored_per_match")
            else 1.3
        )

        # Generiere Scorelines (wie Tab 6)
        all_scorelines = scoreline_pred.predict_scorelines(home_xg, away_xg, top_n=20)

        # Bestimme ML Predictions für Consistency Check
        if "1x2" in predictions:
            ml_1x2 = (
                predictions["1x2"]["prediction"]
                .replace(" WIN", "")
                .replace("DRAW", "DRAW")
            )
            if "HOME" in ml_1x2:
                x2_pred = "HOME"
            elif "DRAW" in ml_1x2:
                x2_pred = "DRAW"
            else:
                x2_pred = "AWAY"
        else:
            # Fallback: ALTE
            probs = result.get("probabilities", {})
            best_1x2_prob = max(
                probs.get("home_win", 0), probs.get("draw", 0), probs.get("away_win", 0)
            )
            if best_1x2_prob == probs.get("home_win", 0):
                x2_pred = "HOME"
            elif best_1x2_prob == probs.get("draw", 0):
                x2_pred = "DRAW"
            else:
                x2_pred = "AWAY"

        if "over_under" in predictions:
            ou_pred = (
                "OVER" if "OVER" in predictions["over_under"]["prediction"] else "UNDER"
            )
        else:
            # Fallback: ALTE
            probs = result.get("probabilities", {})
            ou_pred = (
                "OVER"
                if probs.get("over_25", 0) >= probs.get("under_25", 0)
                else "UNDER"
            )

        if "btts" in predictions:
            btts_pred = "YES" if "YES" in predictions["btts"]["prediction"] else "NO"
        else:
            # Fallback: ALTE
            probs = result.get("probabilities", {})
            btts_pred = (
                "YES" if probs.get("btts_yes", 0) >= probs.get("btts_no", 0) else "NO"
            )

        # Nutze GLEICHE Funktion wie Tab 6!
        best_scoreline = scoreline_pred.get_most_likely_scoreline_for_markets(
            x2_pred, ou_pred, btts_pred, all_scorelines
        )

        # Fallback wenn kein perfektes Match
        if not best_scoreline:
            # Nutze choose_consistent_predicted_score für Soft-Optimierung
            try:
                from app import choose_consistent_predicted_score

                # Erstelle Pseudo-Probabilities aus ML Predictions
                ml_probs = {}

                if "1x2" in predictions:
                    pred = predictions["1x2"]["prediction"]
                    conf = predictions["1x2"]["confidence"]
                    if "HOME" in pred:
                        ml_probs["home_win"] = conf
                        ml_probs["draw"] = (100 - conf) / 2
                        ml_probs["away_win"] = (100 - conf) / 2
                    elif "DRAW" in pred:
                        ml_probs["draw"] = conf
                        ml_probs["home_win"] = (100 - conf) / 2
                        ml_probs["away_win"] = (100 - conf) / 2
                    else:
                        ml_probs["away_win"] = conf
                        ml_probs["home_win"] = (100 - conf) / 2
                        ml_probs["draw"] = (100 - conf) / 2

                if "over_under" in predictions:
                    pred = predictions["over_under"]["prediction"]
                    conf = predictions["over_under"]["confidence"]
                    if "OVER" in pred:
                        ml_probs["over_25"] = conf
                        ml_probs["under_25"] = 100 - conf
                    else:
                        ml_probs["under_25"] = conf
                        ml_probs["over_25"] = 100 - conf

                if "btts" in predictions:
                    pred = predictions["btts"]["prediction"]
                    conf = predictions["btts"]["confidence"]
                    if "YES" in pred:
                        ml_probs["btts_yes"] = conf
                        ml_probs["btts_no"] = 100 - conf
                    else:
                        ml_probs["btts_no"] = conf
                        ml_probs["btts_yes"] = 100 - conf

                temp_result = {
                    "scorelines": [
                        (s["scoreline"], s["probability"]) for s in all_scorelines
                    ],
                    "probabilities": ml_probs,
                }

                temp_result = choose_consistent_predicted_score(temp_result)
                consistent_score = temp_result.get("predicted_score", "")

                if consistent_score:
                    # Finde Scoreline in Liste
                    for s in all_scorelines:
                        if s["scoreline"] == consistent_score:
                            best_scoreline = s
                            break

                    # Falls nicht gefunden, erstelle es
                    if not best_scoreline:
                        best_scoreline = {
                            "scoreline": consistent_score,
                            "probability": 0.0,
                        }
            except:
                pass

            # Final Fallback
            if not best_scoreline:
                best_scoreline = all_scorelines[0] if all_scorelines else None

        # Display im gleichen 4-Spalten Format
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # 1X2 + Quote
            if "1x2" in predictions:
                pred_1x2 = predictions["1x2"]
                label_map = {
                    "HOME WIN": "Heimsieg",
                    "DRAW": "Unentschieden",
                    "AWAY WIN": "Auswärtssieg",
                }
                pred_label = label_map.get(
                    pred_1x2["prediction"], pred_1x2["prediction"]
                )

                # Hole Quote basierend auf Prediction
                if pred_1x2["prediction"] == "HOME WIN":
                    odds = features.get("odds_home", 0.0)
                elif pred_1x2["prediction"] == "DRAW":
                    odds = features.get("odds_draw", 0.0)
                else:
                    odds = features.get("odds_away", 0.0)

                st.success(
                    f"### 🎯 1X2\n\n"
                    f"**{pred_label}**\n\n"
                    f"# {pred_1x2['confidence']:.1f}%\n"
                    f"**Quote: {odds:.2f}**"
                )

        with col2:
            # Over/Under + Quote
            if "over_under" in predictions:
                pred_ou = predictions["over_under"]

                # Hole Quote
                if "OVER" in pred_ou["prediction"]:
                    odds = features.get("odds_over25", 0.0)
                else:
                    odds = features.get("odds_under25", 0.0)

                st.success(
                    f"### 📈 Over/Under 2.5\n\n"
                    f"**{pred_ou['prediction']}**\n\n"
                    f"# {pred_ou['confidence']:.1f}%\n"
                    f"**Quote: {odds:.2f}**"
                )

        with col3:
            # BTTS + Quote
            if "btts" in predictions:
                pred_btts = predictions["btts"]
                label_map = {"BTTS YES": "BTTS Ja", "BTTS NO": "BTTS Nein"}
                pred_label = label_map.get(
                    pred_btts["prediction"], pred_btts["prediction"]
                )

                # Hole Quote
                if pred_btts["prediction"] == "BTTS YES":
                    odds = features.get("odds_btts_yes", 0.0)
                else:
                    odds = features.get("odds_btts_no", 0.0)

                st.success(
                    f"### ⚽ BTTS\n\n"
                    f"**{pred_label}**\n\n"
                    f"# {pred_btts['confidence']:.1f}%\n"
                    f"**Quote: {odds:.2f}**"
                )

        with col4:
            # Wahrscheinlichstes Ergebnis (keine Quote)
            if best_scoreline:
                st.success(
                    f"### 🏆 Wahrscheinlichstes Ergebnis\n\n"
                    f"# {best_scoreline['scoreline']}\n\n"
                    f"**Wahrscheinlichkeit:**\n"
                    f"# {best_scoreline['probability']:.1f}%"
                )

        # Konsens-Analyse
        _show_consensus_analysis(result, predictions, best_scoreline)

        # Erfolgs-Hinweis (ohne DEBUG)
        st.caption(
            f"✅ ML Predictions basieren auf echten Match-Daten (gleiche Quelle wie Tab 6)"
        )

    except Exception as e:
        # Stilles Fallback - zeige nur Info
        st.info("""
        💡 **ML Predictions mit vollständigen Daten:**
        → Nutze Tab 6 "ML Predictions"
        """)


def _show_consensus_analysis(result: Dict, ml_predictions: Dict, ml_scoreline: Dict):
    """
    Zeigt Konsens zwischen SMART-PRECISION und ML
    NUR wenn SMART-PRECISION Schwellenwerte erreicht:
    - 1X2: ≥ 50%
    - Over/Under: ≥ 60%
    - BTTS: ≥ 60%
    """
    try:
        # Extrahiere SMART-PRECISION Predictions
        probs = result.get("probabilities", {})

        # Hole Wahrscheinlichkeiten
        smart_home = probs.get("home_win", 0)
        smart_draw = probs.get("draw", 0)
        smart_away = probs.get("away_win", 0)
        smart_over = probs.get("over_25", 0)
        smart_under = probs.get("under_25", 0)
        smart_btts_yes = probs.get("btts_yes", 0)
        smart_btts_no = probs.get("btts_no", 0)

        # Beste Predictions
        smart_1x2 = (
            "Heimsieg"
            if smart_home >= max(smart_draw, smart_away)
            else ("Unentschieden" if smart_draw >= smart_away else "Auswärtssieg")
        )
        smart_1x2_prob = max(smart_home, smart_draw, smart_away)

        smart_ou = "Over 2.5" if smart_over >= smart_under else "Under 2.5"
        smart_ou_prob = max(smart_over, smart_under)

        smart_btts = "BTTS Ja" if smart_btts_yes >= smart_btts_no else "BTTS Nein"
        smart_btts_prob = max(smart_btts_yes, smart_btts_no)

        smart_score = result.get("predicted_score", "N/A")

        # Extrahiere ML Predictions
        ml_1x2_raw = ml_predictions.get("1x2", {}).get("prediction", "")
        ml_1x2 = {
            "HOME WIN": "Heimsieg",
            "DRAW": "Unentschieden",
            "AWAY WIN": "Auswärtssieg",
        }.get(ml_1x2_raw, ml_1x2_raw)
        ml_ou = ml_predictions.get("over_under", {}).get("prediction", "")
        ml_btts_raw = ml_predictions.get("btts", {}).get("prediction", "")
        ml_btts = {"BTTS YES": "BTTS Ja", "BTTS NO": "BTTS Nein"}.get(
            ml_btts_raw, ml_btts_raw
        )
        ml_score = ml_scoreline.get("scoreline", "N/A") if ml_scoreline else "N/A"

        # Check Konsens MIT SCHWELLENWERTEN!
        consensus_items = []
        weak_items = []  # Items die matchen aber Schwellenwert nicht erreichen

        # 1X2: Nur wenn SMART ≥ 50%
        if smart_1x2 == ml_1x2:
            if smart_1x2_prob >= 50:
                consensus_items.append(f"{smart_1x2} ({smart_1x2_prob:.1f}%)")
            else:
                weak_items.append(f"{smart_1x2} (nur {smart_1x2_prob:.1f}%, <50%)")

        # Over/Under: Nur wenn SMART ≥ 60%
        if smart_ou == ml_ou:
            if smart_ou_prob >= 60:
                consensus_items.append(f"{smart_ou} ({smart_ou_prob:.1f}%)")
            else:
                weak_items.append(f"{smart_ou} (nur {smart_ou_prob:.1f}%, <60%)")

        # BTTS: Nur wenn SMART ≥ 60%
        if smart_btts == ml_btts:
            if smart_btts_prob >= 60:
                consensus_items.append(f"{smart_btts} ({smart_btts_prob:.1f}%)")
            else:
                weak_items.append(f"{smart_btts} (nur {smart_btts_prob:.1f}%, <60%)")

        # Score (kein Schwellenwert)
        if smart_score == ml_score:
            consensus_items.append(f"Score: {smart_score}")

        # Zeige Konsens-Ergebnis
        if len(consensus_items) >= 2:
            st.success(
                f"### ✅ Konsens-Analyse\n\n"
                f"**Starke Übereinstimmung bei:** {', '.join(consensus_items)}\n\n"
                f"🎯 **HOHE CONFIDENCE!**"
            )
        elif len(consensus_items) == 1:
            msg = f"### 📊 Konsens-Analyse\n\n**Übereinstimmung:** {consensus_items[0]}\n\n"
            if weak_items:
                msg += f"⚠️ **Schwache Matches (Schwellenwert nicht erreicht):**\n{', '.join(weak_items)}\n\n"
            msg += f"💡 Teilweise Einigkeit - moderate Vorsicht!"
            st.info(msg)
        else:
            msg = f"### ⚠️ Konsens-Analyse\n\n"
            if weak_items:
                msg += f"**Schwache Matches (Schwellenwert nicht erreicht):**\n{', '.join(weak_items)}\n\n"
                msg += f"💡 Predictions matchen, aber Alte Confidence zu niedrig!\n\n"
            else:
                msg += f"**Keine Übereinstimmung** zwischen den Systemen.\n\n"
            msg += f"⚠️ Bei Uneinigkeit: höhere Vorsicht oder Skip!"
            st.warning(msg)

    except Exception as e:
        # Stilles Ignorieren wenn Konsens nicht berechnet werden kann
        pass


def display_stake_recommendation(
    risk_score: int, odds: float, market_name: str, match_info: str = ""
):
    """
    Zeigt Einsatzempfehlung basierend auf Risiko-Score mit konsistenter Farbcodierung

    Args:
        risk_score: Risiko-Score 1-5
        odds: Wett-Quote
        market_name: Name des Markets
        match_info: Match-Information
    """
    from config.constants import RISK_PROFILES

    stake_info = calculate_stake_recommendation(
        risk_score, odds, market_name, match_info
    )

    st.markdown("---")

    # Konsistente Farbcodierung
    risk_colors = {
        1: "🔴",  # Rot
        2: "🟠",  # Orange
        3: "🟡",  # Gelb
        4: "🟢",  # Hellgrün
        5: "🟩",  # Grün
    }

    color_emoji = risk_colors.get(risk_score, "⚪")

    st.subheader(f"{color_emoji} EINSATZEMPFEHLUNG: {market_name}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label=f"Risiko-Score",
            value=f"{risk_score}/5",
            delta=f"{RISK_PROFILES[st.session_state.risk_management['risk_profile']]['name']}",
        )

    with col2:
        st.metric(
            label="Empfohlener Einsatz",
            value=f"€{stake_info['recommended_stake']}",
            delta=f"{stake_info['adjusted_percentage']}% der Bankroll",
        )

    with col3:
        st.metric(
            label=f"Potentieller Gewinn",
            value=f"+€{stake_info['potential_win']}",
            delta=f"Quote: {odds:.2f}",
        )

    # Demo-Modus: Speichere Wettoptionen
    demo_mode_active = st.session_state.get("enable_demo_mode", False)

    if demo_mode_active and match_info:
        if "demo_bet_options" not in st.session_state:
            st.session_state.demo_bet_options = []

        bet_option = {
            "market": market_name,
            "match_info": match_info,
            "potential_win": stake_info["potential_win"],
            "potential_loss": stake_info["potential_loss"],
            "stake": stake_info["recommended_stake"],
            "unique_id": f"{market_name}_{hash(match_info)}",
        }

        if not any(
            opt["unique_id"] == bet_option["unique_id"]
            for opt in st.session_state.demo_bet_options
        ):
            st.session_state.demo_bet_options.append(bet_option)

        st.caption("🎮 Demo-Modus: Wettauswahl am Ende der Analyse")

    with st.expander("📊 Detaillierte Einsatz-Analyse", expanded=False):
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown("**Einsatz-Bereich:**")
            st.caption(f"• Minimum: €{stake_info['min_stake']}")
            st.caption(f"• Empfohlen: €{stake_info['recommended_stake']}")
            st.caption(f"• Maximum: €{stake_info['max_stake']}")

        with col_b:
            st.markdown("**Risiko-Analyse:**")
            st.caption(f"• Basis: {stake_info['base_percentage']}%")
            st.caption(f"• Adjustiert: {stake_info['adjusted_percentage']}%")

        with col_c:
            st.markdown("**Konsequenzen:**")
            st.caption(
                f"• Bei Gewinn: +{stake_info['potential_win'] / stake_info['recommended_stake'] * 100:.1f}%"
            )
            st.caption(
                f"• Bei Verlust: -{stake_info['adjusted_percentage']:.1f}% Bankroll"
            )


def display_simulation_section(result: Dict):
    """
    Zeigt eine Monte-Carlo-Spielsimulation auf Basis der bereits berechneten
    μ-Werte (result["mu"]). Nutzer wählt die Anzahl der Durchläufe.
    """
    from analysis.simulation import simulate_match

    st.subheader("🎲 Monte-Carlo-Spielsimulation")

    mu_home = result["mu"]["home"]
    mu_away = result["mu"]["away"]

    col_a, col_b = st.columns([2, 1])
    with col_a:
        n_sims = st.select_slider(
            "Anzahl Durchgänge",
            options=[1_000, 10_000, 100_000, 1_000_000],
            value=10_000,
            format_func=lambda x: f"{x:,}".replace(",", "."),
            key=f"sim_n_{result['match_info']['home']}_{result['match_info']['away']}",
        )
    with col_b:
        run_sim = st.button(
            "▶️ Simulation starten",
            key=f"sim_run_{result['match_info']['home']}_{result['match_info']['away']}",
        )

    if run_sim:
        with st.spinner(f"Simuliere {n_sims:,} Spiele...".replace(",", ".")):
            sim_result = simulate_match(mu_home=mu_home, mu_away=mu_away, n_sims=n_sims)

        sp = sim_result["probabilities"]
        ci = sim_result["confidence_95"]

        st.caption(
            f"Basis: μ Heim={mu_home:.2f}, μ Auswärts={mu_away:.2f} · "
            f"{sim_result['n_sims']:,} simulierte Spiele (95%-Konfidenzintervall in Klammern)".replace(
                ",", "."
            )
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Heimsieg", f"{sp['home_win']}%", f"±{ci['home_win']}pp")
        col2.metric("Remis", f"{sp['draw']}%", f"±{ci['draw']}pp")
        col3.metric("Auswärtssieg", f"{sp['away_win']}%", f"±{ci['away_win']}pp")

        col4, col5, col6 = st.columns(3)
        col4.metric("Über 2.5", f"{sp['over_25']}%", f"±{ci['over_25']}pp")
        col5.metric("BTTS Ja", f"{sp['btts_yes']}%", f"±{ci['btts_yes']}pp")
        col6.metric("Ø Tore gesamt", f"{sim_result['avg_goals']['total']}")

        st.markdown("**Häufigste simulierte Ergebnisse:**")
        top_df = pd.DataFrame(
            sim_result["top_scorelines"], columns=["Ergebnis", "Häufigkeit (%)"]
        )
        st.dataframe(top_df, use_container_width=True, hide_index=True)

        # Vergleich zur direkten Poisson-Berechnung (analyze_match_v47_ml)
        with st.expander("Vergleich zur analytischen Poisson-Berechnung"):
            comp_df = pd.DataFrame(
                {
                    "Markt": [
                        "Heimsieg",
                        "Remis",
                        "Auswärtssieg",
                        "Über 2.5",
                        "BTTS Ja",
                    ],
                    "Analytisch (Poisson)": [
                        f"{result['probabilities']['home_win']}%",
                        f"{result['probabilities']['draw']}%",
                        f"{result['probabilities']['away_win']}%",
                        f"{result['probabilities']['over_25']}%",
                        f"{result['probabilities']['btts_yes']}%",
                    ],
                    "Simulation": [
                        f"{sp['home_win']}%",
                        f"{sp['draw']}%",
                        f"{sp['away_win']}%",
                        f"{sp['over_25']}%",
                        f"{sp['btts_yes']}%",
                    ],
                }
            )
            st.dataframe(comp_df, use_container_width=True, hide_index=True)
            st.caption(
                "Beide Werte basieren auf denselben μ-Werten und derselben Poisson-Annahme — "
                "kleine Abweichungen sind reines Simulationsrauschen und schrumpfen mit mehr Durchgängen."
            )


def display_results(result: Dict, key_suffix: str = ""):
    """
    Zeigt vollständige Analyse-Ergebnisse an

    Args:
        result: Dictionary mit Analyse-Ergebnissen
        key_suffix: Eindeutiger Suffix für Widget-Keys, nötig wenn display_results()
            mehrfach auf derselben Seite aufgerufen wird (z. B. Bulk-Analyse-Liste).
            Leer bei Einzelaufruf (Standardverhalten unverändert).
    """
    st.header(f"🎯 {result['match_info']['home']} vs {result['match_info']['away']}")
    st.caption(
        f"📅 {result['match_info']['date']} | {result['match_info']['kickoff']} Uhr | {result['match_info']['competition']}"
    )

    # QUICK SUMMARY BOX
    st.markdown("---")
    probs = result["probabilities"]
    overall_risk = result["extended_risk"]["overall"]

    # Finde beste Empfehlung
    prob_1x2_home = probs["home_win"]
    prob_1x2_draw = probs["draw"]
    prob_1x2_away = probs["away_win"]
    best_1x2_prob = max(prob_1x2_home, prob_1x2_draw, prob_1x2_away)

    if prob_1x2_home == best_1x2_prob:
        best_1x2_market = "Heimsieg"
    elif prob_1x2_draw == best_1x2_prob:
        best_1x2_market = "Unentschieden"
    else:
        best_1x2_market = "Auswärtssieg"

    # Stake berechnen (falls Schwellenwert erreicht)
    if best_1x2_prob >= 50:
        best_1x2_risk = result["extended_risk"]["1x2"]
        stake_info = calculate_stake_recommendation(
            best_1x2_risk["risk_score"], best_1x2_risk["odds"], best_1x2_market, ""
        )
        recommended_stake = f"€{stake_info['recommended_stake']}"
    else:
        recommended_stake = "Keine Empfehlung"

    # Risk Color
    risk_colors = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🟩"}
    risk_emoji = risk_colors.get(overall_risk["score"], "⚪")

    # Summary Box
    st.info(f"""
    ### 📊 QUICK SUMMARY
    
    **Top-Empfehlung:** {best_1x2_market} ({best_1x2_prob:.1f}%)  
    **Risiko-Score:** {risk_emoji} {overall_risk['score']}/5 - {overall_risk['category']}  
    **Empfohlener Einsatz:** {recommended_stake}  
    **Predicted Score:** {result['predicted_score']} ({result['scorelines'][0][1]:.1f}% Wahrscheinlichkeit)
    """)

    st.markdown("---")

    # ========================================================================
    # SCORE-VORHERSAGE - DIREKT NACH QUICK SUMMARY!
    # ========================================================================
    st.subheader("📊 Score-Vorhersage")

    # Verwende 4 Spalten statt 3 für bessere Aufteilung
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # 1X2 mit größerer Schrift + Quote
        best_1x2 = (
            "Heimsieg"
            if probs["home_win"] >= probs["draw"]
            and probs["home_win"] >= probs["away_win"]
            else (
                "Unentschieden"
                if probs["draw"] >= probs["away_win"]
                else "Auswärtssieg"
            )
        )
        best_1x2_prob = max(probs["home_win"], probs["draw"], probs["away_win"])

        # Hole Quote
        risk_1x2 = result["extended_risk"]["1x2"]
        odds_1x2 = risk_1x2.get("odds", 0.0)

        st.success(
            f"### 🎯 1X2\n\n"
            f"**{best_1x2}**\n\n"
            f"# {best_1x2_prob:.1f}%\n"
            f"**Quote: {odds_1x2:.2f}**"
        )

    with col2:
        # Over/Under 2.5 - separate Box + Quote
        best_ou = "Over 2.5" if probs["over_25"] >= probs["under_25"] else "Under 2.5"
        best_ou_prob = max(probs["over_25"], probs["under_25"])

        # Hole Quote
        risk_ou = result["extended_risk"]["over_under"]
        if best_ou == "Over 2.5":
            odds_ou = risk_ou.get("over", {}).get("odds", 0.0)
        else:
            odds_ou = risk_ou.get("under", {}).get("odds", 0.0)

        st.success(
            f"### 📈 Over/Under 2.5\n\n"
            f"**{best_ou}**\n\n"
            f"# {best_ou_prob:.1f}%\n"
            f"**Quote: {odds_ou:.2f}**"
        )

    with col3:
        # BTTS - separate Box + Quote
        best_btts = "BTTS Ja" if probs["btts_yes"] >= probs["btts_no"] else "BTTS Nein"
        best_btts_prob = max(probs["btts_yes"], probs["btts_no"])

        # Hole Quote
        risk_btts = result["extended_risk"]["btts"]
        if best_btts == "BTTS Ja":
            odds_btts = risk_btts.get("yes", {}).get("odds", 0.0)
        else:
            odds_btts = risk_btts.get("no", {}).get("odds", 0.0)

        st.success(
            f"### ⚽ BTTS\n\n"
            f"**{best_btts}**\n\n"
            f"# {best_btts_prob:.1f}%\n"
            f"**Quote: {odds_btts:.2f}**"
        )

    with col4:
        # Wahrscheinlichstes Ergebnis - größte Box (keine Quote für Scoreline)
        if result["scorelines"]:
            predicted_score = result["predicted_score"]
            score_prob = result["scorelines"][0][1]
            st.success(
                f"### 🏆 Wahrscheinlichstes Ergebnis\n\n"
                f"# {predicted_score}\n\n"
                f"**Wahrscheinlichkeit:**\n"
                f"# {score_prob:.1f}%"
            )

    # ========================================================================
    # ML PREDICTIONS - DIREKT DANACH!
    # ========================================================================
    st.markdown("---")
    _display_ml_predictions_inline(result)

    # ========================================================================
    # EXPORT ZU GOOGLE SHEETS - DIREKT NACH KONSENS!
    # ========================================================================
    st.markdown("---")
    st.subheader("📤 Export zu Google Sheets")

    # Letztes Analyse-Ergebnis speichern (damit Export nach Rerun funktioniert)
    st.session_state["_last_analysis_result"] = result

    def _trigger_simple_export():
        st.session_state["_do_export_simple"] = True

    def _trigger_export_with_result():
        h = st.session_state.get(f"exp_home_rd{key_suffix}", 0)
        a = st.session_state.get(f"exp_away_rd{key_suffix}", 0)
        st.session_state["_export_actual_score"] = f"{h}-{a}"
        st.session_state["_do_export_with_result"] = True

    col_export, col_actual = st.columns(2)
    with col_export:
        st.button(
            "💾 Analyse exportieren",
            use_container_width=True,
            key=f"export_btn_simple_rd{key_suffix}",
            on_click=_trigger_simple_export,
        )

    with col_actual:
        st.caption("Optional: Tatsächliches Ergebnis für Export")
        c1, c2 = st.columns(2)
        with c1:
            st.number_input("Heim", 0, 10, 0, key=f"exp_home_rd{key_suffix}")
        with c2:
            st.number_input("Auswärts", 0, 10, 0, key=f"exp_away_rd{key_suffix}")
        st.button(
            "📤 Mit Ergebnis exportieren",
            use_container_width=True,
            key=f"export_btn_with_result_rd{key_suffix}",
            on_click=_trigger_export_with_result,
        )

    # Exporte ausführen (klick-sicher nach Render)
    export_result = st.session_state.get("_last_analysis_result")
    if st.session_state.get("_do_export_simple"):
        st.session_state["_do_export_simple"] = False
        from models import export_analysis_to_sheets

        with st.spinner("Exportiere Analyse..."):
            ok = export_analysis_to_sheets(export_result)
        if ok:
            st.success("✅ Analyse exportiert!")
            st.balloons()
        else:
            st.error("❌ Export fehlgeschlagen")

    if st.session_state.get("_do_export_with_result"):
        st.session_state["_do_export_with_result"] = False
        actual_score = st.session_state.get("_export_actual_score")
        from models import export_analysis_to_sheets

        with st.spinner(f"Exportiere mit Ergebnis {actual_score}..."):
            ok = export_analysis_to_sheets(export_result, actual_score)
        if ok:
            st.success(f"✅ Mit Ergebnis {actual_score} exportiert!")
            st.balloons()
        else:
            st.error("❌ Export fehlgeschlagen")

    st.markdown("---")

    # Alarm-System
    alerts = check_alerts(
        result["mu"]["home"],
        result["mu"]["away"],
        result["tki"]["home"],
        result["tki"]["away"],
        result["mu"]["ppg_diff"],
        st.session_state.alert_thresholds,
    )

    if alerts:
        st.subheader("🚨 ALARM-SYSTEM")
        for alert in alerts:
            if alert["type"] == "warning":
                st.warning(f"{alert['level']} **{alert['title']}**: {alert['message']}")
            elif alert["type"] == "info":
                st.info(f"{alert['level']} **{alert['title']}**: {alert['message']}")
            elif alert["type"] == "success":
                st.success(f"{alert['level']} **{alert['title']}**: {alert['message']}")

    # SMART-PRECISION Werte
    st.subheader("🧠 SMART-PRECISION v6.0")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Smart μ Home", f"{result['mu']['home']:.2f}")
    with col2:
        st.metric("Smart μ Away", f"{result['mu']['away']:.2f}")
    with col3:
        st.metric("PPG Gap", f"{result['mu']['ppg_diff']:.2f}")

    if result.get("ml_position_correction", {}).get("applied", False):
        st.info(
            f"📊 ML-Korrektur angewandt: {result['ml_position_correction']['message']}"
        )

    # Erweiterte Risiko-Analyse
    st.subheader("⚠️ ERWEITERTE RISIKO-ANALYSE (1-5)")

    overall_risk = result["extended_risk"]["overall"]

    risk_color_map = {1: "darkred", 2: "red", 3: "yellow", 4: "lightgreen", 5: "green"}

    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        st.markdown(f"### {overall_risk['score_text']}")
        st.progress(overall_risk["score"] / 5)
    with col2:
        st.markdown(f"**{overall_risk['category']}**")
        st.markdown(f"*{overall_risk['recommendation']}*")
    with col3:
        fig_risk = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=overall_risk["score"],
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Gesamt-Risiko"},
                gauge={
                    "axis": {"range": [1, 5], "tickwidth": 1},
                    "bar": {"color": risk_color_map.get(overall_risk["score"], "gray")},
                    "steps": [
                        {"range": [1, 2], "color": "lightcoral"},
                        {"range": [2, 3], "color": "lightyellow"},
                        {"range": [3, 4], "color": "lightgreen"},
                        {"range": [4, 5], "color": "green"},
                    ],
                },
            )
        )
        fig_risk.update_layout(height=200)
        st.plotly_chart(fig_risk, use_container_width=True)

    # Einzelne Wett-Risikos
    st.subheader("📊 EINZELNE WETT-RISIKOS")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🎯 1X2 WETTE**")
        risk_1x2 = result["extended_risk"]["1x2"]
        risk_display = f"{risk_1x2['risk_score']}/5 {risk_1x2['risk_text']}"
        st.metric(
            label=f"{risk_1x2['market']} ({risk_1x2['probability']:.1f}%)",
            value=f"{risk_1x2['odds']:.2f}",
            delta=risk_display,
            delta_color="off",
        )

    with col2:
        st.markdown("**📈 OVER/UNDER 2.5**")
        risk_ou = result["extended_risk"]["over_under"]
        col2a, col2b = st.columns(2)
        with col2a:
            risk_display_over = (
                f"{risk_ou['over']['risk_score']}/5 {risk_ou['over']['risk_text']}"
            )
            st.metric(
                label=f"Over ({risk_ou['over']['probability']:.1f}%)",
                value=f"{risk_ou['over']['odds']:.2f}",
                delta=risk_display_over,
                delta_color="off",
            )
        with col2b:
            risk_display_under = (
                f"{risk_ou['under']['risk_score']}/5 {risk_ou['under']['risk_text']}"
            )
            st.metric(
                label=f"Under ({risk_ou['under']['probability']:.1f}%)",
                value=f"{risk_ou['under']['odds']:.2f}",
                delta=risk_display_under,
                delta_color="off",
            )

    with col3:
        st.markdown("**⚽ BTTS**")
        risk_btts = result["extended_risk"]["btts"]
        col3a, col3b = st.columns(2)
        with col3a:
            risk_display_yes = (
                f"{risk_btts['yes']['risk_score']}/5 {risk_btts['yes']['risk_text']}"
            )
            st.metric(
                label=f"Ja ({risk_btts['yes']['probability']:.1f}%)",
                value=f"{risk_btts['yes']['odds']:.2f}",
                delta=risk_display_yes,
                delta_color="off",
            )
        with col3b:
            risk_display_no = (
                f"{risk_btts['no']['risk_score']}/5 {risk_btts['no']['risk_text']}"
            )
            st.metric(
                label=f"Nein ({risk_btts['no']['probability']:.1f}%)",
                value=f"{risk_btts['no']['odds']:.2f}",
                delta=risk_display_no,
                delta_color="off",
            )

    # Einsatzempfehlungen - nur wenn Schwellenwerte erreicht
    st.markdown("---")

    probs = result["probabilities"]

    # Prüfe welche Markets die Schwellenwerte erreichen
    show_1x2 = False
    show_ou = False
    show_btts = False

    # 1X2: Beste Option >= 50%
    prob_1x2_home = probs["home_win"]
    prob_1x2_draw = probs["draw"]
    prob_1x2_away = probs["away_win"]
    best_1x2_prob = max(prob_1x2_home, prob_1x2_draw, prob_1x2_away)
    if best_1x2_prob >= 50:
        show_1x2 = True

    # Over/Under: Beste Option >= 60%
    prob_over = probs["over_25"]
    prob_under = probs["under_25"]
    best_ou_prob = max(prob_over, prob_under)
    if best_ou_prob >= 60:
        show_ou = True

    # BTTS: Beste Option >= 60%
    prob_btts_yes = probs["btts_yes"]
    prob_btts_no = probs["btts_no"]
    best_btts_prob = max(prob_btts_yes, prob_btts_no)
    if best_btts_prob >= 60:
        show_btts = True

    # Zeige Empfehlungen nur wenn mindestens eine erfüllt ist
    if show_1x2 or show_ou or show_btts:
        # Beste 1X2 Option (wenn >= 50%)
        if show_1x2:
            best_1x2 = result["extended_risk"]["1x2"]
            display_stake_recommendation(
                risk_score=best_1x2["risk_score"],
                odds=best_1x2["odds"],
                market_name=best_1x2["market"],
                match_info=f"{result['match_info']['home']} vs {result['match_info']['away']} - {best_1x2['market']}",
            )

        # Beste Over/Under Option (wenn >= 60%)
        if show_ou:
            ou_risk = result["extended_risk"]["over_under"]
            best_ou = (
                "over"
                if ou_risk["over"]["risk_score"] >= ou_risk["under"]["risk_score"]
                else "under"
            )
            display_stake_recommendation(
                risk_score=ou_risk[best_ou]["risk_score"],
                odds=ou_risk[best_ou]["odds"],
                market_name=f"{best_ou.upper()} 2.5",
                match_info=f"{result['match_info']['home']} vs {result['match_info']['away']} - {best_ou.upper()} 2.5",
            )

        # Beste BTTS Option (wenn >= 60%)
        if show_btts:
            btts_risk = result["extended_risk"]["btts"]
            best_btts = (
                "yes"
                if btts_risk["yes"]["risk_score"] >= btts_risk["no"]["risk_score"]
                else "no"
            )
            display_stake_recommendation(
                risk_score=btts_risk[best_btts]["risk_score"],
                odds=btts_risk[best_btts]["odds"],
                market_name=f"BTTS {best_btts.upper()}",
                match_info=f"{result['match_info']['home']} vs {result['match_info']['away']} - BTTS {best_btts.upper()}",
            )
    else:
        st.info(
            "ℹ️ Keine Einsatzempfehlungen - Schwellenwerte nicht erreicht (1X2: ≥50%, O/U & BTTS: ≥60%)"
        )

    # Risiko-Faktoren Details
    with st.expander("📋 RISIKO-FAKTOREN DETAILS"):
        details = overall_risk["details"]
        col1, col2, col3 = st.columns(3)
        col1.metric("μ-Total", f"{details['mu_total_impact']:.2f}")
        col2.metric("TKI kombiniert", f"{details['tki_impact']:.2f}")
        col3.metric("Beste 1X2 Wahrscheinlichkeit", f"{details['favorite_prob']:.1f}%")
        col1.metric("PPG Differenz", f"{details['ppg_diff_abs']:.2f}")
        col2.metric("Durchschn. Risiko", f"{details['average_risk']:.2f}")
        col3.metric("Anpassungen", f"{details['adjustments']:.2f}")

    # TKI
    st.subheader("🧤 Torwart-Krisen-Index (TKI)")
    col1, col2, col3 = st.columns(3)
    with col1:
        tki_home = result["tki"]["home"]
        status_home = "🚨 KRISE" if tki_home > 0.3 else "✅ Stabil"
        st.metric(result["match_info"]["home"], f"{tki_home:.2f}", status_home)
    with col2:
        tki_away = result["tki"]["away"]
        status_away = "🚨 KRISE" if tki_away > 0.3 else "✅ Stabil"
        st.metric(result["match_info"]["away"], f"{tki_away:.2f}", status_away)
    with col3:
        st.metric("Kombiniert", f"{result['tki']['combined']:.2f}")

    # H2H
    st.subheader("🔄 Head-to-Head Statistik")
    h2h = result["h2h"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ø Tore/Spiel", f"{h2h['avg_total_goals']:.1f}")
    col2.metric("Ø Heimtore", f"{h2h['avg_home_goals']:.1f}")
    col3.metric("Ø Auswärtstore", f"{h2h['avg_away_goals']:.1f}")
    col4.metric("BTTS-Quote", f"{h2h['btts_percentage'] * 100:.0f}%")

    st.caption(
        f"Bilanz: {h2h['home_wins']} Siege - {h2h['draws']} Remis - {h2h['away_wins']} Niederlagen"
    )

    # Wahrscheinlichkeiten & Quoten
    st.subheader("📈 Wahrscheinlichkeiten & Quoten")
    probs = result["probabilities"]
    odds = result["odds"]

    # Erstelle Daten mit Highlighting
    data = []

    # 1X2 Markets (Schwellenwert: 50%)
    markets = [
        ("Heimsieg", probs["home_win"], odds["1x2"][0], 50),
        ("Remis", probs["draw"], odds["1x2"][1], 50),
        ("Auswärtssieg", probs["away_win"], odds["1x2"][2], 50),
        ("Over 2.5", probs["over_25"], odds["ou25"][0], 60),
        ("Under 2.5", probs["under_25"], odds["ou25"][1], 60),
        ("BTTS Ja", probs["btts_yes"], odds["btts"][0], 60),
        ("BTTS Nein", probs["btts_no"], odds["btts"][1], 60),
    ]

    for market, prob, quote, threshold in markets:
        # Gelbes Emoji wenn Schwellenwert erreicht
        highlight = "🟡 " if prob >= threshold else ""
        data.append(
            {
                "Markt": f"{highlight}{market}",
                "Wahrscheinlichkeit": f"{prob:.1f}%",
                "Quote": f"{quote:.2f}",
            }
        )

    df = pd.DataFrame(data)
    styled_df = df.style.set_properties(
        **{
            "background-color": "#0e1117",
            "color": "white",
            "font-size": "20px",
            "font-weight": "bold",
        }
    )
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Monte-Carlo-Simulation
    st.markdown("---")
    display_simulation_section(result)

    # Visualisierungen
    st.markdown("---")
    st.subheader("📈 Visualisierungen")

    # Import Visualisierungs-Funktionen
    from ui.visualizations import (
        show_poisson_heatmap,
        show_historical_performance,
        show_confidence_gauge,
        show_team_radar,
    )

    viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs(
        [
            "📊 Poisson-Verteilung",
            "📈 Historische Performance",
            "🎲 Confidence-Level",
            "🕸️ Team-Radar",
        ]
    )

    with viz_tab1:
        show_poisson_heatmap(result)

    with viz_tab2:
        show_historical_performance()

    with viz_tab3:
        show_confidence_gauge(result)

    with viz_tab4:
        try:
            show_team_radar(result)
        except Exception as e:
            st.warning(f"⚠️ Radar-Chart nicht verfügbar: {str(e)}")
            st.info("Das Team-Radar-Chart benötigt vollständige Match-Daten.")


def display_risk_distribution(all_results: List[Dict]):
    """
    Zeigt Risiko-Score Verteilung über alle Matches

    Args:
        all_results: Liste von Analyse-Ergebnissen
    """
    if not all_results:
        return

    scores = []
    for item in all_results:
        if "result" in item and "extended_risk" in item["result"]:
            scores.append(item["result"]["extended_risk"]["overall"]["score"])

    if not scores:
        return

    distribution = Counter(scores)
    total = len(scores)

    st.markdown("---")
    st.subheader("📈 Risiko-Score Verteilung")
    st.caption("Zeigt wie viele Matches jedem Risiko-Level zugeordnet wurden")

    cols = st.columns(5)
    colors = ["darkred", "red", "yellow", "lightgreen", "green"]
    labels = ["1/5 Extrem", "2/5 Hoch", "3/5 Moderat", "4/5 Gering", "5/5 Optimal"]

    for i in range(1, 6):
        count = distribution.get(i, 0)
        percentage = (count / total) * 100 if total > 0 else 0

        with cols[i - 1]:
            st.metric(
                label=labels[i - 1],
                value=f"{count}",
                delta=f"{percentage:.1f}%",
                delta_color="off",
            )
            st.progress(min(percentage / 100, 1.0))

    score_5_pct = (distribution.get(5, 0) / total * 100) if total > 0 else 0
    score_3_pct = (distribution.get(3, 0) / total * 100) if total > 0 else 0

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📊 Verteilungs-Analyse")

        if score_5_pct > 10:
            st.warning(
                f"⚠️ **Zu viele 5/5 Bewertungen** ({score_5_pct:.1f}%) - Scoring könnte zu liberal sein!"
            )
        elif score_5_pct < 1 and total > 20:
            st.info(
                f"ℹ️ Sehr wenige 5/5 Bewertungen ({score_5_pct:.1f}%) - Scoring ist sehr streng"
            )
        elif score_5_pct >= 2 and score_5_pct <= 5:
            st.success(
                f"✅ Optimale 5/5 Verteilung ({score_5_pct:.1f}%) - Scoring funktioniert gut!"
            )

        if score_3_pct > 75:
            st.info(
                "ℹ️ Sehr viele 3/5 Bewertungen - Die meisten Wetten sind moderat riskant"
            )
        elif score_3_pct < 50:
            st.warning("⚠️ Wenige 3/5 Bewertungen - Ungewöhnliche Verteilung")

    with col2:
        st.markdown("### 🎯 Ziel-Verteilung")
        st.caption("""
        **Ideal:**
        - 5/5: 2-5%
        - 4/5: 10-15%
        - 3/5: 60-70%
        - 2/5: 15-20%
        - 1/5: 5-10%
        """)
