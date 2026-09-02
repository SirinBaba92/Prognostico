"""
Validierungsfunktionen für Match-Daten
"""

from typing import Tuple, List, Dict
from data.models import MatchData, TeamStats


def validate_match_data(match: MatchData) -> Tuple[bool, List[str]]:
    """
    Validiert Match-Daten auf Vollständigkeit
    
    Args:
        match: MatchData Objekt zum Validieren
        
    Returns:
        Tuple (ist_valid, liste_fehlender_felder)
    """
    missing_fields = []

    def check_team_data(team: TeamStats, team_name: str):
        team_missing = []

        if not team.name or team.name.strip() == "":
            team_missing.append(f"{team_name}: Team-Name")
        if team.position is None or team.position <= 0:
            team_missing.append(f"{team_name}: Tabellenposition")
        if team.games is None or team.games <= 0:
            team_missing.append(f"{team_name}: Anzahl Spiele")
        if team.wins is None:
            team_missing.append(f"{team_name}: Siege")
        if team.draws is None:
            team_missing.append(f"{team_name}: Unentschieden")
        if team.losses is None:
            team_missing.append(f"{team_name}: Niederlagen")
        if team.goals_for is None:
            team_missing.append(f"{team_name}: Tore geschossen")
        if team.goals_against is None:
            team_missing.append(f"{team_name}: Tore kassiert")
        if team.goal_diff is None:
            team_missing.append(f"{team_name}: Tordifferenz")
        if team.points is None:
            team_missing.append(f"{team_name}: Punkte")
        if team.form_points is None:
            team_missing.append(f"{team_name}: Form-Punkte (L5)")
        if team.form_goals_for is None:
            team_missing.append(f"{team_name}: Form-Tore geschossen (L5)")
        if team.form_goals_against is None:
            team_missing.append(f"{team_name}: Form-Tore kassiert (L5)")
        if team.ha_points is None:
            team_missing.append(f"{team_name}: Heim/Auswärts-Punkte")
        if team.ha_goals_for is None:
            team_missing.append(f"{team_name}: H/A Tore geschossen")
        if team.ha_goals_against is None:
            team_missing.append(f"{team_name}: H/A Tore kassiert")
        if team.ppg_overall is None or team.ppg_overall < 0:
            team_missing.append(f"{team_name}: PPG Overall")
        if team.ppg_ha is None or team.ppg_ha < 0:
            team_missing.append(f"{team_name}: PPG Heim/Auswärts")
        if team.avg_goals_match is None or team.avg_goals_match < 0:
            team_missing.append(f"{team_name}: Ø Tore pro Spiel")
        if team.avg_goals_match_ha is None or team.avg_goals_match_ha < 0:
            team_missing.append(f"{team_name}: Ø Tore H/A")
        if team.goals_scored_per_match is None or team.goals_scored_per_match < 0:
            team_missing.append(f"{team_name}: Tore geschossen/Spiel")
        if team.goals_conceded_per_match is None or team.goals_conceded_per_match < 0:
            team_missing.append(f"{team_name}: Tore kassiert/Spiel")
        if team.goals_scored_per_match_ha is None or team.goals_scored_per_match_ha < 0:
            team_missing.append(f"{team_name}: Tore geschossen/Spiel H/A")
        if (
            team.goals_conceded_per_match_ha is None
            or team.goals_conceded_per_match_ha < 0
        ):
            team_missing.append(f"{team_name}: Tore kassiert/Spiel")
        if team.btts_yes_overall is None or team.btts_yes_overall < 0:
            team_missing.append(f"{team_name}: BTTS% Overall")
        if team.btts_yes_ha is None or team.btts_yes_ha < 0:
            team_missing.append(f"{team_name}: BTTS% H/A")
        if team.cs_yes_overall is None or team.cs_yes_overall < 0:
            team_missing.append(f"{team_name}: Clean Sheet% Overall")
        if team.cs_yes_ha is None or team.cs_yes_ha < 0:
            team_missing.append(f"{team_name}: Clean Sheet% H/A")
        if team.fts_yes_overall is None or team.fts_yes_overall < 0:
            team_missing.append(f"{team_name}: FTS% Overall")
        if team.fts_yes_ha is None or team.fts_yes_ha < 0:
            team_missing.append(f"{team_name}: FTS% H/A")
        if team.xg_for is None or team.xg_for < 0:
            team_missing.append(f"{team_name}: xG For")
        if team.xg_against is None or team.xg_against < 0:
            team_missing.append(f"{team_name}: xG Against")
        if team.xg_for_ha is None or team.xg_for_ha < 0:
            team_missing.append(f"{team_name}: xG For H/A")
        if team.xg_against_ha is None or team.xg_against_ha < 0:
            team_missing.append(f"{team_name}: xG Against H/A")
        if team.shots_per_match is None or team.shots_per_match < 0:
            team_missing.append(f"{team_name}: Schüsse/Spiel")
        if team.shots_on_target is None or team.shots_on_target < 0:
            team_missing.append(f"{team_name}: Schüsse aufs Tor")
        if team.conversion_rate is None or team.conversion_rate < 0:
            team_missing.append(f"{team_name}: Conversion Rate")
        if team.possession is None or team.possession < 0:
            team_missing.append(f"{team_name}: Ballbesitz%")

        return team_missing

    missing_fields.extend(check_team_data(match.home_team, "HEIM"))
    missing_fields.extend(check_team_data(match.away_team, "AUSWÄRTS"))

    if not match.date or match.date.strip() == "":
        missing_fields.append("Match-Datum")
    if not match.competition or match.competition.strip() == "":
        missing_fields.append("Wettbewerb/Liga")
    if not match.kickoff or match.kickoff.strip() == "":
        missing_fields.append("Anstoßzeit")

    if not match.odds_1x2 or len(match.odds_1x2) != 3:
        missing_fields.append("1X2 Quoten (vollständig)")
    else:
        if match.odds_1x2[0] is None or match.odds_1x2[0] <= 1.0:
            missing_fields.append("1X2 Quote: Heim")
        if match.odds_1x2[1] is None or match.odds_1x2[1] <= 1.0:
            missing_fields.append("1X2 Quote: Unentschieden")
        if match.odds_1x2[2] is None or match.odds_1x2[2] <= 1.0:
            missing_fields.append("1X2 Quote: Auswärts")

    if not match.odds_ou25 or len(match.odds_ou25) != 2:
        missing_fields.append("Over/Under 2.5 Quoten")
    else:
        if match.odds_ou25[0] is None or match.odds_ou25[0] <= 1.0:
            missing_fields.append("Over 2.5 Quote")
        if match.odds_ou25[1] is None or match.odds_ou25[1] <= 1.0:
            missing_fields.append("Under 2.5 Quote")

    if not match.odds_btts or len(match.odds_btts) != 2:
        missing_fields.append("BTTS Quoten")
    else:
        if match.odds_btts[0] is None or match.odds_btts[0] <= 1.0:
            missing_fields.append("BTTS Ja Quote")
        if match.odds_btts[1] is None or match.odds_btts[1] <= 1.0:
            missing_fields.append("BTTS Nein Quote")

    if match.h2h_results is None:
        missing_fields.append("H2H-Daten (Liste)")

    is_valid = len(missing_fields) == 0
    return is_valid, missing_fields


def check_alerts(
    mu_h: float,
    mu_a: float,
    tki_h: float,
    tki_a: float,
    ppg_diff: float,
    thresholds: Dict,
) -> List[Dict]:
    """
    Prüft auf kritische Situationen und gibt Alarme zurück
    
    Args:
        mu_h: Erwartete Tore Heim
        mu_a: Erwartete Tore Auswärts
        tki_h: TKI Heim
        tki_a: TKI Auswärts
        ppg_diff: PPG-Differenz
        thresholds: Schwellenwerte für Alarme
        
    Returns:
        Liste von Alert-Dictionaries
    """
    alerts = []

    mu_total = mu_h + mu_a
    if mu_total > thresholds.get("mu_total_high", 4.5):
        alerts.append(
            {
                "level": "🔴",
                "title": "EXTREM TORREICHES SPIEL",
                "message": f"μ-Total: {mu_total:.1f} (> {thresholds['mu_total_high']}) - Sehr unvorhersehbar!",
                "type": "warning",
            }
        )
    elif mu_total > 4.0:
        alerts.append(
            {
                "level": "🟠",
                "title": "Sehr torreiches Spiel",
                "message": f"μ-Total: {mu_total:.1f} - Erhöhte Unvorhersehbarkeit",
                "type": "info",
            }
        )

    tki_combined = tki_h + tki_a
    if tki_combined > thresholds.get("tki_high", 1.0):
        alerts.append(
            {
                "level": "🔴",
                "title": "EXTREME TORWART-KRISE",
                "message": f"TKI kombiniert: {tki_combined:.2f} (> {thresholds['tki_high']}) - Defensiven instabil!",
                "type": "warning",
            }
        )
    elif tki_combined > 0.8:
        alerts.append(
            {
                "level": "🟠",
                "title": "Torwart-Probleme",
                "message": f"TKI kombiniert: {tki_combined:.2f} - Defensiven geschwächt",
                "type": "info",
            }
        )

    ppg_diff_abs = abs(ppg_diff)
    if ppg_diff_abs > thresholds.get("ppg_diff_extreme", 1.5):
        alerts.append(
            {
                "level": "🟢",
                "title": "EXTREM KLARER FAVORIT",
                "message": f"PPG-Differenz: {ppg_diff_abs:.2f} - Sehr einseitiges Spiel erwartet",
                "type": "success",
            }
        )

    return alerts
