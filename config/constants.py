"""
Konfigurationskonstanten für die Sportwetten-Prognose App
"""

# Google API Scopes
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Risikoprofile für Bankroll-Management
RISK_PROFILES = {
    "sehr_konservativ": {
        "name": "Sehr konservativ",
        "adjustment": 0.7,
        "max_stake_percent": 2.0,
        "description": "Minimales Risiko, kleine Einsätze",
        "color": "green",
    },
    "konservativ": {
        "name": "Konservativ",
        "adjustment": 0.85,
        "max_stake_percent": 3.0,
        "description": "Sicherheitsorientiert",
        "color": "lightgreen",
    },
    "moderat": {
        "name": "Moderat",
        "adjustment": 1.0,
        "max_stake_percent": 5.0,
        "description": "Ausgewogenes Risiko/Ertrag",
        "color": "yellow",
    },
    "aggressiv": {
        "name": "Aggressiv",
        "adjustment": 1.15,
        "max_stake_percent": 7.0,
        "description": "Höhere Risikobereitschaft",
        "color": "orange",
    },
    "sehr_aggressiv": {
        "name": "Sehr aggressiv",
        "adjustment": 1.3,
        "max_stake_percent": 10.0,
        "description": "Maximale Risikobereitschaft",
        "color": "red",
    },
}

# Stake-Prozentsätze basierend auf Risiko-Score (1-5)
STAKE_PERCENTAGES = {
    1: 0.5,
    2: 1.0,
    3: 2.0,
    4: 3.5,
    5: 5.0,
}

# App-Konfiguration
APP_TITLE = "Sportwetten-Prognose v6.0 (SMART-PRECISION)"
APP_ICON = "⚽"
APP_LAYOUT = "wide"

# Export Sheet
EXPORT_SHEET_ID = "1ycsgPdfFal2pS7pwMlTgTRcXwy_22QFZLb6ZZ85zxNE"

# Version Info
APP_VERSION = "v6.0"
APP_FEATURES = [
    "⚡ ML-Korrekturen aktiviert",
    "🎯 Strenges Risiko-Scoring 1-5",
    "💰 Bankroll-Management",
]
