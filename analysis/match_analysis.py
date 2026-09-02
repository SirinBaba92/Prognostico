"""
Haupt-Analyse-Funktion für Match-Prognosen (v4.7+ SMART-PRECISION)
"""

import streamlit as st
from typing import Dict, Optional
from data.models import MatchData, ExtendedMatchData
from utils.math_helpers import poisson_probability
from analysis.h2h_analysis import analyze_h2h
from analysis.risk_scoring import (
    calculate_risk_score,
    calculate_extended_risk_scores_strict,
)

def _safe_get_session(key):
    """Gibt None zurück wenn kein Streamlit-Kontext vorhanden"""
    try:
        return st.session_state.get(key)
    except Exception:
        return None

def analyze_match_v47_ml(match: MatchData) -> Dict:
    """
    v6.0 mit v4.9 SMART-PRECISION LOGIK + ML-Korrekturen

    NEU von v4.9:
    - Form-Faktoren Integration
    - TKI-Krise deaktiviert BTTS-Dominanz-Killer
    - FTS-Check nur bei PPG > 1.0 (nicht 0.5)
    - Form-Boost bei starker Defensive reduziert
    - TKI-Krise überschreibt Form-Malus
    - Strengere Dominanz-Dämpfer
    - Auswärts-Underdog Boost
    - Verschärfte Clean Sheet Validierung
    - Conversion-Rate Adjustment

    Args:
        match: MatchData Objekt mit allen Spiel-Informationen

    Returns:
        Dictionary mit vollständiger Analyse
    """

    # DATEN-EXTRAKTION
    s_c_ha = [
        match.home_team.goals_scored_per_match_ha,
        match.home_team.goals_conceded_per_match_ha,
        match.away_team.goals_scored_per_match_ha,
        match.away_team.goals_conceded_per_match_ha,
    ]

    xg_ha = [
        match.home_team.xg_for_ha,
        match.home_team.xg_against_ha,
        match.away_team.xg_for_ha,
        match.away_team.xg_against_ha,
    ]

    cs_rates = [match.home_team.cs_yes_ha * 100, match.away_team.cs_yes_ha * 100]

    ppg = [match.home_team.ppg_ha, match.away_team.ppg_ha]

    conv_rate = [
        match.home_team.conversion_rate * 100,
        match.away_team.conversion_rate * 100,
    ]

    # Form-Daten
    form_ppg_h = match.home_team.form_points / 5
    form_ppg_a = match.away_team.form_points / 5

    # Failed to Score
    fts_h = match.home_team.fts_yes_ha
    fts_a = match.away_team.fts_yes_ha

    # --- v4.9 SMART-PRECISION LOGIK ---

    # 1. BASIS μ
    mu_h = (xg_ha[0] + s_c_ha[0]) / 2
    mu_a = (xg_ha[2] + s_c_ha[2]) / 2

    # 2. FORM-FAKTOR
    def calculate_form_factor(form_ppg, overall_ppg):
        if overall_ppg == 0:
            return 1.0
        form_ratio = form_ppg / overall_ppg

        if form_ratio < 0.4:
            return 0.70
        elif form_ratio < 0.6:
            return 0.85
        elif form_ratio > 1.5:
            return 1.20
        elif form_ratio > 1.2:
            return 1.10
        else:
            return 1.0

    form_factor_h = calculate_form_factor(form_ppg_h, ppg[0])
    form_factor_a = calculate_form_factor(form_ppg_a, ppg[1])

    # 3. TKI BERECHNUNG (früh, für spätere Checks)
    tki_h = max(0, s_c_ha[1] - xg_ha[1])
    tki_a = max(0, s_c_ha[3] - xg_ha[3])
    tki_combined = tki_h + tki_a

    # 4. NEU v4.9: TKI-KRISE ÜBERSCHREIBT FORM-MALUS
    if tki_a > 1.0:  # Gast-Keeper in Krise
        if form_factor_h < 1.0:
            form_factor_h = 1.0  # Ignoriere Heim-Form-Malus

    if tki_h > 1.0:  # Heim-Keeper in Krise
        if form_factor_a < 1.0:
            form_factor_a = 1.0  # Ignoriere Gast-Form-Malus

    # 5. NEU v4.9: DEFENSIVE CONTEXT CHECK (Form-Boost reduzieren)
    if cs_rates[0] > 40 and form_factor_h > 1.0:
        form_factor_h = 1.0 + (form_factor_h - 1.0) * 0.5  # Halbiere den Boost

    if cs_rates[1] > 40 and form_factor_a > 1.0:
        form_factor_a = 1.0 + (form_factor_a - 1.0) * 0.5

    # 6. Form-Faktor anwenden
    mu_h *= form_factor_h
    mu_a *= form_factor_a

    # 7. DOMINANZ-DÄMPFER (aggressiv)
    ppg_diff = ppg[0] - ppg[1]

    if ppg_diff > 1.5:
        mu_a *= 0.45
        mu_h *= 1.30
    elif ppg_diff > 1.2:
        mu_a *= 0.55
        mu_h *= 1.25
    elif ppg_diff > 0.8:
        mu_a *= 0.65
        mu_h *= 1.15

    # 8. AUSWÄRTS-UNDERDOG BOOST
    if ppg_diff < -0.5:
        mu_a *= 1.20
        mu_h *= 0.80
    elif ppg_diff < -0.3:
        mu_a *= 1.10
        mu_h *= 0.90

    # 9. CLEAN SHEET VALIDIERUNG (verschärft)
    if cs_rates[0] > 50:
        mu_a *= 0.70
    elif cs_rates[0] > 40:
        mu_a *= 0.80
    elif cs_rates[0] > 30:
        mu_a *= 0.85

    if cs_rates[1] > 50:
        mu_h *= 0.70
    elif cs_rates[1] > 40:
        mu_h *= 0.80
    elif cs_rates[1] > 30:
        mu_h *= 0.85

    # 10. TKI-BOOST
    mu_h = mu_h * (1 + (tki_a * 0.4))
    mu_a = mu_a * (1 + (tki_h * 0.4))

    # 11. CONVERSION-RATE ADJUSTMENT
    def apply_conversion_adjustment(mu, conversion_rate):
        if conversion_rate > 14:
            return mu * 1.10
        elif conversion_rate < 8:
            return mu * 0.90
        return mu

    mu_h = apply_conversion_adjustment(mu_h, conv_rate[0])
    mu_a = apply_conversion_adjustment(mu_a, conv_rate[1])

    # ML-Korrektur (Phase 3) - NACH allen v4.9 Anpassungen
    ml_info = {"applied": False, "reason": "ML-Modell nicht initialisiert"}

    # NEU:
    _pos_model = _safe_get_session("position_ml_model")
    if (
        _pos_model
        and _pos_model.is_trained
    ):
        ml_correction = _pos_model.predict_correction(
            home_team=match.home_team, away_team=match.away_team, match_date=match.date
        )

        if ml_correction["is_trained"] and ml_correction["confidence"] > 0.3:
            mu_h_original = mu_h
            mu_a_original = mu_a

            mu_h *= ml_correction["home_correction"]
            mu_a *= ml_correction["away_correction"]

            ml_info = {
                "applied": True,
                "home_correction": ml_correction["home_correction"],
                "away_correction": ml_correction["away_correction"],
                "confidence": ml_correction["confidence"],
                "original_mu": {"home": mu_h_original, "away": mu_a_original},
                "corrected_mu": {"home": mu_h, "away": mu_a},
                "message": ml_correction["message"],
            }
        else:
            ml_info = {
                "applied": False,
                "reason": ml_correction["message"],
                "confidence": ml_correction["confidence"],
            }

    # 12. POISSON MATRIX
    wh, dr, wa, ov25, btts_p = 0.0, 0.0, 0.0, 0.0, 0.0
    max_p, score = 0.0, (0, 0)
    scoreline_probs = []  # sammle Poisson-Scoreline-Wahrscheinlichkeiten

    for i in range(9):
        for j in range(9):
            p = poisson_probability(mu_h, i) * poisson_probability(mu_a, j)
            scoreline_probs.append((i, j, p))
            if i > j:
                wh += p
            elif i == j:
                dr += p
            else:
                wa += p
            if (i + j) > 2.5:
                ov25 += p
            if i > 0 and j > 0:
                btts_p += p
            if p > max_p:
                max_p, score = p, (i, j)


    # Top-Scorelines für UI/Export (damit predicted_score bei starken OU/BTTS-Signalen konsistent gewählt werden kann)
    scoreline_probs.sort(key=lambda x: x[2], reverse=True)
    top_scorelines = [(f"{i}-{j}", round(p * 100, 2)) for i, j, p in scoreline_probs[:20]]

    # KONSISTENZ-FIX: predicted_score darf nicht dem 1X2-Tipp widersprechen.
    # score/max_p oben ist das globale Maximum über ALLE Zellen - das kann eine
    # andere Ergebnis-Kategorie (Heimsieg/Remis/Auswärtssieg) sein als der
    # tatsächliche 1X2-Tipp (der aus der SUMME wh/dr/wa gebildet wird).
    # Deshalb hier: unter den Zellen, die zur Tipp-Kategorie passen, die
    # wahrscheinlichste nehmen - garantiert konsistent mit dem 1X2-Tipp.
    if wh >= dr and wh >= wa:
        tipp_kategorie = "home"
    elif wa >= wh and wa >= dr:
        tipp_kategorie = "away"
    else:
        tipp_kategorie = "draw"

    consistent_max_p, consistent_score = 0.0, score
    for i, j, p in scoreline_probs:
        if tipp_kategorie == "home" and i > j:
            passt = True
        elif tipp_kategorie == "away" and i < j:
            passt = True
        elif tipp_kategorie == "draw" and i == j:
            passt = True
        else:
            passt = False
        if passt and p > consistent_max_p:
            consistent_max_p, consistent_score = p, (i, j)

    score = consistent_score

    # 13. BTTS-PRÄZISIONS-FILTER v4.9
    if mu_h < 1.0 or mu_a < 1.0:
        btts_p *= 0.8

    # NEU v4.9: DOMINANZ-KILLER (nur wenn KEINE TKI-Krise!)
    if tki_combined < 0.8:  # Nur bei stabilen Defensiven
        if ppg_diff > 1.0:
            btts_p *= 0.60
        elif ppg_diff > 0.8:
            btts_p *= 0.75

    # NEU v4.9: FAILED TO SCORE CHECK (nur bei starker Dominanz)
    if fts_a > 0.30 and ppg_diff > 1.0:  # GEÄNDERT von 0.5 auf 1.0
        btts_p *= 0.70
    if fts_h > 0.30 and ppg_diff < -1.0:  # GEÄNDERT von -0.5 auf -1.0
        btts_p *= 0.70

    h2h_stats = analyze_h2h(match.home_team, match.away_team, match.h2h_results)

    risk_score = calculate_risk_score(
        mu_h, mu_a, tki_h, tki_a, ppg_diff, h2h_stats["avg_total_goals"], btts_p * 100
    )

    extended_risk = calculate_extended_risk_scores_strict(
        prob_1x2_home=wh * 100,
        prob_1x2_draw=dr * 100,
        prob_1x2_away=wa * 100,
        prob_over=ov25 * 100,
        prob_under=(1 - ov25) * 100,
        prob_btts_yes=btts_p * 100,
        prob_btts_no=(1 - btts_p) * 100,
        odds_1x2=match.odds_1x2,
        odds_ou=match.odds_ou25,
        odds_btts=match.odds_btts,
        mu_total=mu_h + mu_a,
        tki_combined=tki_h + tki_a,
        ppg_diff=ppg_diff,
        home_team=match.home_team,
        away_team=match.away_team,
    )

    result = {
        "match_info": {
            "home": match.home_team.name,
            "away": match.away_team.name,
            "date": match.date,
            "competition": match.competition,
            "kickoff": match.kickoff,
        },
        "tki": {
            "home": round(tki_h, 2),
            "away": round(tki_a, 2),
            "combined": round(tki_h + tki_a, 2),
        },
        "mu": {
            "home": round(mu_h, 2),
            "away": round(mu_a, 2),
            "total": round(mu_h + mu_a, 2),
            "ppg_diff": round(ppg_diff, 2),
        },
        "form": {
            "home_factor": round(form_factor_h, 2),
            "away_factor": round(form_factor_a, 2),
            "home_ppg": round(form_ppg_h, 2),
            "away_ppg": round(form_ppg_a, 2),
        },
        "h2h": h2h_stats,
        "probabilities": {
            "home_win": round(wh * 100, 1),
            "draw": round(dr * 100, 1),
            "away_win": round(wa * 100, 1),
            "over_25": round(ov25 * 100, 1),
            "under_25": round((1 - ov25) * 100, 1),
            "btts_yes": round(btts_p * 100, 1),
            "btts_no": round((1 - btts_p) * 100, 1),
        },
        "scorelines": top_scorelines,
        "predicted_score": f"{score[0]}-{score[1]}",
        "risk_score": risk_score,
        "extended_risk": extended_risk,
        "ml_position_correction": ml_info,
        "odds": {
            "1x2": match.odds_1x2,
            "ou25": match.odds_ou25,
            "btts": match.odds_btts,
        },
    }

    # Versuche zu speichern (optional - import wird später hinzugefügt)
    try:
        from models.tracking import save_prediction_to_sheets

        save_prediction_to_sheets(
            match_info=result["match_info"],
            probabilities=result["probabilities"],
            odds=result["odds"],
            risk_score=result["extended_risk"]["overall"],
            predicted_score=result["predicted_score"],
            mu_info=result["mu"],
        )
    except Exception:
        pass

    return result


def analyze_match_with_extended_data(
    match: MatchData, extended_data: Optional[ExtendedMatchData] = None
):
    """
    Analysiert Match mit erweiterten Daten (Phase 4)

    Args:
        match: Basis MatchData
        extended_data: Optional erweiterte Match-Daten

    Returns:
        Analyse-Ergebnis mit optionaler Extended-ML Korrektur
    """
    result = analyze_match_v47_ml(match)

    if (
        extended_data
        and st.session_state.get("extended_ml_model")
        and st.session_state.extended_ml_model.is_trained
    ):
        from ml.features import create_position_features, create_extended_features

        position_features = create_position_features(
            match.home_team, match.away_team, match.date
        )

        extended_features = create_extended_features(
            extended_data,
            {"actual_score": f"{result['mu']['home']:.0f}:{result['mu']['away']:.0f}"},
        )

        extended_ml = st.session_state.extended_ml_model
        extended_correction = extended_ml.predict_with_extended_data(
            position_features, extended_features
        )

        if extended_correction.get("confidence", 0) > 0.3:
            original_mu = result["mu"].copy()

            result["mu"]["home"] *= extended_correction["home_correction"]
            result["mu"]["away"] *= extended_correction["away_correction"]
            result["mu"]["total"] = result["mu"]["home"] + result["mu"]["away"]

            result["extended_ml_correction"] = {
                "applied": True,
                "home_correction": extended_correction["home_correction"],
                "away_correction": extended_correction["away_correction"],
                "confidence": extended_correction["confidence"],
                "match_type": extended_correction.get("match_type", 0),
                "features_used": extended_correction.get("features_used", 0),
                "original_mu": original_mu,
                "message": f"Erweiterte ML-Korrektur (Spieltyp: {extended_correction.get('match_type', 0)})",
            }
        else:
            result["extended_ml_correction"] = {
                "applied": False,
                "message": extended_correction.get("message", "Konfidenz zu niedrig"),
            }
    else:
        result["extended_ml_correction"] = {
            "applied": False,
            "message": "Keine erweiterten Daten oder ML-Modell nicht trainiert",
        }

    return result
