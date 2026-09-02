"""
Datenmodelle für Match-Analysen
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TeamStats:
    """Statistiken für ein Team"""

    name: str
    position: int
    games: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    form_points: int
    form_goals_for: int
    form_goals_against: int
    ha_points: int
    ha_goals_for: int
    ha_goals_against: int
    ppg_overall: float
    ppg_ha: float
    avg_goals_match: float
    avg_goals_match_ha: float
    goals_scored_per_match: float
    goals_conceded_per_match: float
    goals_scored_per_match_ha: float
    goals_conceded_per_match_ha: float
    btts_yes_overall: float
    btts_yes_ha: float
    cs_yes_overall: float
    cs_yes_ha: float
    fts_yes_overall: float
    fts_yes_ha: float
    xg_for: float
    xg_against: float
    xg_for_ha: float
    xg_against_ha: float
    shots_per_match: float
    shots_on_target: float
    conversion_rate: float
    shots_off_target: float
    over25_pct_overall: float
    over25_pct_ha: float
    possession: float


@dataclass
class H2HResult:
    """Head-to-Head Ergebnis"""

    date: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int


@dataclass
class MatchData:
    """Vollständige Match-Daten für Analyse"""

    home_team: TeamStats
    away_team: TeamStats
    h2h_results: List[H2HResult]
    date: str
    competition: str
    kickoff: str
    odds_1x2: Tuple[float, float, float]
    odds_ou25: Tuple[float, float]
    odds_btts: Tuple[float, float]


@dataclass
class ExtendedMatchData:
    """Erweiterte Match-Daten für ML-Training (Phase 4)"""

    match_id: str
    halftime_score: str
    possession_home: float
    possession_away: float
    shots_home: int
    shots_away: int
    shots_on_target_home: int
    shots_on_target_away: int
    corners_home: int
    corners_away: int
    fouls_home: int
    fouls_away: int
    yellow_cards_home: int
    yellow_cards_away: int
    red_cards_home: int
    red_cards_away: int
    substitutions_home: int
    substitutions_away: int
    notes: str

    def to_dict(self):
        """Konvertiert ExtendedMatchData zu Dictionary"""
        return {
            "match_id": self.match_id,
            "halftime": self.halftime_score,
            "possession_home": self.possession_home,
            "possession_away": self.possession_away,
            "shots_home": self.shots_home,
            "shots_away": self.shots_away,
            "shots_on_target_home": self.shots_on_target_home,
            "shots_on_target_away": self.shots_on_target_away,
            "corners_home": self.corners_home,
            "corners_away": self.corners_away,
            "fouls_home": self.fouls_home,
            "fouls_away": self.fouls_away,
            "yellow_home": self.yellow_cards_home,
            "yellow_away": self.yellow_cards_away,
            "red_home": self.red_cards_home,
            "red_away": self.red_cards_away,
            "subs_home": self.substitutions_home,
            "subs_away": self.substitutions_away,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data):
        """Erstellt ExtendedMatchData aus Dictionary"""
        return cls(
            match_id=data.get("match_id", ""),
            halftime_score=data.get("halftime", "0:0"),
            possession_home=float(data.get("possession_home", 50.0)),
            possession_away=float(data.get("possession_away", 50.0)),
            shots_home=int(data.get("shots_home", 0)),
            shots_away=int(data.get("shots_away", 0)),
            shots_on_target_home=int(data.get("shots_on_target_home", 0)),
            shots_on_target_away=int(data.get("shots_on_target_away", 0)),
            corners_home=int(data.get("corners_home", 0)),
            corners_away=int(data.get("corners_away", 0)),
            fouls_home=int(data.get("fouls_home", 0)),
            fouls_away=int(data.get("fouls_away", 0)),
            yellow_cards_home=int(data.get("yellow_home", 0)),
            yellow_cards_away=int(data.get("yellow_away", 0)),
            red_cards_home=int(data.get("red_home", 0)),
            red_cards_away=int(data.get("red_away", 0)),
            substitutions_home=int(data.get("subs_home", 0)),
            substitutions_away=int(data.get("subs_away", 0)),
            notes=data.get("notes", ""),
        )
