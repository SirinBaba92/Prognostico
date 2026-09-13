"""
Trainiert die 6 Produktions-Models (Over/Under 2.5, 1X2, BTTS -- je mit und
ohne Quoten) auf echten historischen Spielen mit echten Ergebnissen.

Feature-Set = exakt die Felder, die TeamStats liefert (siehe data/models.py)
+ Quoten -- bewusst deckungsgleich mit dem, was
ui/sheets_ml_integration.py::convert_match_data_to_features() aus einem
echten Supabase-Match tatsaechlich extrahieren kann. Kein Feature, das im
Live-Betrieb nicht befuellt werden kann.

Chronologischer Split (aelteste Spiele = Training, neueste = Test) statt
zufaelligem Split, weil das Modell im Live-Betrieb auch nur Vergangenes
kennt. Nach dem Training wird der Brier-Score auf dem Test-Teil ausgegeben,
damit man sieht, ob das Modell tatsaechlich etwas taugt statt blind zu
vertrauen.

Nutzung:
    python3 ml/train_models.py --csv /pfad/zu/historical_dataset.csv
"""

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

TEAM_STATS_FIELDS = [
    "position", "games", "wins", "draws", "losses",
    "goals_for", "goals_against", "goal_diff", "points",
    "form_points", "form_goals_for", "form_goals_against",
    "ha_points", "ha_goals_for", "ha_goals_against",
    "ppg_overall", "ppg_ha", "avg_goals_match", "avg_goals_match_ha",
    "goals_scored_per_match", "goals_conceded_per_match",
    "goals_scored_per_match_ha", "goals_conceded_per_match_ha",
    "btts_yes_overall", "btts_yes_ha", "cs_yes_overall", "cs_yes_ha",
    "fts_yes_overall", "fts_yes_ha",
    "xg_for", "xg_against", "xg_for_ha", "xg_against_ha",
    "shots_per_match", "shots_on_target", "shots_off_target", "conversion_rate",
    "over25_pct_overall", "over25_pct_ha", "possession",
]

FEATURES_NO_ODDS = [f"home_{f}" for f in TEAM_STATS_FIELDS] + [f"away_{f}" for f in TEAM_STATS_FIELDS]
ODDS_FEATURES = ["odds_home", "odds_draw", "odds_away", "odds_over25", "odds_under25", "odds_btts_yes", "odds_btts_no"]
FEATURES_WITH_ODDS = FEATURES_NO_ODDS + ODDS_FEATURES

# CSV-Spaltennamen -> unsere Feature-Namen (Statistik-Felder sind 1:1 gleich
# benannt bis auf den home_/away_-Prefix, nur die Quoten heissen in der CSV
# anders als im Feature-Schema der App).
CSV_ODDS_COLS = {
    "odds_home": "odds_1x2_home", "odds_draw": "odds_1x2_draw", "odds_away": "odds_1x2_away",
    "odds_over25": "odds_ou25_over", "odds_under25": "odds_ou25_under",
    "odds_btts_yes": "odds_btts_yes", "odds_btts_no": "odds_btts_no",
}


def load_dataset(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    before = len(df)
    df = df.dropna().reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"{dropped} Zeilen mit fehlenden Werten uebersprungen.")

    df["_date_sort"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
    df = df.sort_values("_date_sort").reset_index(drop=True)

    for feature_name, csv_col in CSV_ODDS_COLS.items():
        df[feature_name] = df[csv_col]

    actual_h = df["actual_home_goals"].astype(int)
    actual_a = df["actual_away_goals"].astype(int)
    # Label-Encoding MUSS zu ml/football_ml_models.py passen:
    # 1X2: 0=DRAW, 1=HOME WIN, 2=AWAY WIN
    df["y_1x2"] = np.select([actual_h > actual_a, actual_h == actual_a], [1, 0], default=2)
    df["y_over_under"] = ((actual_h + actual_a) > 2.5).astype(int)  # 1=OVER
    df["y_btts"] = ((actual_h > 0) & (actual_a > 0)).astype(int)  # 1=YES

    print(f"{len(df)} Spiele geladen ({df['_date_sort'].min().date()} bis {df['_date_sort'].max().date()})")
    return df


MODEL_PARAMS = {
    "1x2": {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.03,
            "subsample": 0.7, "colsample_bytree": 0.6, "min_child_weight": 10, "reg_lambda": 5},
    "over_under": {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.03,
                   "subsample": 0.7, "colsample_bytree": 0.6, "min_child_weight": 10, "reg_lambda": 5},
    "btts": {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.03,
             "subsample": 0.7, "colsample_bytree": 0.6, "min_child_weight": 10, "reg_lambda": 5},
}


def brier_1x2(probs, actual_h, actual_a):
    # probs-Reihenfolge = Klassenindex 0=draw,1=home,2=away (siehe y_1x2 oben)
    if actual_h > actual_a:
        outcome = (0, 1, 0)
    elif actual_h == actual_a:
        outcome = (1, 0, 0)
    else:
        outcome = (0, 0, 1)
    return sum((p - o) ** 2 for p, o in zip(probs, outcome))


def brier_binary(p_yes, actual_yes):
    return (p_yes - (1.0 if actual_yes else 0.0)) ** 2


def train_market(name: str, df: pd.DataFrame, split_idx: int, feature_cols, target_col: str, multiclass: bool):
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]
    X_train, X_test = train_df[feature_cols].values, test_df[feature_cols].values
    y_train = train_df[target_col].values

    clf = XGBClassifier(
        random_state=42,
        eval_metric="mlogloss" if multiclass else "logloss",
        **MODEL_PARAMS[name],
    )
    clf.fit(X_train, y_train)

    proba_test = clf.predict_proba(X_test)
    actual_h, actual_a = test_df["actual_home_goals"].astype(int).values, test_df["actual_away_goals"].astype(int).values

    if multiclass:
        briers = [brier_1x2(proba_test[i], actual_h[i], actual_a[i]) for i in range(len(test_df))]
    else:
        y_test = test_df[target_col].values
        briers = [brier_binary(proba_test[i, 1], bool(y_test[i])) for i in range(len(test_df))]

    print(f"  {name:<12} Brier-Score (Test, n={len(test_df)}): {sum(briers) / len(briers):.4f}")

    # Finales Modell fuer den Export: auf ALLEN Daten trainiert (Training +
    # Test), damit das ausgelieferte Modell die maximale verfuegbare Historie
    # nutzt -- der Brier-Score oben (nur auf dem Trainings-Teil gemessen)
    # bleibt die ehrliche Qualitaetsangabe fuer dieses Feature-Set.
    final_clf = XGBClassifier(
        random_state=42,
        eval_metric="mlogloss" if multiclass else "logloss",
        **MODEL_PARAMS[name],
    )
    final_clf.fit(df[feature_cols].values, df[target_col].values)
    return final_clf, sum(briers) / len(briers)


def main():
    parser = argparse.ArgumentParser(description="Trainiert die ML-Produktionsmodelle auf echten Spieldaten.")
    parser.add_argument("--csv", required=True, help="Pfad zur historical_dataset.csv")
    parser.add_argument("--models-dir", default="models", help="Zielordner fuer .pkl/feature_config.json")
    parser.add_argument("--test-fraction", type=float, default=0.2, help="Anteil der neuesten Spiele fuer die Test-Auswertung")
    args = parser.parse_args()

    df = load_dataset(args.csv)
    split_idx = int(len(df) * (1 - args.test_fraction))
    print(f"Split fuer Evaluation: {split_idx} Training / {len(df) - split_idx} Test\n")

    models_dir = Path(args.models_dir)
    models_dir.mkdir(exist_ok=True)

    results = {}
    print("Training MIT Quoten:")
    for market, target_col, multiclass in [("1x2", "y_1x2", True), ("over_under", "y_over_under", False), ("btts", "y_btts", False)]:
        model, brier = train_market(market, df, split_idx, FEATURES_WITH_ODDS, target_col, multiclass)
        with open(models_dir / f"{market}_with_odds.pkl", "wb") as f:
            pickle.dump(model, f)
        results[f"{market}_with_odds"] = brier

    print("\nTraining OHNE Quoten:")
    for market, target_col, multiclass in [("1x2", "y_1x2", True), ("over_under", "y_over_under", False), ("btts", "y_btts", False)]:
        model, brier = train_market(market, df, split_idx, FEATURES_NO_ODDS, target_col, multiclass)
        with open(models_dir / f"{market}_no_odds.pkl", "wb") as f:
            pickle.dump(model, f)
        results[f"{market}_no_odds"] = brier

    # Feature-Defaults (Median) fuer robustes Fallback bei fehlenden Feldern
    # (z.B. manuelle Eingabe, die nicht alle Felder abfragt) statt hartem 0.
    feature_defaults = {col: float(df[col].median()) for col in FEATURES_WITH_ODDS}

    feature_config = {
        "features_with_odds": FEATURES_WITH_ODDS,
        "features_no_odds": FEATURES_NO_ODDS,
        "odds_features": ODDS_FEATURES,
        "feature_defaults": feature_defaults,
        "model_params": MODEL_PARAMS,
        "trained_on": {
            "csv": str(Path(args.csv).resolve()),
            "n_matches": len(df),
            "date_range": [str(df["_date_sort"].min().date()), str(df["_date_sort"].max().date())],
            "test_brier_scores": results,
        },
    }
    with open(models_dir / "feature_config.json", "w") as f:
        json.dump(feature_config, f, indent=2)

    print(f"\nFertig. Models + feature_config.json geschrieben nach {models_dir.resolve()}")


if __name__ == "__main__":
    main()
