"""
Supabase Verbindung und Query-Funktionen für das Analyse-Tool.
Ersetzt data/google_sheets.py als Datenquelle.

Zugriff: Anon-Key + RLS-Read-Policies (siehe docs/projekt.md).
Schreibzugriff bleibt beim Scraper (Service-Role-Key), hier nur Lesen.

Zeigt (seit 2026-08-30 wieder) auf das alte Football-Stats-Scraper-Projekt
(tatzhceycusngueroqod), da der aktuelle Scraper dorthin schreibt. Alle
Tabellen liegen dort im Standard-Schema `public`, daher kein
client.postgrest.schema(...)-Aufruf. Das neue flashscore-lib-Projekt
(core/stats-Schemas) bleibt unangetastet, bis dafür ein eigenes Tool
entsteht.
"""

from datetime import date
from typing import Dict, List, Optional

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase_client() -> Optional[Client]:
    """Erstellt (und cached) den Supabase-Client."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Fehler bei Supabase-Verbindung: {e}")
        return None


@st.cache_data(ttl=300)
def get_available_dates() -> List[date]:
    """
    Liefert alle Tage, für die mindestens ein Match in der DB existiert.
    Ersetzt list_daily_sheets_in_folder().
    """
    client = get_supabase_client()
    if client is None:
        return []

    resp = client.table("matches").select("match_date").execute()
    rows = resp.data or []
    dates = {r["match_date"] for r in rows if r.get("match_date")}
    return sorted(date.fromisoformat(d) for d in dates)


@st.cache_data(ttl=300)
def get_match_index_for_date(match_date: date) -> List[Dict]:
    """
    Liefert Navigator-Metadaten für alle Matches an einem Tag.
    Ersetzt build_match_index() (utils/match_index.py) — EIN DB-Query
    statt N einzelner Sheet-Reads.

    Rückgabe pro Match: match_id, home, away, competition, country, league, kickoff.
    (get_flag_emoji() aus utils/match_index.py bleibt unverändert nutzbar.)
    """
    client = get_supabase_client()
    if client is None:
        return []

    matches_resp = (
        client.table("matches")
        .select("match_id, home_team_id, away_team_id, competition_id, kickoff_time")
        .eq("match_date", match_date.isoformat())
        .execute()
    )
    matches = matches_resp.data or []
    if not matches:
        return []

    team_ids = sorted(
        {m["home_team_id"] for m in matches} | {m["away_team_id"] for m in matches}
    )
    comp_ids = sorted({m["competition_id"] for m in matches})

    teams_resp = client.table("teams").select("id, name").in_("id", team_ids).execute()
    teams_by_id = {t["id"]: t["name"] for t in (teams_resp.data or [])}

    comps_resp = (
        client.table("competitions")
        .select("id, name, country")
        .in_("id", comp_ids)
        .execute()
    )
    comps_by_id = {c["id"]: c for c in (comps_resp.data or [])}

    index: List[Dict] = []
    for m in matches:
        comp = comps_by_id.get(m["competition_id"], {})
        index.append(
            {
                "match_id": m["match_id"],
                "home": teams_by_id.get(m["home_team_id"], "?"),
                "away": teams_by_id.get(m["away_team_id"], "?"),
                "competition": f"{comp.get('country', '')} - {comp.get('name', '')}".strip(" -"),
                "country": comp.get("country", "Andere"),
                "league": comp.get("name", "Unbekannt"),
                "kickoff": (m.get("kickoff_time") or "")[:5],
            }
        )
    return index


@st.cache_data(ttl=300)
def get_full_match_bundle(match_id: str) -> Optional[Dict]:
    """
    Lädt alle für eine Analyse benötigten Rohdaten zu einem Match aus Supabase.
    Gibt ein Dict mit den rohen Tabellen-Rows zurück; das eigentliche Mapping
    auf MatchData/TeamStats übernimmt data/supabase_mapper.py.

    match_id: die externe UUID (matches.match_id), NICHT der technische PK.
    """
    client = get_supabase_client()
    if client is None:
        return None

    match_resp = (
        client.table("matches").select("*").eq("match_id", match_id).limit(1).execute()
    )
    if not match_resp.data:
        return None
    match_row = match_resp.data[0]
    internal_id = match_row["id"]  # technischer PK, FK-Ziel in allen Detail-Tabellen

    home_team_id = match_row["home_team_id"]
    away_team_id = match_row["away_team_id"]

    teams_resp = (
        client.table("teams")
        .select("*")
        .in_("id", [home_team_id, away_team_id])
        .execute()
    )
    teams_by_id = {t["id"]: t for t in (teams_resp.data or [])}

    comp_resp = (
        client.table("competitions")
        .select("*")
        .eq("id", match_row["competition_id"])
        .limit(1)
        .execute()
    )
    competition = (comp_resp.data or [{}])[0]

    table_stats_resp = (
        client.table("table_stats").select("*").eq("match_id", internal_id).execute()
    )
    footystats_resp = (
        client.table("footystats_match_stats")
        .select("*")
        .eq("match_id", internal_id)
        .execute()
    )
    odds_1x2_resp = (
        client.table("odds_1x2").select("*").eq("match_id", internal_id).execute()
    )
    odds_ou_resp = (
        client.table("odds_over_under").select("*").eq("match_id", internal_id).execute()
    )
    odds_btts_resp = (
        client.table("odds_btts").select("*").eq("match_id", internal_id).execute()
    )
    h2h_resp = (
        client.table("h2h_entries").select("*").eq("match_id", internal_id).execute()
    )

    h2h_rows = h2h_resp.data or []
    h2h_team_ids = sorted(
        {r["home_team_id"] for r in h2h_rows} | {r["away_team_id"] for r in h2h_rows}
    )
    if h2h_team_ids:
        h2h_teams_resp = (
            client.table("teams").select("id, name").in_("id", h2h_team_ids).execute()
        )
        h2h_teams_by_id = {t["id"]: t["name"] for t in (h2h_teams_resp.data or [])}
    else:
        h2h_teams_by_id = {}

    return {
        "match": match_row,
        "home_team": teams_by_id.get(home_team_id, {}),
        "away_team": teams_by_id.get(away_team_id, {}),
        "competition": competition,
        "table_stats": table_stats_resp.data or [],
        "footystats": footystats_resp.data or [],
        "odds_1x2": odds_1x2_resp.data or [],
        "odds_over_under": odds_ou_resp.data or [],
        "odds_btts": odds_btts_resp.data or [],
        "h2h_entries": h2h_rows,
        "h2h_teams_by_id": h2h_teams_by_id,
    }
