"""
ML-Modell für Tabellenpositions-basierte Korrekturen
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List
from data.models import TeamStats
from ml.features import create_position_features, encode_position_features


class TablePositionML:
    """
    ML-Modell zur Korrektur von μ-Werten basierend auf Tabellenpositionen
    """
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.training_data_size = 0
        self.last_trained = None
        self.feature_importance = {}
        self.model_type = "none"

    def initialize_model(self):
        """
        Initialisiert das ML-Modell (XGBoost oder RandomForest als Fallback)
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            try:
                import xgboost as xgb

                self.model = xgb.XGBRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    objective="reg:squarederror",
                )
                self.model_type = "xgboost"
            except ImportError:
                from sklearn.ensemble import RandomForestRegressor

                self.model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    min_samples_split=5,
                    min_samples_leaf=2,
                )
                self.model_type = "randomforest"

            return True
        except Exception as e:
            st.error(f"❌ Fehler bei ML-Modell Initialisierung: {e}")
            self.model = None
            return False

    def create_features(
        self, home_team: TeamStats, away_team: TeamStats, match_date: str
    ) -> Dict:
        """
        Erstellt Features für ein Match
        
        Args:
            home_team: Heimteam Statistics
            away_team: Auswärtsteam Statistics
            match_date: Match-Datum
            
        Returns:
            Dictionary mit Features
        """
        return create_position_features(home_team, away_team, match_date)

    def prepare_training_data(self, historical_matches: List[Dict]):
        """
        Bereitet Trainingsdaten vor
        
        Args:
            historical_matches: Liste von historischen Matches
            
        Returns:
            Tuple (X_train, y_train)
        """
        X_train = []
        y_train = []

        for match in historical_matches:
            try:
                home_team_data = match.get("home_team", {})
                away_team_data = match.get("away_team", {})
                match_date = match.get("date", "")

                features = self.create_features(
                    home_team_data, away_team_data, match_date
                )
                encoded_features = encode_position_features(features)

                predicted_mu_home = match.get("predicted_mu_home", 1.0)
                predicted_mu_away = match.get("predicted_mu_away", 1.0)
                actual_mu_home = match.get("actual_mu_home", 1.0)
                actual_mu_away = match.get("actual_mu_away", 1.0)

                if predicted_mu_home > 0 and predicted_mu_away > 0:
                    correction_home = actual_mu_home / predicted_mu_home
                    correction_away = actual_mu_away / predicted_mu_away

                    X_train.append(list(encoded_features.values()))
                    y_train.append([correction_home, correction_away])

            except Exception as e:
                continue

        return X_train, y_train

    def train(self, historical_matches: List[Dict], min_matches: int = 30) -> Dict:
        """
        Trainiert das ML-Modell
        
        Args:
            historical_matches: Liste von historischen Matches
            min_matches: Minimale Anzahl benötigter Matches
            
        Returns:
            Dictionary mit Training-Ergebnis
        """
        if len(historical_matches) < min_matches:
            return {
                "success": False,
                "message": f"Nicht genügend Daten: {len(historical_matches)}/{min_matches}",
                "matches_required": min_matches - len(historical_matches),
            }

        if self.model is None:
            if not self.initialize_model():
                return {
                    "success": False,
                    "message": "ML-Modell konnte nicht initialisiert werden",
                }

        X_train, y_train = self.prepare_training_data(historical_matches)

        if len(X_train) < min_matches:
            return {
                "success": False,
                "message": f"Nicht genügend Trainingsdaten: {len(X_train)}/{min_matches}",
                "matches_required": min_matches - len(X_train),
            }

        try:
            self.model.fit(X_train, y_train)
            self.is_trained = True
            self.training_data_size = len(X_train)
            self.last_trained = datetime.now()

            if hasattr(self.model, "feature_importances_"):
                dummy_team = TeamStats(
                    "",
                    1,
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                )
                features = self.create_features(dummy_team, dummy_team, "2024-01-01")
                encoded = encode_position_features(features)
                feature_names = list(encoded.keys())

                if len(feature_names) == len(self.model.feature_importances_):
                    self.feature_importance = dict(
                        zip(feature_names, self.model.feature_importances_)
                    )

            return {
                "success": True,
                "message": f"Modell erfolgreich mit {len(X_train)} Matches trainiert",
                "training_size": len(X_train),
                "model_type": self.model_type,
                "last_trained": self.last_trained.strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception as e:
            return {"success": False, "message": f"Fehler beim Training: {str(e)}"}

    def predict_correction(
        self, home_team: TeamStats, away_team: TeamStats, match_date: str
    ) -> Dict:
        """
        Sagt Korrektur-Faktoren für ein Match vorher
        
        Args:
            home_team: Heimteam Statistics
            away_team: Auswärtsteam Statistics
            match_date: Match-Datum
            
        Returns:
            Dictionary mit Korrektur-Faktoren
        """
        if not self.is_trained or self.model is None:
            return {
                "home_correction": 1.0,
                "away_correction": 1.0,
                "confidence": 0.0,
                "is_trained": False,
                "message": "Modell nicht trainiert",
            }

        try:
            features = self.create_features(home_team, away_team, match_date)
            encoded_features = encode_position_features(features)

            X_pred = [list(encoded_features.values())]
            prediction = self.model.predict(X_pred)[0]

            home_correction = float(prediction[0])
            away_correction = float(prediction[1])

            home_correction = max(0.5, min(1.5, home_correction))
            away_correction = max(0.5, min(1.5, away_correction))

            confidence = min(0.9, self.training_data_size / 100)

            return {
                "home_correction": home_correction,
                "away_correction": away_correction,
                "confidence": confidence,
                "is_trained": True,
                "features_used": list(encoded_features.keys()),
                "message": f"ML-Korrektur basierend auf {self.training_data_size} Trainings-Matches",
            }

        except Exception as e:
            return {
                "home_correction": 1.0,
                "away_correction": 1.0,
                "confidence": 0.0,
                "is_trained": False,
                "message": f"Vorhersagefehler: {str(e)}",
            }

    def get_model_info(self) -> Dict:
        """
        Gibt Informationen über das Modell zurück
        
        Returns:
            Dictionary mit Modell-Informationen
        """
        return {
            "is_trained": self.is_trained,
            "model_type": self.model_type,
            "training_data_size": self.training_data_size,
            "last_trained": (
                self.last_trained.strftime("%Y-%m-%d %H:%M:%S")
                if self.last_trained
                else "never"
            ),
            "feature_importance": self.feature_importance,
        }
