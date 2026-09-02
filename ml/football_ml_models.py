"""
Football ML Models Integration
Lädt und nutzt trainierte XGBoost/RandomForest Models
"""

import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional


class FootballMLModels:
    """
    Verwaltet die trainierten ML-Models für Over/Under, 1X2 und BTTS
    Unterstützt beide Versionen: MIT und OHNE Quoten
    """
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_loaded = False
        
        # Models
        self.models_with_odds = {}
        self.models_no_odds = {}
        
        # Feature Lists
        self.features_with_odds = []
        self.features_no_odds = []
        
        # Config
        self.feature_config = {}
        
    def load_models(self) -> bool:
        """
        Lädt alle gespeicherten Models und Konfigurationen
        
        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        try:
            # Lade Feature Config
            config_path = self.models_dir / "feature_config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.feature_config = json.load(f)
                    self.features_with_odds = self.feature_config.get('features_with_odds', [])
                    self.features_no_odds = self.feature_config.get('features_no_odds', [])
            
            # Lade Models MIT Quoten
            models_with = {
                'over_under': self.models_dir / 'over_under_with_odds.pkl',
                '1x2': self.models_dir / '1x2_with_odds.pkl',
                'btts': self.models_dir / 'btts_with_odds.pkl'
            }
            
            for name, path in models_with.items():
                if path.exists():
                    with open(path, 'rb') as f:
                        self.models_with_odds[name] = pickle.load(f)
            
            # Lade Models OHNE Quoten
            models_no = {
                'over_under': self.models_dir / 'over_under_no_odds.pkl',
                '1x2': self.models_dir / '1x2_no_odds.pkl',
                'btts': self.models_dir / 'btts_no_odds.pkl'
            }
            
            for name, path in models_no.items():
                if path.exists():
                    with open(path, 'rb') as f:
                        self.models_no_odds[name] = pickle.load(f)
            
            self.models_loaded = (
                len(self.models_with_odds) > 0 or 
                len(self.models_no_odds) > 0
            )
            
            return self.models_loaded
            
        except Exception as e:
            print(f"Fehler beim Laden der Models: {e}")
            return False
    
    def prepare_features(self, match_data: Dict, use_odds: bool = True) -> Optional[pd.DataFrame]:
        """
        Bereitet Features für Prediction vor
        
        Args:
            match_data: Dictionary mit Match-Daten
            use_odds: True = mit Quoten, False = ohne Quoten
            
        Returns:
            DataFrame mit Features oder None
        """
        try:
            # Wähle Feature-Liste
            features = self.features_with_odds if use_odds else self.features_no_odds
            
            if not features:
                return None
            
            # Erstelle DataFrame
            feature_dict = {}
            
            for feature in features:
                # Versuche Feature aus match_data zu holen
                if feature in match_data:
                    feature_dict[feature] = match_data[feature]
                else:
                    # Default-Wert (Median oder 0)
                    feature_dict[feature] = 0
            
            df = pd.DataFrame([feature_dict])
            
            return df
            
        except Exception as e:
            print(f"Fehler bei Feature-Vorbereitung: {e}")
            return None
    
    def predict_over_under(
        self, 
        match_data: Dict, 
        use_odds: bool = True
    ) -> Optional[Dict]:
        """
        Prediction für Over/Under 2.5
        
        Args:
            match_data: Match-Daten
            use_odds: Mit oder ohne Quoten
            
        Returns:
            Dict mit Prediction und Confidence
        """
        try:
            models = self.models_with_odds if use_odds else self.models_no_odds
            
            if 'over_under' not in models:
                return None
            
            # Features vorbereiten
            X = self.prepare_features(match_data, use_odds)
            if X is None:
                return None
            
            # Prediction
            model = models['over_under']
            prediction = model.predict(X)[0]
            probabilities = model.predict_proba(X)[0]
            
            result = {
                'prediction': 'OVER 2.5' if prediction == 1 else 'UNDER 2.5',
                'prediction_value': int(prediction),
                'confidence': float(probabilities[prediction]) * 100,
                'prob_under': float(probabilities[0]) * 100,
                'prob_over': float(probabilities[1]) * 100,
            }
            
            return result
            
        except Exception as e:
            print(f"Fehler bei Over/Under Prediction: {e}")
            return None
    
    def predict_1x2(
        self, 
        match_data: Dict, 
        use_odds: bool = True
    ) -> Optional[Dict]:
        """
        Prediction für 1X2
        
        Args:
            match_data: Match-Daten
            use_odds: Mit oder ohne Quoten
            
        Returns:
            Dict mit Prediction und Confidence
        """
        try:
            models = self.models_with_odds if use_odds else self.models_no_odds
            
            if '1x2' not in models:
                return None
            
            # Features vorbereiten
            X = self.prepare_features(match_data, use_odds)
            if X is None:
                return None
            
            # Prediction
            model = models['1x2']
            prediction = model.predict(X)[0]
            probabilities = model.predict_proba(X)[0]
            
            labels = {0: 'DRAW', 1: 'HOME WIN', 2: 'AWAY WIN'}
            
            result = {
                'prediction': labels[prediction],
                'prediction_value': int(prediction),
                'confidence': float(probabilities[prediction]) * 100,
                'prob_draw': float(probabilities[0]) * 100,
                'prob_home': float(probabilities[1]) * 100,
                'prob_away': float(probabilities[2]) * 100,
            }
            
            return result
            
        except Exception as e:
            print(f"Fehler bei 1X2 Prediction: {e}")
            return None
    
    def predict_btts(
        self, 
        match_data: Dict, 
        use_odds: bool = True
    ) -> Optional[Dict]:
        """
        Prediction für BTTS
        
        Args:
            match_data: Match-Daten
            use_odds: Mit oder ohne Quoten
            
        Returns:
            Dict mit Prediction und Confidence
        """
        try:
            models = self.models_with_odds if use_odds else self.models_no_odds
            
            if 'btts' not in models:
                return None
            
            # Features vorbereiten
            X = self.prepare_features(match_data, use_odds)
            if X is None:
                return None
            
            # Prediction
            model = models['btts']
            prediction = model.predict(X)[0]
            probabilities = model.predict_proba(X)[0]
            
            result = {
                'prediction': 'BTTS YES' if prediction == 1 else 'BTTS NO',
                'prediction_value': int(prediction),
                'confidence': float(probabilities[prediction]) * 100,
                'prob_no': float(probabilities[0]) * 100,
                'prob_yes': float(probabilities[1]) * 100,
            }
            
            return result
            
        except Exception as e:
            print(f"Fehler bei BTTS Prediction: {e}")
            return None
    
    def predict_all(
        self, 
        match_data: Dict, 
        use_odds: bool = True
    ) -> Dict:
        """
        Alle Predictions auf einmal
        
        Args:
            match_data: Match-Daten
            use_odds: Mit oder ohne Quoten
            
        Returns:
            Dict mit allen Predictions
        """
        return {
            'over_under': self.predict_over_under(match_data, use_odds),
            '1x2': self.predict_1x2(match_data, use_odds),
            'btts': self.predict_btts(match_data, use_odds),
            'version': 'MIT Quoten' if use_odds else 'OHNE Quoten (Echter Edge)'
        }
    
    def analyze_value(
        self, 
        prediction: Dict, 
        odds: float
    ) -> Dict:
        """
        Analysiert ob eine Wette Value hat
        
        Args:
            prediction: Prediction Dictionary
            odds: Wettquote
            
        Returns:
            Dict mit Value-Analyse
        """
        if not prediction or 'confidence' not in prediction:
            return {'has_value': False, 'expected_value': 0}
        
        confidence = prediction['confidence'] / 100
        implied_prob = 1 / odds if odds > 0 else 0
        
        # Expected Value
        ev = (confidence * odds) - 1
        
        # Hat Value wenn Expected Value > 0 UND Confidence > Implied Probability
        has_value = ev > 0 and confidence > implied_prob
        
        return {
            'has_value': has_value,
            'expected_value': ev * 100,  # in %
            'edge': (confidence - implied_prob) * 100,  # in %
            'implied_probability': implied_prob * 100,
            'confidence': confidence * 100
        }


# Singleton Instance
_ml_models_instance = None


def get_ml_models(models_dir: str = "models") -> FootballMLModels:
    """
    Gibt Singleton-Instanz der ML-Models zurück
    """
    global _ml_models_instance
    
    if _ml_models_instance is None:
        _ml_models_instance = FootballMLModels(models_dir)
        _ml_models_instance.load_models()
    
    return _ml_models_instance
