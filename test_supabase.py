import streamlit as st
from datetime import date
from data.supabase_client import (
    get_available_dates,
    get_match_index_for_date,
    get_full_match_bundle,
)
from data.supabase_mapper import map_bundle_to_match_data

dates = get_available_dates()
st.write("Verfügbare Tage:", dates)

target_date = date(2026, 8, 24)
index = get_match_index_for_date(target_date)
st.write(f"Matches am {target_date}:", index)

if index:
    bundle = get_full_match_bundle(index[0]["match_id"])
    match_data = map_bundle_to_match_data(bundle)
    st.write(match_data)
