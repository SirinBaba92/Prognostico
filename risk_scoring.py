"""
Risiko-Scoring Funktionen für Wettmärkte
"""

from typing import Dict
from data.models import TeamStats


def calculate_risk_score(
    mu_h: float,
    mu_a: float,
    tki_h: float,
    tki_a: float,
    ppg_diff: float,
    h2h_avg_goals: float,
    btts_prob: float,
) -> Dict:
    """
    Berechnet Risiko-Score basierend auf verschiedenen Faktoren
    
    Args:
        mu_h: Erwartete Tore Heim
        mu_a: Erwartete Tore Auswärts
        tki_h: TKI Heim
        tki_a: TKI Auswärts
        ppg_diff: PPG-Differenz
        h2h_avg_goals: Durchschnittliche Tore in H2H
        btts_prob: BTTS Wahrscheinlichkeit (0-100)
        
    Returns:
        Dictionary mit Risiko-Score und Details
    """
    score = 50
    faktor_details = {}

    mu_total = mu_h + mu_a
    faktor_details["mu_total"] = mu_total

    if mu_total > 4.5:
        score += 25
        faktor_details["mu_total_impact"] = "+25"
    elif mu_total > 4.0:
        score += 15
        faktor_details["mu_total_impact"] = "+15"
    elif mu_total > 3.5:
        score += 8
        faktor_details["mu_total_impact"] = "+8"
    elif mu_total < 2.0:
        score -= 15
        faktor_details["mu_total_impact"] = "-15"
    elif mu_total < 2.5:
        score -= 8
        faktor_details["mu_total_impact"] = "-8"
    else:
        faktor_details["mu_total_impact"] = "0"

    tki_combined = tki_h + tki_a
    faktor_details["tki_combined"] = tki_combined

    if tki_combined > 1.0:
        score += 20
        faktor_details["tki_impact"] = "+20"
    elif tki_combined > 0.8:
        score += 15
        faktor_details["tki_impact"] = "+15"
    elif tki_combined > 0.6:
        score += 10
        faktor_details["tki_impact"] = "+10"
    elif tki_combined > 0.4:
        score += 5
        faktor_details["tki_impact"] = "+5"
    else:
        faktor_details["tki_impact"] = "0"

    ppg_diff_abs = abs(ppg_diff)
    faktor_details["ppg_diff"] = ppg_diff_abs

    if ppg_diff_abs > 1.2:
        score -= 20
        faktor_details["ppg_impact"] = "-20"
    elif ppg_diff_abs > 0.8:
        score -= 12
        faktor_details["ppg_impact"] = "-12"
    elif ppg_diff_abs > 0.5:
        score -= 6
        faktor_details["ppg_impact"] = "-6"
    elif ppg_diff_abs < 0.2:
        score += 15
        faktor_details["ppg_impact"] = "+15"
    elif ppg_diff_abs < 0.3:
        score += 8
        faktor_details["ppg_impact"] = "+8"
    else:
        faktor_details["ppg_impact"] = "0"

    faktor_details["h2h_avg_goals"] = h2h_avg_goals

    if h2h_avg_goals > 4.5:
        score += 12
        faktor_details["h2h_impact"] = "+12"
    elif h2h_avg_goals > 4.0:
        score += 8
        faktor_details["h2h_impact"] = "+8"
    elif h2h_avg_goals > 3.5:
        score += 4
        faktor_details["h2h_impact"] = "+4"
    elif h2h_avg_goals < 1.5:
        score -= 10
        faktor_details["h2h_impact"] = "-10"
    else:
        faktor_details["h2h_impact"] = "0"

    faktor_details["btts_prob"] = btts_prob

    if btts_prob > 75:
        score += 8
        faktor_details["btts_impact"] = "+8"
    elif btts_prob > 65:
        score += 4
        faktor_details["btts_impact"] = "+4"
    elif btts_prob < 35:
        score -= 6
        faktor_details["btts_impact"] = "-6"
    else:
        faktor_details["btts_impact"] = "0"

    score = max(0, min(100, score))

    if score < 25:
        kategorie = "🟢 SEHR GERINGES RISIKO"
        color = "green"
        empfehlung = "Gute Basis für Wetten"
    elif score < 40:
        kategorie = "🟢 GERINGES RISIKO"
        color = "lightgreen"
        empfehlung = "Solide Wettmöglichkeit"
    elif score < 55:
        kategorie = "🟡 MODERATES RISIKO"
        color = "yellow"
        empfehlung = "Standard-Risiko"
    elif score < 70:
        kategorie = "🟠 ERHÖHTES RISIKO"
        color = "orange"
        empfehlung = "Vorsicht bei Wetten"
    elif score < 85:
        kategorie = "🔴 HOHES RISIKO"
        color = "red"
        empfehlung = "Nur für erfahrene Wettende"
    else:
        kategorie = "🔴 EXTREM HOHES RISIKO"
        color = "darkred"
        empfehlung = "Sehr spekulativ"

    return {
        "score": round(score),
        "kategorie": kategorie,
        "color": color,
        "empfehlung": empfehlung,
        "faktoren": faktor_details,
        "details": {
            "mu_total": f"{mu_total:.1f} ({faktor_details['mu_total_impact']})",
            "tki_combined": f"{tki_combined:.2f} ({faktor_details['tki_impact']})",
            "ppg_diff": f"{ppg_diff_abs:.2f} ({faktor_details['ppg_impact']})",
            "h2h_avg_goals": f"{h2h_avg_goals:.1f} ({faktor_details['h2h_impact']})",
            "btts_prob": f"{btts_prob:.1f}% ({faktor_details['btts_impact']})",
        },
    }


def calculate_extended_risk_scores_strict(
    prob_1x2_home: float,
    prob_1x2_draw: float,
    prob_1x2_away: float,
    prob_over: float,
    prob_under: float,
    prob_btts_yes: float,
    prob_btts_no: float,
    odds_1x2: tuple,
    odds_ou: tuple,
    odds_btts: tuple,
    mu_total: float,
    tki_combined: float,
    ppg_diff: float,
    home_team: TeamStats,
    away_team: TeamStats,
) -> Dict:
    """
    Berechnet erweiterte Risiko-Scores für alle Wettmärkte (1-5 Skala)
    
    Args:
        prob_1x2_home: Wahrscheinlichkeit Heimsieg (%)
        prob_1x2_draw: Wahrscheinlichkeit Unentschieden (%)
        prob_1x2_away: Wahrscheinlichkeit Auswärtssieg (%)
        prob_over: Wahrscheinlichkeit Over 2.5 (%)
        prob_under: Wahrscheinlichkeit Under 2.5 (%)
        prob_btts_yes: Wahrscheinlichkeit BTTS Ja (%)
        prob_btts_no: Wahrscheinlichkeit BTTS Nein (%)
        odds_1x2: Quoten (Heim, X, Auswärts)
        odds_ou: Quoten (Over, Under)
        odds_btts: Quoten (Ja, Nein)
        mu_total: Erwartete Gesamt-Tore
        tki_combined: Kombinierter TKI
        ppg_diff: PPG-Differenz
        home_team: Heimteam Stats
        away_team: Auswärtsteam Stats
        
    Returns:
        Dictionary mit detaillierten Risiko-Scores pro Market
    """

    def strict_risk_description(score: int) -> str:
        descriptions = {
            1: "🔴 EXTREM RISIKANT",
            2: "🔴 HOHES RISIKO",
            3: "🟡 MODERATES RISIKO",
            4: "🟢 GERINGES RISIKO",
            5: "🟢 OPTIMALES RISIKO",
        }
        return descriptions.get(score, "🟡 MODERATES RISIKO")

    def calculate_1x2_risk_strict(
        best_prob: float, best_odds: float, second_best_prob: float
    ) -> int:
        ev = (best_prob / 100) * best_odds - 1
        prob_dominance = (
            best_prob - second_best_prob if second_best_prob > 0 else best_prob
        )

        if ev < -0.15:
            return 1
        elif ev < -0.05:
            return 2
        elif ev < 0.08:
            if prob_dominance < 10:
                return 3
            else:
                return 4
        elif ev < 0.18:
            if prob_dominance > 15:
                return 4
            else:
                return 3
        else:
            if prob_dominance > 20 and ev > 0.25:
                return 5
            else:
                return 4

    probs_1x2 = [prob_1x2_home, prob_1x2_draw, prob_1x2_away]
    markets = ["Heimsieg", "Unentschieden", "Auswärtssieg"]
    sorted_probs = sorted(
        zip(probs_1x2, odds_1x2, markets), key=lambda x: x[0], reverse=True
    )

    best_prob, best_odds, best_market = sorted_probs[0]
    second_best_prob = sorted_probs[1][0]

    risk_1x2 = calculate_1x2_risk_strict(best_prob, best_odds, second_best_prob)

    def calculate_ou_risk_strict(prob: float, odds: float, mu_total: float) -> int:
        ev = (prob / 100) * odds - 1
        mu_adjustment = 0

        if mu_total > 4.0 and prob > 65:
            mu_adjustment = -1
        elif mu_total < 2.0 and prob > 65:
            mu_adjustment = -1

        if ev < -0.15:
            base_score = 1
        elif ev < -0.05:
            base_score = 2
        elif ev < 0.10:
            base_score = 3
        elif ev < 0.20:
            base_score = 4
        else:
            base_score = 5

        return max(1, min(5, base_score + mu_adjustment))

    risk_over = calculate_ou_risk_strict(prob_over, odds_ou[0], mu_total)
    risk_under = calculate_ou_risk_strict(prob_under, odds_ou[1], mu_total)

    def calculate_btts_risk_strict(
        prob: float, odds: float, home_cs_rate: float, away_cs_rate: float
    ) -> int:
        ev = (prob / 100) * odds - 1
        cs_penalty = 0
        avg_cs_rate = (home_cs_rate + away_cs_rate) / 2

        if prob > 70:
            if avg_cs_rate > 0.4:
                cs_penalty = -2
            elif avg_cs_rate > 0.3:
                cs_penalty = -1

        if ev < -0.15:
            base_score = 1
        elif ev < -0.05:
            base_score = 2
        elif ev < 0.12:
            base_score = 3
        elif ev < 0.22:
            base_score = 4
        else:
            base_score = 5

        return max(1, min(5, base_score + cs_penalty))

    risk_btts_yes = calculate_btts_risk_strict(
        prob_btts_yes, odds_btts[0], home_team.cs_yes_ha, away_team.cs_yes_ha
    )
    risk_btts_no = calculate_btts_risk_strict(
        prob_btts_no, odds_btts[1], home_team.cs_yes_ha, away_team.cs_yes_ha
    )

    def calculate_overall_risk_strict(
        risk_1x2: int,
        risk_over: int,
        risk_under: int,
        risk_btts_yes: int,
        risk_btts_no: int,
        best_1x2_prob: float,
        mu_total: float,
        tki_combined: float,
        ppg_diff: float,
        home_games: int,
        away_games: int,
    ) -> Dict:

        weights = {"1x2": 0.35, "ou": 0.30, "btts": 0.25, "data_quality": 0.10}

        data_quality_score = 3
        if home_games < 10 or away_games < 10:
            data_quality_score = 2
        if home_games < 5 or away_games < 5:
            data_quality_score = 1

        avg_risk = (
            risk_1x2 * weights["1x2"]
            + ((risk_over + risk_under) / 2) * weights["ou"]
            + ((risk_btts_yes + risk_btts_no) / 2) * weights["btts"]
            + data_quality_score * weights["data_quality"]
        )

        adjustments = 0.0

        if mu_total > 4.5:
            adjustments -= 1.5
        elif mu_total > 4.0:
            adjustments -= 1.0
        elif mu_total > 3.5:
            adjustments -= 0.6
        elif mu_total < 2.0:
            adjustments += 0.3

        if tki_combined > 1.0:
            adjustments -= 1.5
        elif tki_combined > 0.8:
            adjustments -= 1.0
        elif tki_combined > 0.6:
            adjustments -= 0.6

        ppg_diff_abs = abs(ppg_diff)

        if ppg_diff_abs > 1.5:
            if best_1x2_prob > 75:
                adjustments -= 0.5
            else:
                adjustments += 0.3
        elif ppg_diff_abs > 1.0:
            adjustments += 0.1
        elif ppg_diff_abs < 0.2:
            adjustments += 0.4

        if best_1x2_prob > 75:
            adjustments -= 0.3
        elif best_1x2_prob > 65:
            adjustments += 0.1
        elif best_1x2_prob < 35:
            adjustments -= 0.3

        best_odds_value = max(odds_1x2)
        if best_odds_value > 3.0:
            adjustments -= 0.5
        elif best_odds_value < 1.5:
            adjustments -= 0.3

        total_games = home_games + away_games
        if total_games < 20:
            adjustments -= 0.5

        final_score = avg_risk + adjustments

        if final_score > 4.7:
            final_score_int = 5
        elif final_score > 3.7:
            final_score_int = 4
        elif final_score > 2.7:
            final_score_int = 3
        elif final_score > 1.7:
            final_score_int = 2
        else:
            final_score_int = 1

        if final_score_int == 1:
            category = "🔴 EXTREM RISIKANT"
            recommendation = "Vermeiden - sehr spekulativ"
            color = "darkred"
            score_text = "1/5"
            emoji = "☠️"
        elif final_score_int == 2:
            category = "🔴 HOHES RISIKO"
            recommendation = "Nur für erfahrene Wettende mit kleinem Einsatz"
            color = "red"
            score_text = "2/5"
            emoji = "⚠️"
        elif final_score_int == 3:
            category = "🟡 MODERATES RISIKO"
            recommendation = "Standard-Wette mit normalem Einsatz"
            color = "yellow"
            score_text = "3/5"
            emoji = "📊"
        elif final_score_int == 4:
            category = "🟢 GERINGES RISIKO"
            recommendation = "Gute Wettmöglichkeit - empfohlener Einsatz"
            color = "lightgreen"
            score_text = "4/5"
            emoji = "✅"
        else:
            category = "🟢 OPTIMALES RISIKO"
            recommendation = "Seltene Top-Wette - erhöhter Einsatz möglich"
            color = "green"
            score_text = "5/5"
            emoji = "🎯"

        return {
            "score": final_score_int,
            "score_text": score_text,
            "category": category,
            "recommendation": recommendation,
            "color": color,
            "emoji": emoji,
            "details": {
                "average_risk": round(avg_risk, 2),
                "adjustments": round(adjustments, 2),
                "mu_total_impact": mu_total,
                "tki_impact": tki_combined,
                "favorite_prob": best_1x2_prob,
                "ppg_diff_abs": ppg_diff_abs,
                "best_odds": round(best_odds_value, 2),
                "data_quality": f"{home_games}/{away_games} Spiele",
            },
        }

    overall_risk = calculate_overall_risk_strict(
        risk_1x2,
        risk_over,
        risk_under,
        risk_btts_yes,
        risk_btts_no,
        best_prob,
        mu_total,
        tki_combined,
        ppg_diff,
        home_team.games,
        away_team.games,
    )

    return {
        "overall": overall_risk,
        "1x2": {
            "market": best_market,
            "probability": best_prob,
            "odds": best_odds,
            "risk_score": risk_1x2,
            "risk_text": strict_risk_description(risk_1x2),
            "second_best_prob": second_best_prob,
            "prob_dominance": best_prob - second_best_prob,
            "ev": (best_prob / 100) * best_odds - 1,
        },
        "over_under": {
            "over": {
                "probability": prob_over,
                "odds": odds_ou[0],
                "risk_score": risk_over,
                "risk_text": strict_risk_description(risk_over),
                "ev": (prob_over / 100) * odds_ou[0] - 1,
            },
            "under": {
                "probability": prob_under,
                "odds": odds_ou[1],
                "risk_score": risk_under,
                "risk_text": strict_risk_description(risk_under),
                "ev": (prob_under / 100) * odds_ou[1] - 1,
            },
        },
        "btts": {
            "yes": {
                "probability": prob_btts_yes,
                "odds": odds_btts[0],
                "risk_score": risk_btts_yes,
                "risk_text": strict_risk_description(risk_btts_yes),
                "ev": (prob_btts_yes / 100) * odds_btts[0] - 1,
            },
            "no": {
                "probability": prob_btts_no,
                "odds": odds_btts[1],
                "risk_score": risk_btts_no,
                "risk_text": strict_risk_description(risk_btts_no),
                "ev": (prob_btts_no / 100) * odds_btts[1] - 1,
            },
        },
        "risk_factors": {
            "mu_total": mu_total,
            "tki_combined": tki_combined,
            "ppg_diff": ppg_diff,
            "home_games": home_team.games,
            "away_games": away_team.games,
            "avg_cs_rate": (home_team.cs_yes_ha + away_team.cs_yes_ha) / 2,
        },
    }
