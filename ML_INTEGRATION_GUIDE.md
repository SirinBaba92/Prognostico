# ML Models Integration - Setup Guide

## 📋 Was wurde hinzugefügt?

### Neue Dateien:
1. **ml/football_ml_models.py** - ML Models Manager
2. **ui/ml_predictions_ui.py** - UI für ML Predictions

### Keine Änderungen an bestehenden Dateien!
- ✅ Alle deine bisherigen Funktionen bleiben erhalten
- ✅ Komplett neues Modul, kein Konflikt

---

## 🚀 Setup (3 Schritte)

### SCHRITT 1: Models kopieren

Kopiere die trainierten Models in deine App:

```bash
# Im Football ML Project Verzeichnis
cp -r models/* /path/to/sportwetten-analyse/models/
```

Die Models müssen in `sportwetten-analyse/models/` sein:
- over_under_with_odds.pkl
- over_under_no_odds.pkl
- 1x2_with_odds.pkl
- 1x2_no_odds.pkl
- btts_with_odds.pkl
- btts_no_odds.pkl
- feature_config.json

---

### SCHRITT 2: app.py Integration

Füge folgenden Code in deine `app.py` ein:

**Option A: Neuer Tab in Sidebar**

```python
# Am Anfang der Datei (bei den anderen Imports):
from ui.ml_predictions_ui import show_ml_predictions_tab

# In der main() Funktion, nach deinen bestehenden Tabs:
if st.sidebar.button("🤖 ML Predictions"):
    st.session_state.page = "ml_predictions"

# Im Hauptbereich, wo du deine Pages anzeigst:
if st.session_state.get('page') == "ml_predictions":
    show_ml_predictions_tab()
```

**Option B: Als zusätzlicher Bereich im Match-Tab**

```python
# In deinem bestehenden Match-Analyse Tab:
from ui.ml_predictions_ui import show_ml_predictions_tab

# Nach deiner normalen Analyse:
st.markdown("---")
st.markdown("## 🤖 Zusätzliche ML Predictions")

with st.expander("📊 XGBoost & Random Forest Models", expanded=False):
    show_ml_predictions_tab()
```

---

### SCHRITT 3: Testen

```bash
cd sportwetten-analyse
streamlit run app.py
```

Navigiere zum neuen "ML Predictions" Tab!

---

## 🎯 Verwendung

### Manuelle Eingabe:
1. Öffne ML Predictions Tab
2. Gib Match-Daten ein (Teams, Positionen, etc.)
3. Gib Quoten ein (optional)
4. Klicke "PREDICTIONS ERSTELLEN"

### Zwei Versionen verfügbar:
- **MIT Quoten**: Höhere Accuracy, aber nutzt Markt-Info
- **OHNE Quoten**: Echter Edge, unabhängig vom Markt

### Value-Bet Detection:
- Zeigt automatisch ob eine Wette Value hat
- Expected Value Berechnung
- Edge vs. Markt

---

## 📊 Features

✅ Over/Under 2.5 Predictions (XGBoost)
✅ 1X2 Predictions (Random Forest)
✅ BTTS Predictions (Random Forest)
✅ Confidence Scores
✅ Value-Bet Analyse
✅ Mit/Ohne Quoten Vergleich
✅ Visualisierung mit Progress Bars

---

## 🔧 Troubleshooting

**Problem: "ML-Models nicht gefunden"**
```bash
# Stelle sicher Models im richtigen Ordner sind:
ls models/*.pkl
# Du solltest 6 .pkl Dateien sehen
```

**Problem: Import Fehler**
```bash
# Stelle sicher Pakete installiert sind:
pip install scikit-learn xgboost
```

**Problem: Feature Fehler**
```bash
# Models erwarten bestimmte Features
# Checke feature_config.json für Feature-Liste
```

---

## 💡 Nächste Schritte

### Integration mit Google Sheets:
Du kannst die ML Predictions mit deinen Sheet-Daten verbinden:

```python
# In deiner Sheet-Lade-Funktion:
match_data = parse_sheet_data(sheet)

# Dann:
from ml.football_ml_models import get_ml_models
ml_models = get_ml_models()
predictions = ml_models.predict_all(match_data, use_odds=True)
```

### Automatische Batch-Predictions:
Für alle Matches auf einmal predicten und in Sheet zurückschreiben.

---

## ✅ Fertig!

Du hast jetzt professionelle ML-Models in deiner Streamlit App!

**Viel Erfolg mit den Predictions!** 🚀
