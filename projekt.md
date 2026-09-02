# Analyse-Tool — Migration auf Supabase (Referenzdokument)

> Zweck: Referenzdokument für die Migration des bestehenden Sportwetten-Analyse-Tools
> (Streamlit) von Google Sheets als Datenquelle auf die neue, normalisierte
> Supabase/PostgreSQL-Datenbank aus dem "Football Stats Scraper"-Projekt.
> Schema-Referenz: `docs/database_schema.md` (Flashscore V1.0) + Ergänzungen unten
> (footystats_match_stats, tatsächlich in Supabase vorgefunden).

---

## Ausgangslage

Das Analyse-Tool (`sportwetten-analyse-main`) ist eine Streamlit-App, die bisher:
- Matches aus einem Google-Drive-Ordner liest (ein Spreadsheet pro Tag, benannt `DD.MM.YYYY`)
- pro Match ein Worksheet-Tab liest (`data/google_sheets.py`)
- den rohen Tab-separierten Text über Zeilen-Pattern-Matching parst (`data/parser.py`,
  `DataParser`) in `MatchData`/`TeamStats`/`H2HResult` (`data/models.py`)
- darauf ML-Modelle, Risiko-Scoring und Bankroll-Management aufbaut (`analysis/`, `ml/`, `models/`)

Ziel: Diese Kette durch direkten, read-only Supabase-Zugriff ersetzen — ohne
Text-Parsing, mit stabilen IDs statt Anzeige-Strings als Schlüssel.

---

## Architekturentscheidungen (fix)

1. **Direkter Supabase-Zugriff aus Streamlit**, kein separater API-Layer.
   Begründung: Single-Consumer-App, rein lesend, kein Mehrwert durch eine
   Zwischenschicht. Kann bei Bedarf später ergänzt werden, falls ein zweiter
   Consumer hinzukommt.

2. **Auth: Anon-Key + RLS-Read-Policies**, nicht der Service-Role-Key.
   Begründung: Geringstmögliche Rechte — die App liest nur, der Scraper schreibt
   weiterhin mit dem Service-Role-Key (umgeht RLS). Policies wurden für alle
   11 Tabellen angelegt (`FOR SELECT TO anon USING (true)`), auch für aktuell
   ungenutzte Tabellen (`lineups`, `team_aliases`), da Aufstellungen/Verletzungen
   künftig in die Analyse einfließen sollen.
   Secrets-Struktur: `st.secrets["supabase"]["url"]` / `st.secrets["supabase"]["anon_key"]`
   (analog zum bestehenden `st.secrets["gcp_service_account"]`-Pattern).

3. **`match_id` (UUID, `matches.match_id`) als einziger interner Identifikator**,
   ersetzt den bisherigen Sheet-Tab-Namen überall (Session-State-Keys, Cache-Keys,
   Bulk-Analyse-Loop). Ein lesbarer String ("Bayern vs. Dortmund, 18:30") existiert
   weiterhin, aber nur noch als abgeleitetes Anzeige-Label, nie als Schlüssel.
   Begründung: Tab-Namen sind reine UI-Artefakte aus Google Sheets und können
   kollidieren; `match_id` ist der im Scraper-Projekt bereits etablierte stabile Anker.

4. **Tagesbasierte Navigation bleibt unverändert** (Datums-Picker → Matchliste),
   nur die Quelle wechselt von Ordner/Spreadsheet-Lookup zu einer Query auf
   `matches.match_date`.

5. **Validierung bleibt strikt (keine Lockerung)**: Fehlt für ein Match FootyStats
   (z. B. Competition nicht im Mapping), gilt es weiterhin als unvollständig,
   analog zur bisherigen `validate_match_data()`-Logik. Grund: Es werden ohnehin
   nur Tage/Competitions gescraped, für die vollständige Daten zu erwarten sind.

6. **Competition-Label** für UI/`MatchData.competition`: `f"{country} - {name}"`
   (z. B. `"Germany - Bundesliga"`), konsistent zur bisherigen Navigator-Gruppierung
   nach Land/Liga.

---

## `footystats_match_stats` — tatsächliche Struktur (per Query verifiziert)

Long-Format, nicht Teil von `docs/database_schema.md` (das deckt nur V1.0/Flashscore ab):

| Spalte | Typ |
|---|---|
| id | uuid |
| match_id | uuid (FK → matches.id) |
| team_id | uuid (FK → teams.id) |
| metric | text |
| scope | text, nullable |
| value | numeric |

**Vorkommende `metric`-Werte:**
- Mit `scope` (`overall`/`home`/`away`): `avg`, `btts`, `conceded`, `cs`, `fts`, `ppg`, `scored`, `xg`, `xga`
- Ohne `scope` (NULL): `avg_possession`, `shots_conversion_rate`, `shots_off_target_per_match`,
  `shots_on_target_per_match`, `shots_per_match`

**Wichtig:** "Over/Under 2,5 Goals" (Overall/Home-Away) ist **keine** FootyStats-Metrik,
sondern kommt aus Flashscore → `table_stats`, `section = 'over_under'`
(`over_count`/`under_count`, siehe `database_schema.md`).

---

## Mapping: DB → `TeamStats`

### Aus `table_stats` (Flashscore)

| `TeamStats`-Feld(er) | `section` | `scope` |
|---|---|---|
| position, games, wins, draws, losses, goals_for/against, goal_diff, points | `standings` | `overall` |
| form_points, form_goals_for, form_goals_against | `form` | `overall` |
| ha_points, ha_goals_for, ha_goals_against | `form` | `home` (Heimteam) / `away` (Auswärtsteam) |
| over25_pct_overall *(neu, berechnet: over_count / (over_count+under_count))* | `over_under` | `overall` |
| over25_pct_ha *(neu, gleiche Berechnung)* | `over_under` | `home` (Heimteam) / `away` (Auswärtsteam) |

### Aus `footystats_match_stats`

| `metric` | `scope=overall` → | `scope=ha` → |
|---|---|---|
| ppg | ppg_overall | ppg_ha |
| avg | avg_goals_match | avg_goals_match_ha |
| scored | goals_scored_per_match | goals_scored_per_match_ha |
| conceded | goals_conceded_per_match | goals_conceded_per_match_ha |
| btts | btts_yes_overall | btts_yes_ha |
| cs | cs_yes_overall | cs_yes_ha |
| fts | fts_yes_overall | fts_yes_ha |
| xg | xg_for | xg_for_ha |
| xga | xg_against | xg_against_ha |

| `metric` (scope-los) | → `TeamStats`-Feld |
|---|---|
| shots_per_match | shots_per_match |
| shots_on_target_per_match | shots_on_target |
| shots_off_target_per_match | shots_off_target *(neu)* |
| shots_conversion_rate | conversion_rate |
| avg_possession | possession |

**"_ha"-Semantik** (wichtig, aus Sheet-Struktur bestätigt): Für das Heimteam wird
immer `scope='home'` verwendet, für das Auswärtsteam `scope='away'` — nicht ein
gemeinsamer Wert für beide Teams. Gilt identisch für `table_stats.form`/`over_under`
und alle gescopten `footystats_match_stats`-Metriken.

---

## Neue Felder in `TeamStats` (Erweiterung ggü. Sheet-Ära)

Zwei Werte existierten im alten Google-Sheet, wurden vom bisherigen `DataParser`
aber nie geparst (totes Feld) bzw. fehlten komplett in `TeamStats`. Aufgenommen,
weil eine künftige Überarbeitung der Analyse-Logik geplant ist:

- `shots_off_target: float` — aus `footystats_match_stats`, metric `shots_off_target_per_match`
- `over25_pct_overall: float` — aus `table_stats`, section `over_under`, scope `overall`
- `over25_pct_ha: float` — aus `table_stats`, section `over_under`, scope home/away

---

## Aktueller Stand der Migration

**✅ Migration abgeschlossen und lokal end-to-end getestet (24.08.2026).**

Fertig:
- `data/supabase_client.py` — Verbindung + Query-Funktionen:
  `get_available_dates()`, `get_match_index_for_date()`, `get_full_match_bundle()`
- `data/supabase_mapper.py` — `map_bundle_to_match_data()`, ersetzt `DataParser`
- `TeamStats`-Erweiterung um die drei neuen Felder (siehe oben)
- `app.py`: komplette Tab-1-Navigation + Analyse-Flow auf Supabase umgestellt
  (Datums-Picker, Matchliste/Navigator, Einzelanalyse, Bulk-Analyse, Rohdaten-Expander,
  historisches Ergebnis eintragen) — `match_id` durchgängig als Schlüssel
  (Session State, Cache-Keys, Bulk-Loop) statt vormals `selected_tab`
- `ui/results_display.py`: ML-Inline-Prognose lädt jetzt über `get_full_match_bundle`
  + `map_bundle_to_match_data` (`result['_match_id']` statt `_sheet_id`/`_selected_tab`)
- `ui/sheets_ml_integration.py` + `ui/ml_predictions_ui.py`: ML Predictions Tab (Tab 6)
  nutzt `match_id` aus `st.session_state.selected_match_id`
- `models/export_to_sheets.py`: interner ML-Re-Fetch-Block auf Supabase umgestellt;
  das eigentliche Export-Ziel (`EXPORT_SHEET_ID`, Wettquoten-Tipps-Tracking-Sheet)
  bleibt bewusst Google Sheets — das ist ein Export-Ziel, keine Match-Datenquelle,
  und war nie Teil dieser Migration
- `requirements.txt`: `supabase==2.3.4` + `gotrue==2.8.1` (siehe Dependency-Pinning unten)
- RLS-Policies + `GRANT SELECT` für `anon` auf allen 11 Tabellen (siehe unten)
- `st.secrets["supabase"]` lokal eingetragen

**Bewusst nicht migriert / außerhalb des Scopes:**
- `EXPORT_SHEET_ID` / `models/export_to_sheets.py`: Export-*Ziel* bleibt Google Sheets
- `get_tracking_sheet_id()` (`ui/sidebar.py`, `ui/historical_data_ui.py`,
  `ui/extended_data_entry.py`, `models/tracking.py`): Bankroll-/Ergebnis-Tracking-Sheet,
  komplett separates Feature, nie Teil dieser Migration
- Keine Übernahme historischer Matches aus Google Sheets — DB startet "leer" bis
  auf bereits gescrapte Tage, alte Sheets-Daten werden nicht nachimportiert
- `data/google_sheets.py`, `data/parser.py` bleiben im Repo (werden noch von den
  beiden obigen Tracking-Stellen genutzt), aber sind für die Match-Analyse selbst
  nicht mehr im Einsatz

**Auf dem Horizont:**
- Gemeinsame Überarbeitung der Analyse-Logik (`analysis/`), im Licht der neu
  verfügbaren Felder (`over25_pct_overall`/`_ha`, `shots_off_target`) und der
  zusätzlichen Rohdaten aus `lineups` (Aufstellungen/Verletzungen)

---

## Dependency-Pinning: `supabase` + `httpx` (macOS-Umgebung)

Beim lokalen Setup traten zwei aufeinanderfolgende Versionskonflikte auf, gelöst wie folgt:

1. **`httpx`-Konflikt**: `python-telegram-bot==20.7` pinnt `httpx~=0.25.2` fest;
   die neueste `supabase`-Version erwartet über `gotrue` ein neueres `httpx` (≥0.26,
   `proxy`-Kwarg). Da nur eine `httpx`-Version im venv koexistieren kann, wurde
   `supabase==2.3.4` gepinnt (letzte Version, die mit `httpx 0.25.x` kompatibel ist).
   Nach dem Pin: `pip install -r requirements.txt --upgrade` (ohne `--no-deps`),
   damit `realtime`/`postgrest`/`storage3`/`supafunc` konsistent mitgezogen werden.

2. **`gotrue`-Bug**: Auch mit `supabase==2.3.4` blieb `gotrue==2.9.1` installiert
   (erfüllt dessen Versionsspanne) und wirft beim Client-Aufbau
   `Client.__init__() got an unexpected keyword argument 'proxy'` — ein bekannter
   Bug in `gotrue 2.9.1` selbst (nicht `httpx`-Version-abhängig,
   [supabase-py #949](https://github.com/supabase/supabase-py/issues/949)).
   Fix: `gotrue==2.8.1` zusätzlich explizit in `requirements.txt` gepinnt.

**Finale, verifiziert funktionierende Kombination:**
`supabase==2.3.4`, `gotrue==2.8.1`, `httpx~=0.25.2` (über `python-telegram-bot`),
`postgrest==0.15.1`, `realtime==1.0.6`, `storage3==0.7.7`, `supafunc==0.3.3`,
`websockets==12.0`.

---

## Datumsformat-Fix (`data/supabase_mapper.py`)

Beim Dokumentieren aufgefallen: Supabase liefert `matches.match_date` im ISO-Format
`YYYY-MM-DD`. `MatchData.date` wurde ursprünglich unkonvertiert durchgereicht — das
hätte `models/export_to_sheets.py` gebrochen, das `result["match_info"]["date"]`
im Format `DD.MM.YYYY` erwartet, um den passenden Tab im Export-Tracking-Sheet zu
finden (Tab-Namen dort sind weiterhin `DD.MM.YYYY`, unabhängig von der
Match-Datenquelle). Fix: `map_bundle_to_match_data()` konvertiert `match_date` jetzt
über einen neuen Helper `_to_ddmmyyyy()` nach `DD.MM.YYYY`, konsistent mit dem
Rest der App. `H2HResult.date` bleibt bewusst im nativen `YYYY-MM-DD` — wird an
keiner Stelle im Code geparst oder formatabhängig verwendet.

---

## Bugfix während der Migration (nicht migrationsbedingt)

`ui/results_display.py::display_results()` hatte vier fest verdrahtete Widget-Keys
(`export_btn_simple_rd`, `exp_home_rd`, `exp_away_rd`, `export_btn_with_result_rd`).
Fiel bisher nicht auf, da die Funktion nur einmal pro Seite aufgerufen wurde
(Einzelanalyse). Bei der Bulk-Analyse (mehrere Aufrufe derselben Funktion auf einer
Seite) führte das zu `StreamlitDuplicateElementKey`. Fix: neuer Parameter
`key_suffix: str = ""`, alle vier Keys damit parametrisiert; `app.py` übergibt in
der Bulk-Ergebnisliste `key_suffix=f"_{item['match_id']}"`.

---

## Supabase RLS + Grants (bereits durchgeführt)

RLS war auf allen 11 Tabellen aktiviert, aber ohne Policies (Anon-Key hatte
faktisch keinen Lesezugriff). Angelegt: `SELECT`-Policies für `anon` auf
`teams`, `team_aliases`, `competitions`, `matches`, `lineups`, `odds_1x2`,
`odds_over_under`, `odds_btts`, `h2h_entries`, `table_stats`,
`footystats_match_stats`.

**Zusätzlich nötig, per Live-Test entdeckt:** RLS-Policies allein reichen in
PostgreSQL/Supabase nicht — es braucht zusätzlich ein einfaches `GRANT SELECT`
auf Tabellenebene für die Rolle `anon` (RLS filtert *welche Zeilen* sichtbar sind,
`GRANT` regelt *ob überhaupt* zugegriffen werden darf). Bei über SQL/Skript
angelegten Tabellen wird das von Supabase nicht automatisch gesetzt (anders als
bei über die Weboberfläche erstellten Tabellen). `GRANT SELECT ON <table> TO anon;`
wurde für alle 11 Tabellen nachgeholt.

Schreibrechte unverändert (Service-Role-Key beim Scraper, umgeht RLS).
