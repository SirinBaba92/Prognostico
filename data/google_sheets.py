"""
Google Sheets und Google Drive Verbindungsfunktionen
"""

import re
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config.constants import DRIVE_SCOPES, SHEETS_SCOPES


def connect_to_sheets(readonly: bool = True):
    """
    Verbindet sich mit Google Sheets API

    Args:
        readonly: Wenn True, nur Lesezugriff

    Returns:
        Google Sheets Service oder None bei Fehler
    """
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            credentials_dict, scopes=SHEETS_SCOPES
        )
        service = build("sheets", "v4", credentials=creds)
        return service
    except Exception as e:
        st.error(f"❌ Fehler bei Google Sheets Verbindung: {e}")
        return None


def connect_to_drive():
    """
    Verbindet sich mit Google Drive API

    Returns:
        Google Drive Service oder None bei Fehler
    """
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            credentials_dict, scopes=DRIVE_SCOPES
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        st.error(f"❌ Fehler bei Google Drive Verbindung: {e}")
        return None


DATE_NAME_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


@st.cache_data(ttl=300)
def list_daily_sheets_in_folder(folder_id: str) -> Dict[str, str]:
    """
    Listet alle Tabellenblätter in einem Ordner auf, die nach Datum benannt sind

    Args:
        folder_id: Google Drive Ordner-ID

    Returns:
        Dictionary: '15.12.2025' -> '<spreadsheetId>'
    """
    service = connect_to_drive()
    if service is None:
        return {}

    q = (
        f"'{folder_id}' in parents "
        "and mimeType='application/vnd.google-apps.spreadsheet' "
        "and trashed=false"
    )

    date_to_id: Dict[str, str] = {}
    page_token = None

    while True:
        resp = (
            service.files()
            .list(
                q=q,
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )

        for f in resp.get("files", []):
            name = (f.get("name") or "").strip()
            if DATE_NAME_RE.match(name):
                date_to_id[name] = f["id"]

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return date_to_id


@st.cache_data(ttl=300)
def list_match_tabs_for_day(sheet_id: str) -> List[str]:
    """
    Listet alle Worksheet-Titel in einem Spreadsheet auf

    Args:
        sheet_id: Google Sheets ID

    Returns:
        Liste der Worksheet-Titel in Reihenfolge
    """
    service = connect_to_sheets(readonly=True)
    if service is None:
        return []

    meta = (
        service.spreadsheets()
        .get(spreadsheetId=sheet_id, fields="sheets(properties(title,index))")
        .execute()
    )

    sheets = meta.get("sheets", [])
    sheets_sorted = sorted(sheets, key=lambda s: s["properties"].get("index", 0))
    return [s["properties"]["title"] for s in sheets_sorted]


@st.cache_data(ttl=300)
def read_sheet_range(sheet_id: str, a1_range: str) -> List[List[str]]:
    """
    Liest einen Bereich aus einem Google Sheet

    Args:
        sheet_id: Google Sheets ID
        a1_range: A1-Notation Bereich (z.B. "Sheet1!A:Z")

    Returns:
        2D-Liste mit Zellenwerten
    """
    service = connect_to_sheets(readonly=True)
    if service is None:
        return []
    resp = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=a1_range)
        .execute()
    )
    return resp.get("values", [])


def parse_date(d: str) -> date:
    """
    Parst Datumsstring im Format dd.mm.yyyy
    """
    return datetime.strptime(d, "%d.%m.%Y").date()


@st.cache_resource
def get_all_worksheets(sheet_url: str):
    """
    Holt alle Worksheets aus einer Google Sheets URL
    """
    try:
        service = connect_to_sheets(readonly=True)
        if service is None:
            return None

        spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        sheets = sheet_metadata.get("sheets", [])
        return {
            sheet["properties"]["title"]: sheet["properties"]["sheetId"]
            for sheet in sheets
        }
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        return None


@st.cache_data(ttl=300)
def read_worksheet_data(sheet_url: str, sheet_name: str) -> Optional[str]:
    """
    Liest Worksheet-Daten aus Google Sheets (Text-Repräsentation A:Z)
    """
    try:
        service = connect_to_sheets(readonly=True)
        if service is None:
            return None

        spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
        range_name = f"'{sheet_name}'!A:Z"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        data = result.get("values", [])

        text_data: List[str] = []
        for row in data:
            if any(cell.strip() for cell in row if cell):
                text_data.append("\t".join(row))
        return "\n".join(text_data)
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        return None


@st.cache_resource
def get_all_worksheets_by_id(spreadsheet_id: str):
    """
    Wie get_all_worksheets(), aber bekommt direkt die spreadsheetId
    """
    try:
        service = connect_to_sheets(readonly=True)
        if service is None:
            return None

        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        sheets = sheet_metadata.get("sheets", [])
        return {s["properties"]["title"]: s["properties"]["sheetId"] for s in sheets}
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        return None


@st.cache_data(ttl=300)
def read_worksheet_text_by_id(spreadsheet_id: str, sheet_name: str) -> Optional[str]:
    """
    Wie read_worksheet_data(), aber spreadsheetId direkt (Text-Repräsentation A:Z)
    """
    try:
        service = connect_to_sheets(readonly=True)
        if service is None:
            return None

        range_name = f"'{sheet_name}'!A:Z"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        data = result.get("values", [])

        text_data: List[str] = []
        for row in data:
            if any(cell.strip() for cell in row if cell):
                text_data.append("\t".join(row))
        return "\n".join(text_data)
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        return None


@st.cache_data(ttl=300)
def read_worksheet_text_range_by_id(
    spreadsheet_id: str, sheet_name: str, a1_range: str = "A1:Z40"
) -> Optional[str]:
    """
    Liest nur einen kleinen Bereich eines Worksheets (für schnelle Navigator-Indizes).
    Gibt Text-Repräsentation zurück.
    """
    try:
        service = connect_to_sheets(readonly=True)
        if service is None:
            return None

        range_name = f"'{sheet_name}'!{a1_range}"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        data = result.get("values", [])

        text_data: List[str] = []
        for row in data:
            if any(cell.strip() for cell in row if cell):
                text_data.append("\t".join(row))
        return "\n".join(text_data)
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        return None


def get_tracking_sheet_id() -> Optional[str]:
    """
    Holt die Tracking Sheet ID aus secrets (mit Fallbacks)
    """
    if "tracking" not in st.secrets:
        return None
    tracking = st.secrets["tracking"]
    return (
        tracking.get("sheet_id")
        or tracking.get("sheet_id_v48")
        or tracking.get("sheet_id_v47")
    )


@st.cache_data(ttl=300)
def read_worksheet_values_range_by_id(
    spreadsheet_id: str, sheet_name: str, a1_range: str = "B4:E7"
) -> Optional[List[List[str]]]:
    """
    Reads a small value range and returns the raw 2D values.
    Useful for fast match-header indexing without scanning large sheets.
    """
    try:
        service = connect_to_sheets(readonly=True)
        if service is None:
            return None

        range_name = f"'{sheet_name}'!{a1_range}"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        return result.get("values", [])
    except Exception:
        return None


@st.cache_data(ttl=300)
def batch_get_worksheet_values_ranges_by_id(
    spreadsheet_id: str,
    ranges: Tuple[str, ...],
) -> Dict[str, List[List[str]]]:
    """
    Batch reads multiple ranges from a single spreadsheet in ONE API call.

    Args:
        spreadsheet_id: Google Sheets ID
        ranges: A1 ranges including sheet name, e.g. ("'Tab1'!B4:E7", "'Tab2'!B4:E7")

    Returns:
        Mapping: range -> values (2D list)
    """
    try:
        service = connect_to_sheets(readonly=True)
        if service is None:
            return {}

        result = (
            service.spreadsheets()
            .values()
            .batchGet(spreadsheetId=spreadsheet_id, ranges=list(ranges))
            .execute()
        )

        out: Dict[str, List[List[str]]] = {}
        for vr in result.get("valueRanges", []) or []:
            r = vr.get("range", "")
            out[r] = vr.get("values", []) or []
        return out
    except Exception:
        return {}
