"""
Google Sheets Persistenz für das Bankroll System
- Tab "Bankroll_Status": Bankroll pro User (user_id, bankroll, initial, updated)
- Tab "Bankroll_Bets": Alle Wetten (offen + abgeschlossen)
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

TAB_STATUS = "Bankroll_Status"
TAB_BETS   = "Bankroll_Bets"

HEADERS_STATUS = ["user_id", "bankroll", "initial", "open_bets_count", "updated_at"]
HEADERS_BETS   = [
    "user_id", "bet_id", "match", "bet_type", "odds",
    "stake", "potential_win", "prob", "date", "time",
    "status", "profit", "closed_at"
]


# ─────────────────────────────────────────────
# SERVICE
# ─────────────────────────────────────────────

def _get_service():
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    import streamlit as st

    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds)


def _get_sheet_id() -> Optional[str]:
    try:
        import streamlit as st
        return st.secrets.get("tracking", {}).get("sheet_id")
    except Exception:
        return os.getenv("TRACKING_SHEET_ID")


# ─────────────────────────────────────────────
# SETUP: Tabs + Header erstellen
# ─────────────────────────────────────────────

def _ensure_tabs(service, spreadsheet_id: str):
    """Erstellt fehlende Tabs mit Headern"""
    try:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        existing = [s["properties"]["title"] for s in meta.get("sheets", [])]

        requests = []
        for tab in [TAB_STATUS, TAB_BETS]:
            if tab not in existing:
                requests.append({"addSheet": {"properties": {"title": tab}}})

        if requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            ).execute()

        # Header setzen falls Tab neu oder leer
        for tab, headers in [(TAB_STATUS, HEADERS_STATUS), (TAB_BETS, HEADERS_BETS)]:
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{tab}!A1:Z1"
            ).execute()
            if not result.get("values"):
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{tab}!A1",
                    valueInputOption="RAW",
                    body={"values": [headers]}
                ).execute()
                logger.info(f"Header für Tab '{tab}' erstellt")

    except Exception as e:
        logger.error(f"_ensure_tabs Fehler: {e}")


# ─────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────

def load_user(user_id: int) -> Optional[dict]:
    try:
        sheet_id = _get_sheet_id()
        if not sheet_id:
            return None

        service = _get_service()
        _ensure_tabs(service, sheet_id)

        # Status laden
        res = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_STATUS}!A:E"
        ).execute()
        rows = res.get("values", [])
        status_row = None
        for row in rows[1:]:
            if len(row) >= 1 and str(row[0]) == str(user_id):
                status_row = row
                break

        if not status_row:
            return None

        bankroll = float(status_row[1]) if len(status_row) > 1 else 0.0
        initial  = float(status_row[2]) if len(status_row) > 2 else 0.0

        # Wetten laden
        res2 = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_BETS}!A:M"
        ).execute()
        bet_rows = res2.get("values", [])

        open_bets = []
        history   = []

        for row in bet_rows[1:]:
            if len(row) < 11 or str(row[0]) != str(user_id):
                continue
            bet = {
                "id":            int(row[1]) if len(row) > 1 else 0,
                "match":         row[2]      if len(row) > 2 else "",
                "bet_type":      row[3]      if len(row) > 3 else "",
                "odds":          float(row[4]) if len(row) > 4 else 0,
                "stake":         float(row[5]) if len(row) > 5 else 0,
                "potential_win": float(row[6]) if len(row) > 6 else 0,
                "prob":          float(row[7]) if len(row) > 7 else 0,
                "date":          row[8]       if len(row) > 8 else "",
                "time":          row[9]       if len(row) > 9 else "",
                "status":        row[10]      if len(row) > 10 else "open",
                "profit":        float(row[11]) if len(row) > 11 else 0,
                "closed":        row[12]      if len(row) > 12 else "",
            }
            if bet["status"] == "open":
                open_bets.append(bet)
            else:
                history.append(bet)

        return {
            "bankroll": bankroll,
            "initial":  initial,
            "bets":     open_bets,
            "history":  history,
        }

    except Exception as e:
        logger.error(f"load_user Fehler: {e}")
        return None


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────

def save_user(user_id: int, data: dict):
    try:
        sheet_id = _get_sheet_id()
        if not sheet_id:
            return

        service = _get_service()
        _ensure_tabs(service, sheet_id)

        from datetime import datetime
        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        # ── Status Tab ──
        res = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_STATUS}!A:A"
        ).execute()
        uid_col = [r[0] if r else "" for r in res.get("values", [])]

        open_count = len(data.get("bets", []))
        status_row = [
            str(user_id),
            str(data["bankroll"]),
            str(data["initial"]),
            str(open_count),
            now
        ]

        if str(user_id) in uid_col:
            row_num = uid_col.index(str(user_id)) + 1
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{TAB_STATUS}!A{row_num}",
                valueInputOption="RAW",
                body={"values": [status_row]}
            ).execute()
        else:
            service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=f"{TAB_STATUS}!A:E",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [status_row]}
            ).execute()

        # ── Bets Tab: alle Wetten dieses Users neu schreiben ──
        res2 = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_BETS}!A:M"
        ).execute()
        all_rows = res2.get("values", [])

        # Andere User behalten, eigene entfernen
        header = all_rows[0] if all_rows else HEADERS_BETS
        other_rows = [r for r in all_rows[1:] if r and str(r[0]) != str(user_id)]

        # Eigene Wetten (offen + history) als Rows
        all_bets = data.get("bets", []) + data.get("history", [])
        new_bet_rows = []
        for bet in all_bets:
            new_bet_rows.append([
                str(user_id),
                str(bet.get("id", "")),
                bet.get("match", ""),
                bet.get("bet_type", ""),
                str(bet.get("odds", "")),
                str(bet.get("stake", "")),
                str(bet.get("potential_win", "")),
                str(bet.get("prob", "")),
                bet.get("date", ""),
                bet.get("time", ""),
                bet.get("status", "open"),
                str(bet.get("profit", "")),
                bet.get("closed", ""),
            ])

        # Alles neu schreiben
        all_new = [header] + other_rows + new_bet_rows
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=f"{TAB_BETS}!A:M"
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{TAB_BETS}!A1",
            valueInputOption="RAW",
            body={"values": all_new}
        ).execute()

    except Exception as e:
        logger.error(f"save_user Fehler: {e}")
