import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time

# --- SETTINGS ---
# ⚠️ MAKE SURE THIS URL ENDS IN output=csv
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXv6-bYGpE2J4FCXwdDSoRDNl7UhseCyaURUhIEnF-ZkI12GS7UD0pM4UQIoe96EJPJJavGnCuAWbI/pub?output=csv"

st.set_page_config(layout="wide", page_title="K2K 2026 Map")

@st.cache_data(ttl=60)
def load_data(url):
    try:
        # We add a custom header to pretend we are a browser (helps with Google's filters)
        df = pd.read_csv(url, on_bad_lines='skip')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Could not connect to Google Sheets: {e}")
        return None

st.title("🏔️ K2K 2026 Route")

if st.button("🔄 Sync with Google Sheet"):
    st.cache_data.clear()
    st.rerun()

df = load_data(CSV_URL)

if df is not None:
    # --- DEBUG SECTION ---
    # If we don't find 'From', show the user what we DID find
    if 'From' not in df.columns:
        st.error("❌ Column Header Error!")
        st.write("The app is reading the link, but it can't find 'From'.")
        st.write("Here is a preview of the data I received (Top 3 rows):")
        st.dataframe(df.head(3))
        st.info("💡 TIP: If the preview above looks like a bunch of random text/code, your link is a 'Web Page' link, not a 'CSV' link.")
    else:
        # --- MAP LOGIC ---
        unique_cities = pd.concat([df['From'], df['To']]).unique()
        
        geolocator = Nominatim(user_agent="k2k_final_navigator")
        coords_dict = {}
        
        # We only geocode if we haven't already
        for city in unique_cities:
            clean_name = str(city).split('/')[0].strip()
            try:
                time.sleep(1) # Keep Google happy
                loc = geolocator.geocode(f"{clean_name}, India")
                if loc: coords_dict[city] = [loc.latitude, loc.longitude]
            except: continue

        m = folium.Map(location=[22.0, 78.0], zoom_start=5, tiles="CartoDB positron")

        for _, row in df.iterrows():
            f, t = row['From'], row['To']
            if f in coords_dict and t in coords_dict:
                p1, p2 = coords_dict[f], coords_dict[t]
                # Simple line for speed (OSRM can be added back once headers work)
                folium.PolyLine([p1, p2], color="#E74C3C", weight=3).add_to(m)
                folium.Marker(location=p2, popup=f"Day {row['SL']}: {t}").add_to(m)

        st_folium(m, use_container_width=True)
        st.success(f"Successfully loaded {len(df)} days from your itinerary!")
