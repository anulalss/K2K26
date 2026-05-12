import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time

# --- SETTINGS ---
# 1. MAKE SURE THIS LINK IS UPDATED!
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXv6-bYGpE2J4FCXwdDSoRDNl7UhseCyaURUhIEnF-ZkI12GS7UD0pM4UQIoe96EJPJJavGnCuAWbI/pub?output=csv"

st.set_page_config(layout="wide", page_title="K2K 2026", initial_sidebar_state="collapsed")

@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url)
        # FORCE CLEANING: Remove spaces and make lowercase for internal matching
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")
        return None

@st.cache_data
def get_coords(city_list):
    geolocator = Nominatim(user_agent="k2k_navigator_final")
    coords = {}
    for city in city_list:
        clean_name = str(city).split('/')[0].split(',')[0].strip()
        try:
            time.sleep(1) # Respect OSM usage limits
            loc = geolocator.geocode(f"{clean_name}, India")
            if loc: coords[city] = [loc.latitude, loc.longitude]
        except: continue
    return coords

def get_osrm_route(p1, p2):
    url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: return [p1, p2]

# --- APP LAYOUT ---
st.title("🏔️ K2K 2026 Map")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

df = load_data(CSV_URL)

if df is not None:
    # Debug: Check if the columns exist
    required_cols = ['From', 'To', 'SL']
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        st.warning(f"Wait! These columns are missing in your sheet: {missing}")
        st.write("Found these columns instead:", list(df.columns))
    else:
        unique_cities = pd.concat([df['From'], df['To']]).unique()
        with st.spinner("Mapping your route..."):
            coords_dict = get_coords(unique_cities)

        m = folium.Map(location=[22.0, 78.0], zoom_start=5, tiles="CartoDB positron")

        for _, row in df.iterrows():
            f, t = row['From'], row['To']
            if f in coords_dict and t in coords_dict:
                p1, p2 = coords_dict[f], coords_dict[t]
                route = get_osrm_route(p1, p2)
                folium.PolyLine(route, color="#E74C3C", weight=4).add_to(m)
                
                popup_html = f"<b>Day {row['SL']}</b>: {t}<br>Stay: {row.get('Night Stay', 'N/A')}"
                folium.Marker(location=p2, popup=folium.Popup(popup_html, max_width=200)).add_to(m)

        st_folium(m, use_container_width=True)

        # Itinerary List
        for _, row in df.iterrows():
            with st.expander(f"Day {row['SL']}: {row['From']} ➔ {row['To']}"):
                st.write(f"**Stay:** {row.get('Night Stay', 'N/A')}")
                st.info(f"**Notes:** {row.get('Notes', 'None')}")
