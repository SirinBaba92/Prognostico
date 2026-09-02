"""
Erweitertes ML-Modell mit In-Game Features
"""

import streamlit as st
import numpy as np
from typing import Dict, List


class ExtendedMatchML:
    """
    Erweitertes ML-Modell das Position-Features mit In-Game Daten kombiniert
    """
    
    def __init__(self):
        self.position_ml = None
        self.extended_model = None
        self.is_trained = False
        self.training_data_size = 0
        self.feature_importance = {}

    def initialize_model(self, base_ml_model):
        """
        Initialisiert das erweiterte ML-Modell
        
        Args:
            base_ml_model: Basis TablePositionML Modell
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        self.position_ml = base_ml_model

        try:
            from sklearn.ensemble import StackingRegressor, RandomForestRegressor
            from sklearn.linear_model import Ridge

            base_models = [
                (
                    "rf",
                    RandomForestRegressor(
                        n_estimators=50, max_depth=7, random_state=42
                    ),
                ),
                ("ridge", Ridge(alpha=1.0)),
            ]

            self.extended_model = StackingRegressor(
                estimators=base_models, final_estimator=Ridge(alpha=1.0), cv=5
            )

            return True
        except Exception as e:
            st.error(f"❌ Erweitertes ML-Modell Initialisierung fehlgeschlagen: {e}")
            return False

    def create_combined_features(
        self, position_features: Dict, extended_features: Dict
    ) -> Dict:
        """
        Kombiniert Position- und Extended-Features
        
        Args:
            position_features: Features von Tabellenpositionen
            extended_features: Features von In-Game Daten
            
        Returns:
            Dictionary mit kombinierten Features
        """
        combined = {}

        position_keys = [
            "home_position",
            "away_position",
            "position_diff",
            "position_diff_abs",
            "home_ppg",
            "away_ppg",
            "ppg_diff",
            "ppg_diff_abs",
            "season_progress",
            "home_pressure",
            "away_pressure",
        ]

        for key in position_keys:
            if key in position_features:
                combined[f"pos_{key}"] = position_features[key]

        extended_keys = [
            "halftime_lead",
            "home_leading_at_ht",
            "possession_dominance",
            "shot_dominance",
            "shot_on_target_dominance",
            "corner_dominance",
            "control_score",
            "defensive_stability_home",
            "defensive_stability_away",
            "offensive_efficiency_home",
            "offensive_efficiency_away",
        ]

        for key in extended_keys:
            if key in extended_features:
                combined[f"ext_{key}"] = extended_features[key]

        if "pos_home_position" in combined and "ext_possession_dominance" in combined:
            combined["interaction_top_possession"] = (
                1 if combined["pos_home_position"] <= 3 else 0
            ) * (1 if combined["ext_possession_dominance"] > 10 else 0)

        if "pos_home_pressure" in combined and "ext_halftime_lead" in combined:
            combined["interaction_pressure_halftime"] = combined[
                "pos_home_pressure"
            ] * (1 if combined["ext_halftime_lead"] > 0 else 0)

        combined["match_type"] = self.classify_match_type(
            position_features, extended_features
        )

        return combined

    def classify_match_type(
        self, position_features: Dict, extended_features: Dict
    ) -> int:
        """
        Klassifiziert Match-Typ basierend auf Features
        
        Args:
            position_features: Position-Features
            extended_features: Extended-Features
            
        Returns:
            Match-Typ (0-4)
        """
        possession = extended_features.get("possession_dominance", 0)
        shots_diff = extended_features.get("shot_dominance", 0)
        halftime_lead = extended_features.get("halftime_lead", 0)

        if abs(possession) > 15 and abs(shots_diff) > 8:
            return 1

        elif extended_features.get("fouls_total", 0) > 25:
            return 2

        elif extended_features.get("shots_total", 0) > 30:
            return 3

        elif abs(halftime_lead) > 2:
            return 4

        else:
            return 0

    def prepare_extended_training_data(self, historical_matches_with_extended: List[Dict]):
        """
        Bereitet erweiterte Trainingsdaten vor
        
        Args:
            historical_matches_with_extended: Historische Matches mit Extended Data
            
        Returns:
            Tuple (X_train, y_train) als numpy arrays
        """
        X_train = []
        y_train = []

        for match in historical_matches_with_extended:
            try:
                position_features = match.get("position_features", {})
                extended_features = match.get("extended_features", {})

                combined_features = self.create_combined_features(
                    position_features, extended_features
                )

                feature_vector = list(combined_features.values())

                predicted_mu_home = match.get("predicted_mu_home", 1.5)
                predicted_mu_away = match.get("predicted_mu_away", 1.5)
                actual_mu_home = match.get("actual_mu_home", 1.5)
                actual_mu_away = match.get("actual_mu_away", 1.5)

                if predicted_mu_home > 0 and predicted_mu_away > 0:
                    home_correction = actual_mu_home / predicted_mu_home
                    away_correction = actual_mu_away / predicted_mu_away

                    home_correction = max(0.5, min(2.0, home_correction))
                    away_correction = max(0.5, min(2.0, away_correction))

                    X_train.append(feature_vector)
                    y_train.append([home_correction, away_correction])

            except Exception as e:
                continue

        return np.array(X_train), np.array(y_train)

    def train(self, historical_matches_with_extended: List[Dict], min_matches: int = 20) -> Dict:
        """
        Trainiert das erweiterte ML-Modell
        
        Args:
            historical_matches_with_extended: Historische Matches mit Extended Data
            min_matches: Minimale Anzahl Matches
            
        Returns:
            Dictionary mit Training-Ergebnis
        """
        if len(historical_matches_with_extended) < min_matches:
            return {
                "success": False,
                "message": f"Nicht genügend erweiterte Daten: {len(historical_matches_with_extended)}/{min_matches}",
            }

        if self.extended_model is None:
            if not self.initialize_model(st.session_state.position_ml_model):
                return {
                    "success": False,
                    "message": "Erweitertes Modell konnte nicht initialisiert werden",
                }

        X_train, y_train = self.prepare_extended_training_data(
            historical_matches_with_extended
        )

        if len(X_train) < min_matches:
            return {
                "success": False,
                "message": f"Nicht genügend Trainingsdaten: {len(X_train)}/{min_matches}",
            }

        try:
            self.extended_model.fit(X_train, y_train)
            self.is_trained = True
            self.training_data_size = len(X_train)

            return {
                "success": True,
                "message": f"Erweitertes ML-Modell mit {len(X_train)} Spielen trainiert",
                "feature_count": X_train.shape[1] if len(X_train.shape) > 1 else 0,
            }

        except Exception as e:
            return {"success": False, "message": f"Training fehlgeschlagen: {str(e)}"}

    def predict_with_extended_data(
        self, position_features: Dict, extended_features: Dict
    ) -> Dict:
        """
        Sagt Korrekturen basierend auf erweiterten Features vorher
        
        Args:
            position_features: Position-Features
            extended_features: Extended-Features
            
        Returns:
            Dictionary mit Korrektur-Faktoren
        """
        if not self.is_trained:
            return {
                "home_correction": 1.0,
                "away_correction": 1.0,
                "confidence": 0.0,
                "message": "Erweitertes Modell nicht trainiert",
            }

        try:
            combined_features = self.create_combined_features(
                position_features, extended_features
            )

            X_pred = np.array([list(combined_features.values())])
            prediction = self.extended_model.predict(X_pred)[0]

            home_correction = float(prediction[0])
            away_correction = float(prediction[1])

            home_correction = max(0.5, min(1.5, home_correction))
            away_correction = max(0.5, min(1.5, away_correction))

            confidence = min(0.95, self.training_data_size / 50)

            return {
                "home_correction": home_correction,
                "away_correction": away_correction,
                "confidence": confidence,
                "features_used": len(combined_features),
                "match_type": combined_features.get("match_type", 0),
            }

        except Exception as e:
            return {
                "home_correction": 1.0,
                "away_correction": 1.0,
                "confidence": 0.0,
                "message": f"Vorhersagefehler: {str(e)}",
            }
