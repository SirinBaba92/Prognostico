"""
Selbststaendiger Check: bestaetigt, dass der Skalierungs-Fix greift.
Holt sich automatisch ein echtes Match aus der DB -- keine match_id von Hand noetig.

Ausfuehren im Projektordner (mit aktiver .venv):
    python3 check_scale.py
"""

from data.supabase_client import get_available_dates, get_match_index_for_date, get_full_match_bundle
from data.supabase_mapper import map_bundle_to_match_data

dates = get_available_dates()
if not dates:
    print("Keine Daten in der DB gefunden -- Supabase-Verbindung/Zugangsdaten pruefen.")
    raise SystemExit(1)

match = None
for d in dates:
    index = get_match_index_for_date(d)
    if index:
        match_id = index[0]["match_id"]
        label = f"{index[0]['home']} vs {index[0]['away']}"
        bundle = get_full_match_bundle(match_id)
        if bundle:
            match = map_bundle_to_match_data(bundle)
            break

if match is None:
    print("Kein vollstaendiges Match gefunden.")
    raise SystemExit(1)

print(f"Test-Match: {label} ({d})\n")
print(f"conversion_rate (Heim): {match.home_team.conversion_rate}   -- erwartet: ~0.0-0.3, NICHT 0-30")
print(f"possession (Heim):      {match.home_team.possession}   -- erwartet: ~0.3-0.7, NICHT 30-70")
print(f"btts_yes_ha (Heim):     {match.home_team.btts_yes_ha}   -- erwartet: ~0.3-0.8, NICHT 30-80")
print(f"cs_yes_ha (Heim):       {match.home_team.cs_yes_ha}   -- erwartet: ~0.0-0.5, NICHT 0-50")

if match.home_team.conversion_rate and match.home_team.conversion_rate > 1:
    print("\n⚠️  WERT SIEHT NOCH UNSKALIERT AUS (>1) -- Fix greift vermutlich noch nicht.")
    print("    Pruefe: liegt die ersetzte supabase_mapper.py wirklich im richtigen Ordner?")
else:
    print("\n✅ Werte sehen korrekt skaliert aus (0-1-Bereich) -- Fix greift.")
