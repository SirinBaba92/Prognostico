"""
Daten-Modul für Sportwetten-Prognose App
"""

from .models import TeamStats, H2HResult, MatchData, ExtendedMatchData
from .parser import DataParser
from .google_sheets import (
    connect_to_sheets,
    connect_to_drive,
    list_daily_sheets_in_folder,
    list_match_tabs_for_day,
    read_sheet_range,
    parse_date,
    get_all_worksheets,
    read_worksheet_data,
    get_all_worksheets_by_id,
    read_worksheet_text_by_id,
    get_tracking_sheet_id,
)

__all__ = [
    # Models
    "TeamStats",
    "H2HResult",
    "MatchData",
    "ExtendedMatchData",
    # Parser
    "DataParser",
    # Google Sheets
    "connect_to_sheets",
    "connect_to_drive",
    "list_daily_sheets_in_folder",
    "list_match_tabs_for_day",
    "read_sheet_range",
    "parse_date",
    "get_all_worksheets",
    "read_worksheet_data",
    "get_all_worksheets_by_id",
    "read_worksheet_text_by_id",
    "get_tracking_sheet_id",
]
