# Fix: Skalierungs-Bug in `data/supabase_mapper.py`

Nur dieser eine Fix, nichts anderes -- kein neues Modell, keine UI-Änderung.

## Problem

Der Scraper schreibt bestimmte FootyStats-Metriken als rohe Prozentzahl
(z. B. `15.4`) in `footystats_match_stats.value`. Der Rest des Tools (alter
Sheets-Parser, `analysis/match_analysis.py`) erwartet an diesen Stellen aber
0-1-Brüche (`0.154`) und multipliziert selbst mit 100, wo eine Prozentzahl
gebraucht wird.

**Betroffene Metriken:** `btts`, `cs`, `fts`, `shots_conversion_rate`, `avg_possession`
→ landen in `TeamStats` als `btts_yes_overall`/`_ha`, `cs_yes_overall`/`_ha`,
`fts_yes_overall`/`_ha`, `conversion_rate`, `possession`.

**Bestätigt per direkter DB-Abfrage** (SQL siehe weiter oben im Chat):
`avg_possession` Ø 50.7, `shots_conversion_rate` Ø 15.4, `btts` Ø 64.6 --
eindeutig 0-100, nicht 0-1.

**Konkreter Effekt:** `apply_conversion_adjustment()` in
`analysis/match_analysis.py` prüft `conversion_rate > 14`. Mit dem
unkorrigierten Wert (~15.4 * 100 = 1540) ist das **immer** wahr -- jedes
Spiel bekommt seit der Supabase-Migration denselben ×1.10-μ-Boost,
unabhängig von den tatsächlichen Team-Daten. Vermutlich ähnlich bei den
`cs_rates`-Schwellenwerten in derselben Funktion.

## Fix

`data/supabase_mapper.py`, Funktion `_apply_footystats()`: die betroffenen
Metriken werden jetzt beim Mappen zentral durch 100 geteilt -- korrigiert für
jeden Verbraucher (Kaskade, künftige Modelle), nicht nur punktuell an einer
Stelle.

## Diff (zur Kontrolle, exakt das und nichts anderes wurde geändert)

```diff
+ # Metriken, die der Scraper als rohe Prozentzahl (0-100) in
+ # footystats_match_stats.value schreibt, waehrend der Rest des Tools (alter
+ # data/parser.py, analysis/match_analysis.py) durchgaengig 0-1-Brueche erwartet.
+ # Bestaetigt per direkter DB-Abfrage: avg_possession Ø 50.7, shots_conversion_rate
+ # Ø 15.4, btts Ø 64.6 -- alles klar 0-100, nicht 0-1.
+ _PERCENTAGE_METRICS_NEEDING_NORMALIZATION = {"btts", "cs", "fts", "shots_conversion_rate", "avg_possession"}

  def _apply_footystats(...):
      ...
+         if value is not None and metric in _PERCENTAGE_METRICS_NEEDING_NORMALIZATION:
+             value = value / 100
+
          if metric in _FOOTYSTATS_SCOPED_METRICS:
              ...
```

## Einbauen & lokal testen

```bash
cp data/supabase_mapper.py ~/Desktop/.../sportwetten-analyse-main/data/supabase_mapper.py
streamlit run app.py
```

Ein Spiel analysieren, das du vorher schon mal analysiert hattest (Cache ggf.
über den Refresh-Button umgehen). Die μ-Werte / Prozentangaben sollten sich
jetzt spürbar ändern -- vor allem bei Teams mit `conversion_rate` nah an oder
über der 14%-Schwelle sollte der bisher immer greifende ×1.10-Boost jetzt
nicht mehr bei jedem Spiel auftreten.

**Quick-Check zur Bestätigung:** in einer Python-Konsole im Projektordner:

```python
from data.supabase_client import get_full_match_bundle
from data.supabase_mapper import map_bundle_to_match_data

bundle = get_full_match_bundle("<irgendeine match_id>")
match = map_bundle_to_match_data(bundle)
print(match.home_team.conversion_rate)  # sollte jetzt z.B. 0.154 sein, nicht 15.4
print(match.home_team.possession)       # sollte z.B. 0.52 sein, nicht 52.0
```
