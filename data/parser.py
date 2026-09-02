"""
Parser für Google Sheets Match-Daten
"""

import re
from typing import Tuple, List, Dict
from data.models import TeamStats, H2HResult, MatchData


class DataParser:
    """Parser für Match-Daten aus Google Sheets"""
    
    def __init__(self):
        self.lines = []

    def parse(self, text: str) -> MatchData:
        """
        Parst Text-Daten zu MatchData Objekt
        
        Args:
            text: Tab-separierter Text aus Google Sheets
            
        Returns:
            MatchData Objekt
        """
        self.lines = [line.strip() for line in text.split("\n") if line.strip()]
        home_name, away_name = self._parse_match_details()
        date, competition, kickoff = self._parse_date_competition()
        home_overall = self._parse_team_overall(home_name)
        away_overall = self._parse_team_overall(away_name)
        home_form = self._parse_team_form(home_name)
        away_form = self._parse_team_form(away_name)
        home_ha = self._parse_team_ha(home_name, is_home=True)
        away_ha = self._parse_team_ha(away_name, is_home=False)
        h2h_results = self._parse_h2h(home_name, away_name)
        home_stats, away_stats = self._parse_statistics()
        odds_1x2, odds_ou25, odds_btts = self._parse_odds()
        home_team = self._create_team_stats(
            home_name, home_overall, home_form, home_ha, home_stats
        )
        away_team = self._create_team_stats(
            away_name, away_overall, away_form, away_ha, away_stats
        )
        return MatchData(
            home_team=home_team,
            away_team=away_team,
            h2h_results=h2h_results,
            date=date,
            competition=competition,
            kickoff=kickoff,
            odds_1x2=odds_1x2,
            odds_ou25=odds_ou25,
            odds_btts=odds_btts,
        )

    def _find_line_with(self, text: str, start_from: int = 0) -> int:
        """Findet Index der ersten Zeile die text enthält"""
        for i in range(start_from, len(self.lines)):
            if text.lower() in self.lines[i].lower():
                return i
        return -1

    def _parse_match_details(self) -> Tuple[str, str]:
        """Parst Heimteam und Auswärtsteam"""
        idx = self._find_line_with("heimteam")
        if idx == -1:
            raise ValueError("Heimteam nicht gefunden")
        idx += 1
        while idx < len(self.lines) and not self.lines[idx]:
            idx += 1
        teams_line = self.lines[idx]
        teams = [t.strip() for t in teams_line.split("\t") if t.strip()]
        if len(teams) >= 2:
            return teams[0], teams[1]
        teams = [t.strip() for t in re.split(r"\s{2,}", teams_line) if t.strip()]
        return teams[0], teams[1]

    def _parse_date_competition(self) -> Tuple[str, str, str]:
        """Parst Datum, Wettbewerb und Anstoßzeit"""
        date_idx = self._find_line_with("datum:")
        date = self.lines[date_idx].split(":", 1)[1].strip() if date_idx != -1 else ""
        comp_idx = self._find_line_with("wettbewerb:")
        competition = (
            self.lines[comp_idx].split(":", 1)[1].strip() if comp_idx != -1 else ""
        )
        kick_idx = self._find_line_with("anstoß:")
        kickoff = (
            self.lines[kick_idx].split(":", 1)[1].strip() if kick_idx != -1 else ""
        )
        return date, competition, kickoff

    def _parse_team_overall(self, team_name: str) -> Dict:
        """Parst Overall-Statistiken für ein Team"""
        for i, line in enumerate(self.lines):
            if (
                team_name in line
                and "tabellenposition" not in line.lower()
                and "letzte 5" not in line.lower()
            ):
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                if len(parts) >= 9:
                    goals = parts[6].split(":")
                    return {
                        "position": int(parts[1].replace(".", "")),
                        "games": int(parts[2]),
                        "wins": int(parts[3]),
                        "draws": int(parts[4]),
                        "losses": int(parts[5]),
                        "goals_for": int(goals[0]),
                        "goals_against": int(goals[1]),
                        "goal_diff": int(parts[7]),
                        "points": int(parts[8]),
                    }
        return {}

    def _parse_team_form(self, team_name: str) -> Dict:
        """Parst Form-Statistiken (Letzte 5 Spiele)"""
        idx = self._find_line_with(f"{team_name} letzte 5 spiele")
        if idx == -1:
            return {}
        line = self.lines[idx]
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) >= 8:
            goals = parts[6].split(":")
            return {
                "points": int(parts[-1]),
                "goals_for": int(goals[0]),
                "goals_against": int(goals[1]),
            }
        return {}

    def _parse_team_ha(self, team_name: str, is_home: bool) -> Dict:
        """Parst Heim/Auswärts-Statistiken"""
        search_term = "heimspiele" if is_home else "auswärtsspiele"
        idx = self._find_line_with(f"{team_name} letzte 5 {search_term}")
        if idx == -1:
            return {}
        line = self.lines[idx]
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        goals_for = 0
        goals_against = 0
        points = 0
        for part in parts:
            if ":" in part and re.match(r"\d+:\d+", part):
                goals = part.split(":")
                goals_for = int(goals[0])
                goals_against = int(goals[1])
            elif part.isdigit() and int(part) <= 15:
                points = int(part)
        return {
            "points": points,
            "goals_for": goals_for,
            "goals_against": goals_against,
        }

    def _parse_h2h(self, home_name: str, away_name: str) -> List[H2HResult]:
        """Parst Head-to-Head Ergebnisse"""
        results = []
        idx = self._find_line_with("ergebnisse")
        if idx == -1:
            return results
        idx += 1
        while idx < len(self.lines):
            line = self.lines[idx]
            if any(
                marker in line.lower()
                for marker in ["statistische", "wettquoten", "1x2", "points per game"]
            ):
                break
            if re.search(r"\d+:\d+", line):
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                if len(parts) >= 2:
                    date = parts[0]
                    match_str = parts[1]
                    match = re.search(r"(.+?)\s+(\d+):(\d+)\s+(.+)", match_str)
                    if match:
                        team1 = match.group(1).strip()
                        goals1 = int(match.group(2))
                        goals2 = int(match.group(3))
                        team2 = match.group(4).strip()
                        results.append(
                            H2HResult(
                                date=date,
                                home_team=team1,
                                away_team=team2,
                                home_goals=goals1,
                                away_goals=goals2,
                            )
                        )
            idx += 1
        return results

    def _parse_statistics(self) -> Tuple[Dict, Dict]:
        """Parst erweiterte Statistiken für beide Teams"""
        home_stats = {}
        away_stats = {}
        idx = self._find_line_with("points per game overall")
        if idx == -1:
            return home_stats, away_stats
        stat_lines = []
        i = idx
        while i < len(self.lines):
            line = self.lines[i]
            if "wettquoten" in line.lower() or "1x2" in line.lower():
                break
            if line and not line.startswith("*"):
                stat_lines.append(line)
            i += 1
        for line in stat_lines:
            parts = [p.strip() for p in line.split("\t") if p.strip()]
            if len(parts) >= 3:
                stat_name = parts[0].lower()
                try:
                    if "points per game overall" in stat_name:
                        home_stats["ppg_overall"] = float(parts[1])
                        away_stats["ppg_overall"] = float(parts[2])
                    elif "points per game home/away" in stat_name:
                        home_stats["ppg_ha"] = float(parts[1])
                        away_stats["ppg_ha"] = float(parts[2])
                    elif "average goals scored/conceded per match overall" in stat_name:
                        if len(parts) >= 5:
                            home_stats["goals_scored_per_match"] = float(parts[1])
                            home_stats["goals_conceded_per_match"] = float(parts[2])
                            away_stats["goals_scored_per_match"] = float(parts[3])
                            away_stats["goals_conceded_per_match"] = float(parts[4])
                    elif (
                        "average goals scored/conceded per match home/away" in stat_name
                    ):
                        if len(parts) >= 5:
                            home_stats["goals_scored_per_match_ha"] = float(parts[1])
                            home_stats["goals_conceded_per_match_ha"] = float(parts[2])
                            away_stats["goals_scored_per_match_ha"] = float(parts[3])
                            away_stats["goals_conceded_per_match_ha"] = float(parts[4])
                    elif "xg overall" in stat_name.lower():
                        if len(parts) >= 5:
                            home_stats["xg_for"] = float(parts[1])
                            home_stats["xg_against"] = float(parts[2])
                            away_stats["xg_for"] = float(parts[3])
                            away_stats["xg_against"] = float(parts[4])
                    elif "xg home/away" in stat_name.lower():
                        if len(parts) >= 5:
                            home_stats["xg_for_ha"] = float(parts[1])
                            home_stats["xg_against_ha"] = float(parts[2])
                            away_stats["xg_for_ha"] = float(parts[3])
                            away_stats["xg_against_ha"] = float(parts[4])
                    elif "clean sheet yes/no overall" in stat_name:
                        if len(parts) >= 5:
                            home_stats["cs_yes_overall"] = (
                                float(parts[1].replace("%", "")) / 100
                            )
                            away_stats["cs_yes_overall"] = (
                                float(parts[3].replace("%", "")) / 100
                            )
                    elif "clean sheet yes/no home/away" in stat_name:
                        if len(parts) >= 5:
                            home_stats["cs_yes_ha"] = (
                                float(parts[1].replace("%", "")) / 100
                            )
                            away_stats["cs_yes_ha"] = (
                                float(parts[3].replace("%", "")) / 100
                            )
                    elif "failed to score yes/no home/away" in stat_name:
                        if len(parts) >= 5:
                            home_stats["fts_yes_ha"] = (
                                float(parts[1].replace("%", "")) / 100
                            )
                            away_stats["fts_yes_ha"] = (
                                float(parts[3].replace("%", "")) / 100
                            )
                    elif "conversion rate" in stat_name.lower():
                        home_stats["conversion_rate"] = (
                            float(parts[1].replace("%", "")) / 100
                        )
                        away_stats["conversion_rate"] = (
                            float(parts[2].replace("%", "")) / 100
                        )
                except (ValueError, IndexError):
                    continue
        return home_stats, away_stats

    def _parse_odds(
        self,
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float], Tuple[float, float]]:
        """Parst Wettquoten"""
        odds_1x2 = (1.0, 1.0, 1.0)
        odds_ou25 = (1.0, 1.0)
        odds_btts = (1.0, 1.0)
        for line in self.lines:
            line_lower = line.lower()
            if "1x2" in line_lower:
                match = re.search(r"([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+)", line)
                if match:
                    odds_1x2 = (
                        float(match.group(1)),
                        float(match.group(2)),
                        float(match.group(3)),
                    )
            elif "over/under 2" in line_lower:
                match = re.search(r"([\d.]+)\s*/\s*([\d.]+)", line)
                if match:
                    odds_ou25 = (float(match.group(1)), float(match.group(2)))
            elif "btts" in line_lower and "ja/nein" in line_lower:
                match = re.search(r"([\d.]+)\s*/\s*([\d.]+)", line)
                if match:
                    odds_btts = (float(match.group(1)), float(match.group(2)))
        return odds_1x2, odds_ou25, odds_btts

    def _create_team_stats(
        self, name: str, overall: Dict, form: Dict, ha: Dict, stats: Dict
    ) -> TeamStats:
        """Erstellt TeamStats Objekt aus geparsten Daten"""
        return TeamStats(
            name=name,
            position=overall.get("position", 0),
            games=overall.get("games", 0),
            wins=overall.get("wins", 0),
            draws=overall.get("draws", 0),
            losses=overall.get("losses", 0),
            goals_for=overall.get("goals_for", 0),
            goals_against=overall.get("goals_against", 0),
            goal_diff=overall.get("goal_diff", 0),
            points=overall.get("points", 0),
            form_points=form.get("points", 0),
            form_goals_for=form.get("goals_for", 0),
            form_goals_against=form.get("goals_against", 0),
            ha_points=ha.get("points", 0),
            ha_goals_for=ha.get("goals_for", 0),
            ha_goals_against=ha.get("goals_against", 0),
            ppg_overall=stats.get("ppg_overall", 0.0),
            ppg_ha=stats.get("ppg_ha", 0.0),
            avg_goals_match=stats.get("avg_goals_match", 0.0),
            avg_goals_match_ha=stats.get("avg_goals_match_ha", 0.0),
            goals_scored_per_match=stats.get("goals_scored_per_match", 0.0),
            goals_conceded_per_match=stats.get("goals_conceded_per_match", 0.0),
            goals_scored_per_match_ha=stats.get("goals_scored_per_match_ha", 0.0),
            goals_conceded_per_match_ha=stats.get("goals_conceded_per_match_ha", 0.0),
            btts_yes_overall=stats.get("btts_yes_overall", 0.0),
            btts_yes_ha=stats.get("btts_yes_ha", 0.0),
            cs_yes_overall=stats.get("cs_yes_overall", 0.0),
            cs_yes_ha=stats.get("cs_yes_ha", 0.0),
            fts_yes_overall=stats.get("fts_yes_overall", 0.0),
            fts_yes_ha=stats.get("fts_yes_ha", 0.0),
            xg_for=stats.get("xg_for", 0.0),
            xg_against=stats.get("xg_against", 0.0),
            xg_for_ha=stats.get("xg_for_ha", 0.0),
            xg_against_ha=stats.get("xg_against_ha", 0.0),
            shots_per_match=stats.get("shots_per_match", 0.0),
            shots_on_target=stats.get("shots_on_target", 0.0),
            conversion_rate=stats.get("conversion_rate", 0.0),
            possession=stats.get("possession", 0.0),
        )
