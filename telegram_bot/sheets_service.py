"""
Service: Google Sheets Zugriff ohne Streamlit-Abhängigkeit
Lädt Credentials aus Streamlit Secrets oder Umgebungsvariablen
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import date
import re

logger = logging.getLogger(__name__)

_credentials_dict = None


def _load_credentials() -> Optional[dict]:
    global _credentials_dict
    if _credentials_dict:
        return _credentials_dict

    # Option 1: Streamlit secrets (bevorzugt, da App in Streamlit läuft)
    try:
        import streamlit as st
        _credentials_dict = dict(st.secrets["gcp_service_account"])
        return _credentials_dict
    except Exception:
        pass

    logger.warning("Keine GCP Credentials gefunden")
    return None


def _get_folder_id() -> str:
    """Liest Folder ID aus Env-Variable oder Streamlit Secrets"""
    # Env-Variable hat Vorrang
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    if folder_id:
        return folder_id

    # Fallback: Streamlit Secrets
    try:
        import streamlit as st
        return st.secrets["prematch"]["folder_id"]
    except Exception:
        pass

    return ""


def _build_sheets_service():
    creds_dict = _load_credentials()
    if not creds_dict:
        return None
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        return build("sheets", "v4", credentials=creds)
    except Exception as e:
        logger.error(f"Sheets Service Fehler: {e}")
        return None


def _build_drive_service():
    creds_dict = _load_credentials()
    if not creds_dict:
        return None
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"Drive Service Fehler: {e}")
        return None


DATE_PATTERN = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


def list_available_dates() -> Dict[str, str]:
    """
    Gibt alle verfügbaren Datum-Sheets zurück.
    Returns: {'15.02.2025': '<spreadsheet_id>', ...}
    """
    folder_id = _get_folder_id()
    if not folder_id:
        logger.error("Keine Folder ID konfiguriert")
        return {}

    service = _build_drive_service()
    if not service:
        return {}

    try:
        q = (
            f"'{folder_id}' in parents "
            "and mimeType='application/vnd.google-apps.spreadsheet' "
            "and trashed=false"
        )
        result = service.files().list(q=q, fields="files(id,name)").execute()
        files = result.get("files", [])
        return {
            f["name"]: f["id"]
            for f in files
            if DATE_PATTERN.match(f["name"])
        }
    except Exception as e:
        logger.error(f"Drive list error: {e}")
        return {}


def list_tabs_in_sheet(spreadsheet_id: str) -> List[str]:
    """Gibt alle Tab-Namen eines Spreadsheets zurück"""
    service = _build_sheets_service()
    if not service:
        return []
    try:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        return [s["properties"]["title"] for s in meta.get("sheets", [])]
    except Exception as e:
        logger.error(f"List tabs error: {e}")
        return []


def read_sheet_tab(spreadsheet_id: str, tab_name: str) -> str:
    """Liest einen Tab und gibt ihn als Text zurück (kompatibel mit DataParser)"""
    service = _build_sheets_service()
    if not service:
        return ""
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=tab_name)
            .execute()
        )
        rows = result.get("values", [])
        return "\n".join("\t".join(row) for row in rows)
    except Exception as e:
        logger.error(f"Read sheet error: {e}")
        return ""


def get_todays_sheet_id() -> Optional[Tuple[str, str]]:
    """Gibt (date_str, spreadsheet_id) für heute zurück oder None"""
    today = date.today().strftime("%d.%m.%Y")
    dates = list_available_dates()
    if today in dates:
        return today, dates[today]
    return None
