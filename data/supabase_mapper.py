"""
Mapper: rohes Supabase-Bundle (aus data/supabase_client.get_full_match_bundle)
-> data/models.py Dataclasses (MatchData, TeamStats, H2HResult)

Ersetzt data/parser.py (DataParser), das bisher rohen Sheet-Text via
Zeilen-Pattern-Matching geparst hat. Kein Text-Parsing mehr nötig — die DB
liefert bereits strukturierte, typisierte Werte.
"""

from typing import Dict, List, Optional, Tuple

from data.models import TeamStats, H2HResult, MatchData


def _to_ddmmyyyy(iso_date_str: str) -> str:
    """
    Konvertiert Supabase-Datumsformat (YYYY-MM-DD) zum app-weiten Format (DD.MM.YYYY).
    Die restliche App (Anzeige, models/export_to_sheets.py Tab-Namen-Lookup) erwartet
    durchgängig DD.MM.YYYY — das war bisher implizit durch die Sheet-Tab-Namen gegeben.
    """
    if not iso_date_str:
        return ""
    try:
        y, m, d = iso_date_str.split("-")
        return f"{d}.{m}.{y}"
    except ValueError:
        return iso_date_str  # Fallback: unverändert durchreichen statt zu crashen


# footystats_match_stats.metric (mit scope) -> TeamStats-Feld
# Reihenfolge: (Feld für scope='overall', Feld für scope=ha_scope [home/away])
_FOOTYSTATS_SCOPED_METRICS = {
    "ppg": ("ppg_overall", "ppg_ha"),
    "avg": ("avg_goals_match", "avg_goals_match_ha"),
    "scored": ("goals_scored_per_match", "goals_scored_per_match_ha"),
    "conceded": ("goals_conceded_per_match", "goals_conceded_per_match_ha"),
    "btts": ("btts_yes_overall", "btts_yes_ha"),
    "cs": ("cs_yes_overall", "cs_yes_ha"),
    "fts": ("fts_yes_overall", "fts_yes_ha"),
    "xg": ("xg_for", "xg_for_ha"),
    "xga": ("xg_against", "xg_against_ha"),
}

# footystats_match_stats.metric OHNE scope (scope ist NULL in der DB) -> TeamStats-Feld
_FOOTYSTATS_UNSCOPED_METRICS = {
    "shots_per_match": "shots_per_match",
    "shots_on_target_per_match": "shots_on_target",
    "shots_off_target_per_match": "shots_off_target",
    "shots_conversion_rate": "conversion_rate",
    "avg_possession": "possession",
}


# Metriken, die der Scraper als rohe Prozentzahl (0-100) in
# footystats_match_stats.value schreibt, waehrend der Rest des Tools (alter
# data/parser.py, analysis/match_analysis.py) durchgaengig 0-1-Brueche erwartet
# -- siehe docs/projekt.md, Abschnitt "Skalierungs-Bug FootyStats-Metriken".
# Bestaetigt per direkter DB-Abfrage: avg_possession Ø 50.7, shots_conversion_rate
# Ø 15.4, btts Ø 64.6 -- alles klar 0-100, nicht 0-1.
_PERCENTAGE_METRICS_NEEDING_NORMALIZATION = {"btts", "cs", "fts", "shots_conversion_rate", "avg_possession"}


def _apply_footystats(
    team_fields: Dict, footystats_rows: List[Dict], team_id: str, is_home: bool
) -> None:
    ha_scope = "home" if is_home else "away"
    for row in footystats_rows:
        if row.get("team_id") != team_id:
            continue
        metric = row.get("metric")
        scope = row.get("scope")
        value = row.get("value")

        if value is not None and metric in _PERCENTAGE_METRICS_NEEDING_NORMALIZATION:
            value = value / 100

        if metric in _FOOTYSTATS_SCOPED_METRICS:
            overall_field, ha_field = _FOOTYSTATS_SCOPED_METRICS[metric]
            if scope == "overall":
                team_fields[overall_field] = value
            elif scope == ha_scope:
                team_fields[ha_field] = value
        elif metric in _FOOTYSTATS_UNSCOPED_METRICS:
            team_fields[_FOOTYSTATS_UNSCOPED_METRICS[metric]] = value


def _over_pct(row: Dict) -> Optional[float]:
    """Berechnet Over-2.5-Anteil aus over_count/under_count (table_stats, section=over_under)."""
    over_count = row.get("over_count")
    under_count = row.get("under_count")
    if over_count is None or under_count is None:
        return None
    total = over_count + under_count
    if total == 0:
        return None
    return over_count / total


def _apply_table_stats(
    team_fields: Dict, table_stats_rows: List[Dict], team_id: str, is_home: bool
) -> None:
    ha_scope = "home" if is_home else "away"
    for row in table_stats_rows:
        if row.get("team_id") != team_id:
            continue
        section = row.get("section")
        scope = row.get("scope")

        if section == "standings" and scope == "overall":
            team_fields["position"] = row.get("rank")
            team_fields["games"] = row.get("played")
            team_fields["wins"] = row.get("wins")
            team_fields["draws"] = row.get("draws")
            team_fields["losses"] = row.get("losses")
            team_fields["goals_for"] = row.get("goals_for")
            team_fields["goals_against"] = row.get("goals_against")
            team_fields["goal_diff"] = row.get("goal_diff")
            team_fields["points"] = row.get("points")
        elif section == "form" and scope == "overall":
            team_fields["form_points"] = row.get("points")
            team_fields["form_goals_for"] = row.get("goals_for")
            team_fields["form_goals_against"] = row.get("goals_against")
        elif section == "form" and scope == ha_scope:
            team_fields["ha_points"] = row.get("points")
            team_fields["ha_goals_for"] = row.get("goals_for")
            team_fields["ha_goals_against"] = row.get("goals_against")
        elif section == "over_under" and scope == "overall":
            pct = _over_pct(row)
            if pct is not None:
                team_fields["over25_pct_overall"] = pct
        elif section == "over_under" and scope == ha_scope:
            pct = _over_pct(row)
            if pct is not None:
                team_fields["over25_pct_ha"] = pct


def _build_team_stats(
    name: str,
    team_id: str,
    table_stats_rows: List[Dict],
    footystats_rows: List[Dict],
    is_home: bool,
) -> TeamStats:
    fields: Dict = {"name": name}
    _apply_table_stats(fields, table_stats_rows, team_id, is_home)
    _apply_footystats(fields, footystats_rows, team_id, is_home)

    # Defaults für alle TeamStats-Felder, falls DB-seitig mal etwas fehlt
    # (sollte laut Validierungs-Policy [Variante A] nicht vorkommen, ist aber
    # ein sinnvoller Fallback statt eines harten KeyError).
    defaults = {f: (0.0 if f != "name" else "") for f in TeamStats.__dataclass_fields__}
    merged = {**defaults, **fields}
    return TeamStats(**{k: v for k, v in merged.items() if k in TeamStats.__dataclass_fields__})


def _map_h2h(h2h_rows: List[Dict], h2h_teams_by_id: Dict) -> List[H2HResult]:
    results = []
    for row in h2h_rows:
        results.append(
            H2HResult(
                date=row.get("h2h_date", ""),
                home_team=h2h_teams_by_id.get(row.get("home_team_id"), "?"),
                away_team=h2h_teams_by_id.get(row.get("away_team_id"), "?"),
                home_goals=row.get("home_goals", 0),
                away_goals=row.get("away_goals", 0),
            )
        )
    return results


def _first_row(rows: List[Dict]) -> Dict:
    return rows[0] if rows else {}


def map_bundle_to_match_data(bundle: Dict) -> MatchData:
    """Wandelt das Rohdaten-Bundle aus get_full_match_bundle() in ein MatchData-Objekt um."""
    match_row = bundle["match"]
    home_team_row = bundle["home_team"]
    away_team_row = bundle["away_team"]
    competition = bundle["competition"]

    home_id = home_team_row.get("id")
    away_id = away_team_row.get("id")

    home_team = _build_team_stats(
        home_team_row.get("name", ""),
        home_id,
        bundle["table_stats"],
        bundle["footystats"],
        is_home=True,
    )
    away_team = _build_team_stats(
        away_team_row.get("name", ""),
        away_id,
        bundle["table_stats"],
        bundle["footystats"],
        is_home=False,
    )

    h2h_results = _map_h2h(bundle["h2h_entries"], bundle["h2h_teams_by_id"])

    odds_1x2_row = _first_row(bundle["odds_1x2"])
    odds_ou_row = _first_row(bundle["odds_over_under"])
    odds_btts_row = _first_row(bundle["odds_btts"])

    competition_label = (
        f"{competition.get('country', '')} - {competition.get('name', '')}".strip(" -")
    )

    return MatchData(
        home_team=home_team,
        away_team=away_team,
        h2h_results=h2h_results,
        date=_to_ddmmyyyy(match_row.get("match_date", "")),
        competition=competition_label,
        kickoff=(match_row.get("kickoff_time") or "")[:5],
        odds_1x2=(
            odds_1x2_row.get("home", 1.0),
            odds_1x2_row.get("draw", 1.0),
            odds_1x2_row.get("away", 1.0),
        ),
        odds_ou25=(odds_ou_row.get("over", 1.0), odds_ou_row.get("under", 1.0)),
        odds_btts=(odds_btts_row.get("yes", 1.0), odds_btts_row.get("no", 1.0)),
    )
