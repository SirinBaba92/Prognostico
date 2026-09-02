"""
Monte-Carlo-Spielsimulation

Simuliert ein Spiel N-mal auf Basis der bereits berechneten μ-Werte
(erwartete Tore Heim/Auswärts aus SMART-PRECISION oder einem späteren
Dixon-Coles-Modell) und liefert empirische Wahrscheinlichkeiten für
1X2, Über/Unter 2.5, BTTS sowie die häufigsten Ergebnisse.

Bewusst getrennt von match_analysis.py gehalten: die Simulation nimmt
nur mu_home/mu_away entgegen und ist damit unabhängig davon, welches
Modell diese Werte liefert.
"""

import numpy as np
from typing import Dict, Optional


def simulate_match(
    mu_home: float,
    mu_away: float,
    n_sims: int = 10_000,
    seed: Optional[int] = None,
    top_n_scorelines: int = 10,
) -> Dict:
    """
    Simuliert ein Spiel n_sims-mal per Poisson-Ziehung.

    Args:
        mu_home: Erwartete Tore Heimteam (aus analyze_match_v47_ml -> result["mu"]["home"])
        mu_away: Erwartete Tore Auswärtsteam
        n_sims: Anzahl Durchläufe (z.B. 1_000 / 10_000 / 100_000 / 1_000_000)
        seed: Optionaler Seed für Reproduzierbarkeit (None = zufällig)
        top_n_scorelines: Wie viele häufigste Ergebnisse zurückgegeben werden

    Returns:
        Dictionary mit Wahrscheinlichkeiten, Konfidenzintervallen (95%) und
        den häufigsten simulierten Ergebnissen.
    """
    if n_sims <= 0:
        raise ValueError("n_sims muss > 0 sein")

    rng = np.random.default_rng(seed)

    # Vektorisierte Poisson-Ziehung -- auch bei 1 Mio. Durchläufen < 1s
    home_goals = rng.poisson(max(mu_home, 0.0), n_sims)
    away_goals = rng.poisson(max(mu_away, 0.0), n_sims)

    total_goals = home_goals + away_goals

    home_win = float(np.mean(home_goals > away_goals))
    draw = float(np.mean(home_goals == away_goals))
    away_win = float(np.mean(home_goals < away_goals))
    over25 = float(np.mean(total_goals > 2.5))
    under25 = 1.0 - over25
    btts_yes = float(np.mean((home_goals > 0) & (away_goals > 0)))
    btts_no = 1.0 - btts_yes

    def _ci95(p: float) -> float:
        """Halbe Breite des 95%-Konfidenzintervalls (Normalapprox. der Binomialverteilung)."""
        return 1.96 * ((p * (1 - p)) / n_sims) ** 0.5

    # Häufigste Ergebnisse (vektorisiert statt Counter -> deutlich schneller bei großem n_sims)
    scorelines = np.stack([home_goals, away_goals], axis=1)
    unique_scores, counts = np.unique(scorelines, axis=0, return_counts=True)
    order = np.argsort(-counts)[:top_n_scorelines]
    top_scorelines = [
        (f"{unique_scores[i][0]}-{unique_scores[i][1]}", round(float(counts[i]) / n_sims * 100, 2))
        for i in order
    ]

    return {
        "n_sims": n_sims,
        "mu_home": mu_home,
        "mu_away": mu_away,
        "probabilities": {
            "home_win": round(home_win * 100, 1),
            "draw": round(draw * 100, 1),
            "away_win": round(away_win * 100, 1),
            "over_25": round(over25 * 100, 1),
            "under_25": round(under25 * 100, 1),
            "btts_yes": round(btts_yes * 100, 1),
            "btts_no": round(btts_no * 100, 1),
        },
        "confidence_95": {
            "home_win": round(_ci95(home_win) * 100, 2),
            "draw": round(_ci95(draw) * 100, 2),
            "away_win": round(_ci95(away_win) * 100, 2),
            "over_25": round(_ci95(over25) * 100, 2),
            "btts_yes": round(_ci95(btts_yes) * 100, 2),
        },
        "avg_goals": {
            "home": round(float(home_goals.mean()), 2),
            "away": round(float(away_goals.mean()), 2),
            "total": round(float(total_goals.mean()), 2),
        },
        "top_scorelines": top_scorelines,
    }
