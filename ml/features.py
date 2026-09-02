"""
Feature Engineering für ML-Modelle
"""

from typing import Dict
from datetime import datetime
from data.models import TeamStats, ExtendedMatchData


def create_position_features(
    home_team: TeamStats, away_team: TeamStats, match_date: str, total_teams: int = 18
) -> Dict:
    """
    Erstellt Features basierend auf Tabellenpositionen
    
    Args:
        home_team: Heimteam Statistics
        away_team: Auswärtsteam Statistics
        match_date: Datum des Matches (YYYY-MM-DD)
        total_teams: Anzahl Teams in der Liga
        
    Returns:
        Dictionary mit Position-Features
    """
    features = {}

    features["home_position"] = home_team.position
    features["away_position"] = away_team.position
    features["position_diff"] = home_team.position - away_team.position
    features["position_diff_abs"] = abs(features["position_diff"])

    features["home_pos_norm"] = (home_team.position - 1) / (total_teams - 1)
    features["away_pos_norm"] = (away_team.position - 1) / (total_teams - 1)

    features["home_ppg"] = home_team.points / max(home_team.games, 1)
    features["away_ppg"] = away_team.points / max(away_team.games, 1)
    features["ppg_diff"] = features["home_ppg"] - features["away_ppg"]
    features["ppg_diff_abs"] = abs(features["ppg_diff"])

    def get_table_zone(position, total_teams):
        if position <= 3:
            return "champions_league"
        elif position <= 6:
            return "europa_league"
        elif position <= total_teams - 4:
            return "midfield"
        elif position <= total_teams - 2:
            return "relegation_threat"
        else:
            return "direct_relegation"

    features["home_zone"] = get_table_zone(home_team.position, total_teams)
    features["away_zone"] = get_table_zone(away_team.position, total_teams)

    features["season_progress"] = home_team.games / 34

    def calculate_pressure(position, games_played, season_progress):
        pressure = 0.0

        if position >= total_teams - 2:
            pressure += 0.8
        elif position >= total_teams - 4:
            pressure += 0.5

        if position <= 3:
            pressure += 0.4

        if season_progress > 0.75:
            pressure *= 1.3

        return min(1.0, pressure)

    features["home_pressure"] = calculate_pressure(
        home_team.position, home_team.games, features["season_progress"]
    )
    features["away_pressure"] = calculate_pressure(
        away_team.position, away_team.games, features["season_progress"]
    )

    features["is_top_vs_bottom"] = (
        1 if home_team.position <= 3 and away_team.position >= total_teams - 3 else 0
    )
    features["is_midfield_clash"] = (
        1 if 6 <= home_team.position <= 12 and 6 <= away_team.position <= 12 else 0
    )
    features["is_relegation_battle"] = (
        1
        if home_team.position >= total_teams - 4
        and away_team.position >= total_teams - 4
        else 0
    )

    try:
        match_dt = datetime.strptime(match_date, "%Y-%m-%d")
        features["month"] = match_dt.month
        features["is_second_half"] = 1 if match_dt.month >= 1 else 0
        features["is_final_month"] = 1 if match_dt.month == 5 else 0
    except:
        features["month"] = 0
        features["is_second_half"] = 0
        features["is_final_month"] = 0

    return features


def encode_position_features(features_dict: Dict) -> Dict:
    """
    Encodiert Position-Features für ML
    
    Args:
        features_dict: Dictionary mit rohen Features
        
    Returns:
        Dictionary mit encodierten Features
    """
    encoded = {}

    numeric_features = [
        "home_position",
        "away_position",
        "position_diff",
        "position_diff_abs",
        "home_pos_norm",
        "away_pos_norm",
        "home_ppg",
        "away_ppg",
        "ppg_diff",
        "ppg_diff_abs",
        "season_progress",
        "home_pressure",
        "away_pressure",
        "is_top_vs_bottom",
        "is_midfield_clash",
        "is_relegation_battle",
        "month",
        "is_second_half",
        "is_final_month",
    ]

    for feature in numeric_features:
        if feature in features_dict:
            encoded[feature] = features_dict[feature]

    zone_mapping = {
        "champions_league": [1, 0, 0, 0, 0],
        "europa_league": [0, 1, 0, 0, 0],
        "midfield": [0, 0, 1, 0, 0],
        "relegation_threat": [0, 0, 0, 1, 0],
        "direct_relegation": [0, 0, 0, 0, 1],
    }

    home_zone = features_dict.get("home_zone", "midfield")
    away_zone = features_dict.get("away_zone", "midfield")

    for i, val in enumerate(zone_mapping.get(home_zone, [0, 0, 0, 0, 0])):
        encoded[f"home_zone_{i}"] = val

    for i, val in enumerate(zone_mapping.get(away_zone, [0, 0, 0, 0, 0])):
        encoded[f"away_zone_{i}"] = val

    return encoded


def create_extended_features(extended_data: ExtendedMatchData, match_info: Dict) -> Dict:
    """
    Erstellt erweiterte Features aus Extended Match Data
    
    Args:
        extended_data: ExtendedMatchData Objekt
        match_info: Dictionary mit Match-Informationen (enthält actual_score)
        
    Returns:
        Dictionary mit Extended Features
    """
    features = {}

    try:
        ht_home, ht_away = map(int, extended_data.halftime_score.split(":"))

        features["halftime_home_goals"] = ht_home
        features["halftime_away_goals"] = ht_away
        features["halftime_total"] = ht_home + ht_away

        features["halftime_lead"] = ht_home - ht_away
        features["home_leading_at_ht"] = 1 if ht_home > ht_away else 0
        features["away_leading_at_ht"] = 1 if ht_away > ht_home else 0
        features["draw_at_halftime"] = 1 if ht_home == ht_away else 0

        if "actual_score" in match_info:
            try:
                ft_home, ft_away = map(int, match_info["actual_score"].split(":"))
                features["second_half_goals_home"] = ft_home - ht_home
                features["second_half_goals_away"] = ft_away - ht_away
                features["comeback_occurred"] = (
                    1
                    if (ht_home < ht_away and ft_home > ft_away)
                    or (ht_home > ht_away and ft_home < ft_away)
                    else 0
                )
            except:
                pass

    except:
        features["halftime_home_goals"] = 0
        features["halftime_away_goals"] = 0
        features["halftime_total"] = 0
        features["halftime_lead"] = 0
        features["home_leading_at_ht"] = 0
        features["away_leading_at_ht"] = 0
        features["draw_at_halftime"] = 0

    features["possession_home"] = extended_data.possession_home
    features["possession_away"] = extended_data.possession_away
    features["possession_dominance"] = (
        extended_data.possession_home - extended_data.possession_away
    )

    if extended_data.possession_home > 60:
        features["possession_category"] = 2
    elif extended_data.possession_home > 55:
        features["possession_category"] = 1
    elif extended_data.possession_home > 45:
        features["possession_category"] = 0
    elif extended_data.possession_home > 40:
        features["possession_category"] = -1
    else:
        features["possession_category"] = -2

    features["shots_total_home"] = extended_data.shots_home
    features["shots_total_away"] = extended_data.shots_away
    features["shots_total"] = extended_data.shots_home + extended_data.shots_away

    features["shots_on_target_home"] = extended_data.shots_on_target_home
    features["shots_on_target_away"] = extended_data.shots_on_target_away
    features["shots_on_target_total"] = (
        extended_data.shots_on_target_home + extended_data.shots_on_target_away
    )

    features["shot_accuracy_home"] = (
        (extended_data.shots_on_target_home / extended_data.shots_home)
        if extended_data.shots_home > 0
        else 0
    )
    features["shot_accuracy_away"] = (
        (extended_data.shots_on_target_away / extended_data.shots_away)
        if extended_data.shots_away > 0
        else 0
    )

    features["shot_dominance"] = extended_data.shots_home - extended_data.shots_away
    features["shot_on_target_dominance"] = (
        extended_data.shots_on_target_home - extended_data.shots_on_target_away
    )

    features["shots_per_minute_home"] = extended_data.shots_home / 90
    features["shots_per_minute_away"] = extended_data.shots_away / 90

    features["corners_home"] = extended_data.corners_home
    features["corners_away"] = extended_data.corners_away
    features["corners_total"] = extended_data.corners_home + extended_data.corners_away

    features["corner_dominance"] = (
        extended_data.corners_home - extended_data.corners_away
    )
    features["corners_per_minute"] = features["corners_total"] / 90

    if features["corners_total"] > 0:
        features["corner_ratio_home"] = (
            extended_data.corners_home / features["corners_total"]
        )
    else:
        features["corner_ratio_home"] = 0.5

    features["fouls_home"] = extended_data.fouls_home
    features["fouls_away"] = extended_data.fouls_away
    features["fouls_total"] = extended_data.fouls_home + extended_data.fouls_away

    features["fouls_per_minute"] = features["fouls_total"] / 90

    features["yellow_cards_total"] = (
        extended_data.yellow_cards_home + extended_data.yellow_cards_away
    )
    features["red_cards_total"] = (
        extended_data.red_cards_home + extended_data.red_cards_away
    )
    features["cards_total"] = (
        features["yellow_cards_total"] + features["red_cards_total"]
    )

    features["aggression_index_home"] = (
        extended_data.fouls_home
        + extended_data.yellow_cards_home * 2
        + extended_data.red_cards_home * 5
    ) / 90
    features["aggression_index_away"] = (
        extended_data.fouls_away
        + extended_data.yellow_cards_away * 2
        + extended_data.red_cards_away * 5
    ) / 90

    features["substitutions_home"] = extended_data.substitutions_home
    features["substitutions_away"] = extended_data.substitutions_away
    features["substitutions_total"] = (
        extended_data.substitutions_home + extended_data.substitutions_away
    )

    if features["shots_on_target_total"] > 0:
        features["expected_win_ratio_home"] = (
            extended_data.shots_on_target_home / features["shots_on_target_total"]
        )
    else:
        features["expected_win_ratio_home"] = 0.5

    features["control_score"] = (
        features["possession_dominance"] * 0.3
        + features["shot_dominance"] * 0.3
        + features["corner_dominance"] * 0.2
        + features["halftime_lead"] * 0.2
    ) / 10

    features["defensive_stability_home"] = (
        1 / (features["shots_on_target_away"] + 1) * 100
    )
    features["defensive_stability_away"] = (
        1 / (features["shots_on_target_home"] + 1) * 100
    )

    if extended_data.shots_home > 0:
        features["offensive_efficiency_home"] = (
            (
                features.get("halftime_home_goals", 0)
                + features.get("second_half_goals_home", 0)
            )
            / extended_data.shots_home
            * 100
        )
    else:
        features["offensive_efficiency_home"] = 0

    if extended_data.shots_away > 0:
        features["offensive_efficiency_away"] = (
            (
                features.get("halftime_away_goals", 0)
                + features.get("second_half_goals_away", 0)
            )
            / extended_data.shots_away
            * 100
        )
    else:
        features["offensive_efficiency_away"] = 0

    return features
