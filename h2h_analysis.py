"""
Head-to-Head Analyse Funktionen
"""

from typing import List, Dict
from data.models import TeamStats, H2HResult


def analyze_h2h(home: TeamStats, away: TeamStats, h2h_data: List[H2HResult]) -> Dict:
    """
    Analysiert Head-to-Head Statistiken zwischen zwei Teams
    
    Args:
        home: Heimteam Statistics
        away: Auswärtsteam Statistics
        h2h_data: Liste von H2H-Ergebnissen
        
    Returns:
        Dictionary mit H2H-Statistiken
    """
    if not h2h_data:
        return {
            "avg_total_goals": 2.5,
            "avg_home_goals": 1.5,
            "avg_away_goals": 1.0,
            "home_wins": 0,
            "draws": 0,
            "away_wins": 0,
            "btts_percentage": 0.5,
        }

    total_goals = []
    home_goals_list = []
    away_goals_list = []
    home_wins = 0
    draws = 0
    away_wins = 0
    btts_count = 0

    for result in h2h_data:
        total_goals.append(result.home_goals + result.away_goals)

        if result.home_team == home.name:
            home_goals_list.append(result.home_goals)
            away_goals_list.append(result.away_goals)

            if result.home_goals > result.away_goals:
                home_wins += 1
            elif result.home_goals == result.away_goals:
                draws += 1
            else:
                away_wins += 1
        else:
            home_goals_list.append(result.away_goals)
            away_goals_list.append(result.home_goals)

            if result.away_goals > result.home_goals:
                home_wins += 1
            elif result.home_goals == result.away_goals:
                draws += 1
            else:
                away_wins += 1

        if result.home_goals > 0 and result.away_goals > 0:
            btts_count += 1

    return {
        "avg_total_goals": sum(total_goals) / len(total_goals),
        "avg_home_goals": sum(home_goals_list) / len(home_goals_list),
        "avg_away_goals": sum(away_goals_list) / len(away_goals_list),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "btts_percentage": btts_count / len(h2h_data),
    }
