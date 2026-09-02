"""
Scoreline Prediction mit Poisson Distribution
Erstellt konsistente Predictions über alle Märkte
"""

import numpy as np
from typing import Dict, List, Tuple
from scipy.stats import poisson


class ScorelinePredictor:
    """
    Erstellt Scoreline-Predictions basierend auf Expected Goals (Poisson)
    """
    
    def __init__(self):
        self.max_goals = 6  # Maximum Goals pro Team zu berechnen
        
    def predict_scorelines(
        self, 
        home_xg: float, 
        away_xg: float,
        top_n: int = 10
    ) -> List[Dict]:
        """
        Berechnet wahrscheinlichste Scorelines
        
        Args:
            home_xg: Expected Goals Heimteam
            away_xg: Expected Goals Auswärtsteam
            top_n: Anzahl Top-Scorelines zurückgeben
            
        Returns:
            Liste von Scoreline-Dictionaries
        """
        scorelines = []
        
        # Berechne alle Kombinationen
        for home_goals in range(self.max_goals + 1):
            for away_goals in range(self.max_goals + 1):
                # Poisson Wahrscheinlichkeit
                prob_home = poisson.pmf(home_goals, home_xg)
                prob_away = poisson.pmf(away_goals, away_xg)
                prob_combined = prob_home * prob_away
                
                # Bestimme Märkte
                result = self._determine_result(home_goals, away_goals)
                over_under = self._determine_over_under(home_goals, away_goals)
                btts = self._determine_btts(home_goals, away_goals)
                
                scorelines.append({
                    'home_goals': home_goals,
                    'away_goals': away_goals,
                    'scoreline': f"{home_goals}-{away_goals}",
                    'probability': prob_combined * 100,
                    'result': result,
                    'over_under': over_under,
                    'btts': btts
                })
        
        # Sortiere nach Wahrscheinlichkeit
        scorelines.sort(key=lambda x: x['probability'], reverse=True)
        
        return scorelines[:top_n]
    
    def derive_market_probabilities(self, scorelines: List[Dict]) -> Dict:
        """
        Leitet Markt-Wahrscheinlichkeiten aus Scorelines ab
        
        Args:
            scorelines: Liste aller Scorelines mit Wahrscheinlichkeiten
            
        Returns:
            Dictionary mit Markt-Wahrscheinlichkeiten
        """
        # Initialisiere Counters
        prob_home = 0
        prob_draw = 0
        prob_away = 0
        prob_over = 0
        prob_under = 0
        prob_btts_yes = 0
        prob_btts_no = 0
        
        # Summiere Wahrscheinlichkeiten
        for scoreline in scorelines:
            prob = scoreline['probability'] / 100  # Convert to decimal
            
            # 1X2
            if scoreline['result'] == 'HOME':
                prob_home += prob
            elif scoreline['result'] == 'DRAW':
                prob_draw += prob
            else:
                prob_away += prob
            
            # Over/Under
            if scoreline['over_under'] == 'OVER':
                prob_over += prob
            else:
                prob_under += prob
            
            # BTTS
            if scoreline['btts'] == 'YES':
                prob_btts_yes += prob
            else:
                prob_btts_no += prob
        
        return {
            '1x2': {
                'home': prob_home * 100,
                'draw': prob_draw * 100,
                'away': prob_away * 100
            },
            'over_under': {
                'over': prob_over * 100,
                'under': prob_under * 100
            },
            'btts': {
                'yes': prob_btts_yes * 100,
                'no': prob_btts_no * 100
            }
        }
    
    def _determine_result(self, home_goals: int, away_goals: int) -> str:
        """Bestimmt 1X2 Ergebnis"""
        if home_goals > away_goals:
            return 'HOME'
        elif home_goals < away_goals:
            return 'AWAY'
        else:
            return 'DRAW'
    
    def _determine_over_under(self, home_goals: int, away_goals: int) -> str:
        """Bestimmt Over/Under 2.5"""
        total = home_goals + away_goals
        return 'OVER' if total > 2.5 else 'UNDER'
    
    def _determine_btts(self, home_goals: int, away_goals: int) -> str:
        """Bestimmt BTTS"""
        return 'YES' if home_goals > 0 and away_goals > 0 else 'NO'
    
    def check_consistency(
        self, 
        prediction_1x2: str,
        prediction_ou: str, 
        prediction_btts: str
    ) -> Dict:
        """
        Prüft ob die 3 Market-Predictions konsistent sind
        
        Args:
            prediction_1x2: 'HOME', 'DRAW', 'AWAY'
            prediction_ou: 'OVER', 'UNDER'
            prediction_btts: 'YES', 'NO'
            
        Returns:
            Dict mit Konsistenz-Info und möglichen Scorelines
        """
        consistent_scorelines = []
        
        # Generiere alle möglichen Scorelines bis 5-5
        for home in range(6):
            for away in range(6):
                result = self._determine_result(home, away)
                ou = self._determine_over_under(home, away)
                btts = self._determine_btts(home, away)
                
                # Check ob konsistent
                if (result == prediction_1x2 and 
                    ou == prediction_ou and 
                    btts == prediction_btts):
                    consistent_scorelines.append(f"{home}-{away}")
        
        is_consistent = len(consistent_scorelines) > 0
        
        return {
            'is_consistent': is_consistent,
            'possible_scorelines': consistent_scorelines,
            'count': len(consistent_scorelines)
        }
    
    def estimate_xg_from_features(self, features: Dict) -> Tuple[float, float]:
        """
        Schätzt Expected Goals aus verfügbaren Features
        
        Args:
            features: Feature Dictionary
            
        Returns:
            (home_xg, away_xg)
        """
        # Basis: Durchschnittliche Tore
        home_xg = features.get('home_avg_goals_scored_overall', 1.5)
        away_xg = features.get('away_avg_goals_scored_overall', 1.3)
        
        # Adjustierung: Heimvorteil
        home_xg *= 1.15  # 15% Heimvorteil
        away_xg *= 0.95  # 5% Auswärts-Nachteil
        
        # Adjustierung: Defensive Stärke
        home_conceded = features.get('home_avg_goals_conceded_overall', 1.2)
        away_conceded = features.get('away_avg_goals_conceded_overall', 1.3)
        
        # Kombiniere Offensive + Gegner-Defensive
        home_xg_adjusted = (home_xg + away_conceded) / 2
        away_xg_adjusted = (away_xg + home_conceded) / 2
        
        # Clamp zwischen 0.3 und 4.0
        home_xg_final = max(0.3, min(4.0, home_xg_adjusted))
        away_xg_final = max(0.3, min(4.0, away_xg_adjusted))
        
        return home_xg_final, away_xg_final
    
    def get_most_likely_scoreline_for_markets(
        self,
        prediction_1x2: str,
        prediction_ou: str,
        prediction_btts: str,
        scorelines: List[Dict]
    ) -> Dict:
        """
        Findet wahrscheinlichste Scoreline die zu den Market-Predictions passt
        
        Args:
            prediction_1x2: '1X2' prediction
            prediction_ou: 'Over/Under' prediction
            prediction_btts: 'BTTS' prediction
            scorelines: Liste aller Scorelines
            
        Returns:
            Dict mit bester Scoreline oder None
        """
        matching = []
        
        for scoreline in scorelines:
            if (scoreline['result'] == prediction_1x2 and
                scoreline['over_under'] == prediction_ou and
                scoreline['btts'] == prediction_btts):
                matching.append(scoreline)
        
        if matching:
            # Sortiere nach Wahrscheinlichkeit
            matching.sort(key=lambda x: x['probability'], reverse=True)
            return matching[0]
        
        return None


def create_scoreline_display(
    scorelines: List[Dict],
    market_probs: Dict,
    home_team: str,
    away_team: str
) -> str:
    """
    Erstellt formatierte Ausgabe für Scorelines
    
    Args:
        scorelines: Top Scorelines
        market_probs: Markt-Wahrscheinlichkeiten
        home_team: Heimteam Name
        away_team: Auswärtsteam Name
        
    Returns:
        Formatierter String
    """
    output = f"\n🎯 SCORELINE PREDICTIONS\n"
    output += f"{home_team} vs {away_team}\n"
    output += "="*50 + "\n\n"
    
    output += "Top 5 Wahrscheinlichste Ergebnisse:\n\n"
    
    for i, scoreline in enumerate(scorelines[:5], 1):
        output += f"{i}. {scoreline['scoreline']} ({scoreline['probability']:.1f}%)\n"
        output += f"   ├─ Ergebnis: {scoreline['result']}\n"
        output += f"   ├─ Over/Under 2.5: {scoreline['over_under']}\n"
        output += f"   └─ BTTS: {scoreline['btts']}\n\n"
    
    output += "="*50 + "\n"
    output += "📊 ABGELEITETE MARKT-WAHRSCHEINLICHKEITEN:\n\n"
    
    output += "1X2:\n"
    output += f"  Home: {market_probs['1x2']['home']:.1f}%\n"
    output += f"  Draw: {market_probs['1x2']['draw']:.1f}%\n"
    output += f"  Away: {market_probs['1x2']['away']:.1f}%\n\n"
    
    output += "Over/Under 2.5:\n"
    output += f"  Over: {market_probs['over_under']['over']:.1f}%\n"
    output += f"  Under: {market_probs['over_under']['under']:.1f}%\n\n"
    
    output += "BTTS:\n"
    output += f"  Yes: {market_probs['btts']['yes']:.1f}%\n"
    output += f"  No: {market_probs['btts']['no']:.1f}%\n"
    
    return output
