"""
UI-Modul für Sportwetten-Prognose App
"""

from .results_display import display_results, display_risk_distribution
from .sidebar import show_sidebar
from .ml_training import show_ml_training_ui
from .extended_data_entry import show_extended_data_entry_ui
from .historical_data_ui import add_historical_match_ui
from .visualizations import (
    show_poisson_heatmap,
    show_historical_performance,
    show_confidence_gauge,
    show_team_radar,
)

__all__ = [
    "display_results",
    "display_risk_distribution",
    "show_sidebar",
    "show_ml_training_ui",
    "show_extended_data_entry_ui",
    "add_historical_match_ui",
    "show_poisson_heatmap",
    "show_historical_performance",
    "show_confidence_gauge",
    "show_team_radar",
]
