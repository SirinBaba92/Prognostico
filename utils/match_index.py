"""
Match Index / Navigator helpers

Builds lightweight metadata for matches (country/league/teams) for fast navigation UI.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional

import streamlit as st

from data.google_sheets import batch_get_worksheet_values_ranges_by_id


_COUNTRY_FLAG_OVERRIDES: Dict[str, str] = {
    # If you ever want to force a specific emoji for a label, add it here.
    # NOTE: We prefer widely supported country flags (e.g., 🇬🇧 instead of the England sub-flag).
    "England": "🇬🇧",
    "United Kingdom": "🇬🇧",
    "UK": "🇬🇧",
}

_COUNTRY_TO_ISO2: Dict[str, str] = {
    # Germany
    "deutschland": "DE",
    "germany": "DE",
    # UK / Home Nations (fallback to GB for compatibility)
    "england": "GB",
    "grossbritannien": "GB",
    "vereinigtes koenigreich": "GB",
    "united kingdom": "GB",
    "uk": "GB",
    "scotland": "GB",
    "wales": "GB",
    # Europe (common)
    "italien": "IT",
    "italy": "IT",
    "spanien": "ES",
    "spain": "ES",
    "frankreich": "FR",
    "france": "FR",
    "niederlande": "NL",
    "netherlands": "NL",
    "belgien": "BE",
    "belgium": "BE",
    "oesterreich": "AT",
    "osterreich": "AT",
    "austria": "AT",
    "schweiz": "CH",
    "switzerland": "CH",
    "portugal": "PT",
    "tuerkei": "TR",
    "turkei": "TR",
    "turkey": "TR",
    "griechenland": "GR",
    "greece": "GR",
    "daenemark": "DK",
    "danemark": "DK",
    "denmark": "DK",
    "schweden": "SE",
    "sweden": "SE",
    "norwegen": "NO",
    "norway": "NO",
    "finnland": "FI",
    "finland": "FI",
    "polen": "PL",
    "poland": "PL",
    "tschechien": "CZ",
    "czech republic": "CZ",
    "tchechien": "CZ",
    "slowakei": "SK",
    "slovakia": "SK",
    "slowenien": "SI",
    "slovenia": "SI",
    "ungarn": "HU",
    "hungary": "HU",
    "rumaenien": "RO",
    "rumanien": "RO",
    "romania": "RO",
    "bulgarien": "BG",
    "bulgaria": "BG",
    "kroatien": "HR",
    "croatia": "HR",
    "serbien": "RS",
    "serbia": "RS",
    "bosnien": "BA",
    "bosnia": "BA",
    "montenegro": "ME",
    "albanien": "AL",
    "albania": "AL",
    "nordmazedonien": "MK",
    "north macedonia": "MK",
    "irland": "IE",
    "ireland": "IE",
    "island": "IS",
    "iceland": "IS",
    "estland": "EE",
    "estonia": "EE",
    "lettland": "LV",
    "latvia": "LV",
    "litauen": "LT",
    "lithuania": "LT",
    "ukraine": "UA",
    "russland": "RU",
    "russia": "RU",
    "weissrussland": "BY",
    "belarus": "BY",
    "georgien": "GE",
    "georgia": "GE",
    "armenien": "AM",
    "armenia": "AM",
    "aserbaidschan": "AZ",
    "azerbaijan": "AZ",
    "israel": "IL",
    "zypern": "CY",
    "cyprus": "CY",
    "malta": "MT",
    "luxemburg": "LU",
    "luxembourg": "LU",
    # Americas (common)
    "usa": "US",
    "united states": "US",
    "vereinigte staaten": "US",
    "kanada": "CA",
    "canada": "CA",
    "mexiko": "MX",
    "mexico": "MX",
    "brasilien": "BR",
    "brazil": "BR",
    "argentinien": "AR",
    "argentina": "AR",
    "chile": "CL",
    "kolumbien": "CO",
    "colombia": "CO",
    "uruguay": "UY",
    "peru": "PE",
    # Africa (common)
    "marokko": "MA",
    "morocco": "MA",
    "aegypten": "EG",
    "egypt": "EG",
    "tunesien": "TN",
    "tunisia": "TN",
    "algerien": "DZ",
    "algeria": "DZ",
    "ghana": "GH",
    "nigeria": "NG",
    "senegal": "SN",
    "suedafrika": "ZA",
    "south africa": "ZA",
    "cote divoire": "CI",
    "elfenbeinkueste": "CI",
    # Asia / Oceania (common)
    "japan": "JP",
    "china": "CN",
    "su Korea": "KR",
    "suedkorea": "KR",
    "south korea": "KR",
    "australien": "AU",
    "australia": "AU",
    "neuseeland": "NZ",
    "new zealand": "NZ",
}


def _normalize_country_key(s: str) -> str:
    s = (s or "").strip().lower()
    # German umlauts + ß
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    # Strip accents
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    # Keep basic chars
    s = re.sub(r"[^a-z0-9\s\-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _iso2_to_flag(iso2: str) -> str:
    iso2 = (iso2 or "").strip().upper()
    if len(iso2) != 2 or not iso2.isalpha():
        return "🌍"
    # Regional indicator symbols
    return chr(ord("🇦") + (ord(iso2[0]) - ord("A"))) + chr(ord("🇦") + (ord(iso2[1]) - ord("A")))


def get_flag_emoji(country: str) -> str:
    country = (country or "").strip()
    if not country:
        return "🌍"

    # Explicit overrides first (exact match)
    if country in _COUNTRY_FLAG_OVERRIDES:
        return _COUNTRY_FLAG_OVERRIDES[country]

    key = _normalize_country_key(country)
    iso2 = _COUNTRY_TO_ISO2.get(key)

    # Also support when the sheet already provides ISO codes (e.g., "DE", "GB")
    if not iso2 and len(key) == 2 and key.isalpha():
        iso2 = key.upper()

    return _iso2_to_flag(iso2) if iso2 else "🌍"


def extract_country_league(competition: str) -> Tuple[str, str]:
    """
    Expected format (from user): "Land - Liga - Spieltag"
    We handle small variations and return ("Andere", "Unbekannt") fallback.
    """
    comp = (competition or "").strip()
    if not comp:
        return ("Andere", "Unbekannt")

    # Normalize separators
    comp = comp.replace("–", "-").replace("—", "-")
    parts = [p.strip() for p in comp.split("-") if p.strip()]

    if len(parts) >= 2:
        country = parts[0]
        league = parts[1]
        return (country or "Andere", league or "Unbekannt")

    # Try "Country: League" style
    if ":" in comp:
        left, right = comp.split(":", 1)
        country = left.strip()
        league = right.strip()
        if country and league:
            return (country, league)

    return ("Andere", comp)


def parse_tab_teams(tab_name: str) -> Tuple[str, str]:
    """
    Tab names often look like:
    '118_Le Mans FC vs USL Dunkerque'
    or 'Le Mans FC vs USL Dunkerque'
    """
    name = (tab_name or "").strip()
    name = re.sub(r"^\d+\s*[_-]\s*", "", name)  # remove leading index
    if " vs " in name:
        a, b = name.split(" vs ", 1)
        return a.strip(), b.strip()
    if " - " in name:
        a, b = name.split(" - ", 1)
        return a.strip(), b.strip()
    return name, ""


def _extract_field(match_text: str, field: str) -> str:
    """
    Extracts 'Wettbewerb:' / 'Datum:' / 'Anstoß:' lines from raw sheet text.
    Works with different cases.
    """
    if not match_text:
        return ""
    # raw text can contain tabs; we just scan lines
    lines = [ln.strip() for ln in match_text.splitlines() if ln.strip()]
    field_low = field.lower()
    for ln in lines:
        if ln.lower().startswith(field_low):
            return ln.split(":", 1)[1].strip() if ":" in ln else ""
    return ""


@st.cache_data(ttl=300)
def build_match_index(spreadsheet_id: str, match_tabs: Tuple[str, ...]) -> List[Dict]:
    """
    Builds lightweight metadata per match tab for the navigation UI.

    PERFORMANCE: uses ONE Sheets API batchGet call to read only the stable header cells (B4:E7)
    from ALL match tabs.
    """
    if not spreadsheet_id or not match_tabs:
        return []

    ranges = tuple([f"'{tab}'!B4:E7" for tab in match_tabs])
    range_map = batch_get_worksheet_values_ranges_by_id(spreadsheet_id, ranges)

    def first_non_empty(row: List[str]) -> str:
        for v in row or []:
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    def last_non_empty(row: List[str]) -> str:
        for v in reversed(row or []):
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    index: List[Dict] = []
    for tab in match_tabs:
        key = f"'{tab}'!B4:E7"
        vals = range_map.get(key, []) or []

        home = away = match_date = competition = kickoff = ""

        if len(vals) >= 1:
            row0 = vals[0] or []
            # B4:C4 is home (merged), D4:E4 is away (merged)
            # Depending on merge behavior, Google may return only one cell, or both.
            home = first_non_empty(row0[:2] if len(row0) >= 2 else row0)
            away = last_non_empty(row0[2:] if len(row0) >= 3 else row0)

        if len(vals) >= 2:
            match_date = first_non_empty(vals[1] or [])

        if len(vals) >= 3:
            competition = first_non_empty(vals[2] or [])

        if len(vals) >= 4:
            kickoff = first_non_empty(vals[3] or [])

        if not (home and away):
            ph, pa = parse_tab_teams(tab)
            home = home or ph
            away = away or pa

        country, league = extract_country_league(competition)

        index.append(
            {
                "tab": tab,
                "home": home,
                "away": away,
                "competition": competition,
                "country": country,
                "league": league,
                "flag": get_flag_emoji(country),
                "kickoff": kickoff,
                "date": match_date,
            }
        )

    return index

def group_matches_by_country_league(match_index: List[Dict]) -> Dict[str, Dict[str, List[Dict]]]:
    grouped: Dict[str, Dict[str, List[Dict]]] = {}
    for m in match_index:
        country = (m.get("country") or "Andere").strip() or "Andere"
        league = (m.get("league") or "Unbekannt").strip() or "Unbekannt"
        grouped.setdefault(country, {}).setdefault(league, []).append(m)
    return grouped