import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time

# --- CONFIG ---
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXv6-bYGpE2J4FCXwdDSoRDNl7UhseCyaURUhIEnF-ZkI12GS7UD0pM4UQIoe96EJPJJavGnCuAWbI/pub?output=csv"

st.set_page_config(layout="wide", page_title="K2K 2026", initial_sidebar_state="collapsed")

@st.cache_data(ttl=300)
def load_itinerary(url):
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return None

@st.cache_data
def get_city_coord(city):
    geolocator = Nominatim(user_agent="k2k_final_test_2026")
    # Clean the name: Take the first part of a slash, remove special chars
    clean_name = str(city).split('/')[0].strip()
    
    # Try 1: Just the name
    # Try 2: Name + India
    for query in [f"{clean_name}, India", clean_name]:
        try:
            time.sleep(1.2) # Slightly longer delay to avoid 403 errors
            loc = geolocator.geocode(query, timeout=10)
            if loc: return [loc.latitude, loc.longitude]
        except: continue
    return None

@st.cache_data
def get_road_path(p1, p2):
    url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        if 'routes' in r:
            return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: pass
    return [p1, p2]

# --- MAIN ---
st.title("🏔️ K2K 2026: Route Debugger")

df = load_itinerary(CSV_URL)

if df is not None and 'From' in df.columns:
    if st.button("🔄 Force Resync All Data"):
        st.cache_data.clear()
        st.rerun()

    coords_dict = {}
    unique_cities = pd.concat([df['From'], df['To']]).unique()
    
    with st.status("🗺️ Finding locations...") as status:
        for city in unique_cities:
            c = get_city_coord(city)
            if c: coords_dict[city] = c
        status.update(label="✅ Search Finished", state="complete")

    # --- MAP BUILDING ---
    m = folium.Map(location=[20.5, 78.9], zoom_start=5, tiles="OpenStreetMap") # Switched to OSM for better contrast
    
    all_points = []
    found_count = 0

    for _, row in df.iterrows():
        f, t = row['From'], row['To']
        if f in coords_dict and t in coords_dict:
            p1, p2 = coords_dict[f], coords_dict[t]
            all_points.extend([p1, p2])
            
            path = get_road_path(p1, p2)
            folium.PolyLine(path, color="red", weight=5, opacity=0.8).add_to(m)
            folium.Marker(location=p2, popup=f"Day {row['SL']}: {t}").add_to(m)
            found_count += 1

    if all_points:
        m.fit_bounds(all_points)
    
    st_folium(m, use_container_width=True)
    st.write(f"📊 Successfully mapped **{found_count}** out of **{len(df)}** route legs.")

    # --- TROUBLESHOOTER ---
    with st.expander("🔍 Coordinate Troubleshooter (Check this if map is empty)"):
        debug_data = []
        for city in unique_cities:
            loc = coords_dict.get(city)
            debug_data.append({"City in Excel": city, "Found?": "✅" if loc else "❌", "Coords": loc})
        st.table(pd.DataFrame(debug_data))

else:
    st.error("Cannot find columns 'From' and 'To' in your sheet.")
