"""
Extended Data Entry UI-Komponente
"""

import streamlit as st
from data.google_sheets import connect_to_sheets, get_tracking_sheet_id
from data.models import ExtendedMatchData


def show_extended_data_entry_ui():
    """
    Zeigt UI für Eingabe von erweiterten Match-Daten (für Phase 4 ML)
    """
    st.subheader("📊 Erweiterte Match-Daten (Phase 4)")

    st.info(
        "💡 Diese Daten werden für das erweiterte ML-Modell benötigt und sollten nach dem Spiel eingetragen werden"
    )

    # Form für Extended Data
    with st.form("extended_data_form", clear_on_submit=True):
        st.markdown("### Match-Identifikation")
        match_id = st.text_input(
            "Match ID / Beschreibung",
            placeholder="z.B. Bayern vs Dortmund 2024-01-15",
        )

        st.markdown("---")
        st.markdown("### Halbzeit-Ergebnis")
        col1, col2 = st.columns(2)
        with col1:
            ht_home = st.number_input("Halbzeit Heim-Tore", 0, 10, 0)
        with col2:
            ht_away = st.number_input("Halbzeit Auswärts-Tore", 0, 10, 0)

        halftime_score = f"{ht_home}:{ht_away}"

        st.markdown("---")
        st.markdown("### Ballbesitz (%)")
        col1, col2 = st.columns(2)
        with col1:
            possession_home = st.slider("Ballbesitz Heim", 0, 100, 50)
        with col2:
            possession_away = 100 - possession_home
            st.metric("Ballbesitz Auswärts", f"{possession_away}%")

        st.markdown("---")
        st.markdown("### Schüsse")
        col1, col2 = st.columns(2)
        with col1:
            shots_home = st.number_input("Schüsse Heim", 0, 50, 10)
            shots_on_target_home = st.number_input(
                "Schüsse aufs Tor Heim", 0, shots_home, min(5, shots_home)
            )
        with col2:
            shots_away = st.number_input("Schüsse Auswärts", 0, 50, 8)
            shots_on_target_away = st.number_input(
                "Schüsse aufs Tor Auswärts", 0, shots_away, min(4, shots_away)
            )

        st.markdown("---")
        st.markdown("### Ecken")
        col1, col2 = st.columns(2)
        with col1:
            corners_home = st.number_input("Ecken Heim", 0, 30, 5)
        with col2:
            corners_away = st.number_input("Ecken Auswärts", 0, 30, 3)

        st.markdown("---")
        st.markdown("### Fouls")
        col1, col2 = st.columns(2)
        with col1:
            fouls_home = st.number_input("Fouls Heim", 0, 40, 10)
        with col2:
            fouls_away = st.number_input("Fouls Auswärts", 0, 40, 12)

        st.markdown("---")
        st.markdown("### Karten")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            yellow_home = st.number_input("Gelbe Heim", 0, 10, 2)
        with col2:
            yellow_away = st.number_input("Gelbe Auswärts", 0, 10, 3)
        with col3:
            red_home = st.number_input("Rote Heim", 0, 3, 0)
        with col4:
            red_away = st.number_input("Rote Auswärts", 0, 3, 0)

        st.markdown("---")
        st.markdown("### Auswechslungen")
        col1, col2 = st.columns(2)
        with col1:
            subs_home = st.number_input("Auswechslungen Heim", 0, 5, 3)
        with col2:
            subs_away = st.number_input("Auswechslungen Auswärts", 0, 5, 3)

        st.markdown("---")
        notes = st.text_area("Notizen (optional)", placeholder="Besondere Vorkommnisse")

        # Submit Button
        submitted = st.form_submit_button(
            "💾 Erweiterte Daten speichern", use_container_width=True
        )

        if submitted:
            if not match_id:
                st.error("❌ Bitte Match ID eingeben!")
            else:
                # Erstelle ExtendedMatchData Objekt
                extended_data = ExtendedMatchData(
                    match_id=match_id,
                    halftime_score=halftime_score,
                    possession_home=float(possession_home),
                    possession_away=float(possession_away),
                    shots_home=shots_home,
                    shots_away=shots_away,
                    shots_on_target_home=shots_on_target_home,
                    shots_on_target_away=shots_on_target_away,
                    corners_home=corners_home,
                    corners_away=corners_away,
                    fouls_home=fouls_home,
                    fouls_away=fouls_away,
                    yellow_cards_home=yellow_home,
                    yellow_cards_away=yellow_away,
                    red_cards_home=red_home,
                    red_cards_away=red_away,
                    substitutions_home=subs_home,
                    substitutions_away=subs_away,
                    notes=notes,
                )

                # Speichere zu Google Sheets
                sheet_id = get_tracking_sheet_id()
                if sheet_id:
                    try:
                        service = connect_to_sheets(readonly=False)
                        if service:
                            # Prüfe ob EXTENDED_DATA Sheet existiert
                            try:
                                service.spreadsheets().values().get(
                                    spreadsheetId=sheet_id, range="EXTENDED_DATA!A:A"
                                ).execute()
                            except:
                                # Erstelle Sheet mit Headers
                                body = {
                                    "requests": [
                                        {
                                            "addSheet": {
                                                "properties": {"title": "EXTENDED_DATA"}
                                            }
                                        }
                                    ]
                                }
                                service.spreadsheets().batchUpdate(
                                    spreadsheetId=sheet_id, body=body
                                ).execute()

                                headers = [
                                    "Match_ID",
                                    "Halftime",
                                    "Possession_Home",
                                    "Possession_Away",
                                    "Shots_Home",
                                    "Shots_Away",
                                    "ShotsOnTarget_Home",
                                    "ShotsOnTarget_Away",
                                    "Corners_Home",
                                    "Corners_Away",
                                    "Fouls_Home",
                                    "Fouls_Away",
                                    "Yellow_Home",
                                    "Yellow_Away",
                                    "Red_Home",
                                    "Red_Away",
                                    "Subs_Home",
                                    "Subs_Away",
                                    "Notes",
                                ]

                                body = {"values": [headers]}
                                service.spreadsheets().values().update(
                                    spreadsheetId=sheet_id,
                                    range="EXTENDED_DATA!A1:S1",
                                    valueInputOption="RAW",
                                    body=body,
                                ).execute()

                            # Füge Daten hinzu
                            values = [
                                [
                                    match_id,
                                    halftime_score,
                                    possession_home,
                                    possession_away,
                                    shots_home,
                                    shots_away,
                                    shots_on_target_home,
                                    shots_on_target_away,
                                    corners_home,
                                    corners_away,
                                    fouls_home,
                                    fouls_away,
                                    yellow_home,
                                    yellow_away,
                                    red_home,
                                    red_away,
                                    subs_home,
                                    subs_away,
                                    notes,
                                ]
                            ]

                            body = {"values": values}
                            service.spreadsheets().values().append(
                                spreadsheetId=sheet_id,
                                range="EXTENDED_DATA!A:S",
                                valueInputOption="RAW",
                                insertDataOption="INSERT_ROWS",
                                body=body,
                            ).execute()

                            st.success(f"✅ Erweiterte Daten für '{match_id}' gespeichert!")
                            st.balloons()

                    except Exception as e:
                        st.error(f"❌ Fehler beim Speichern: {e}")
                else:
                    st.warning("⚠️ Google Sheets nicht konfiguriert")
