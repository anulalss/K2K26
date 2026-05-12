import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time

# --- CONFIGURATION ---
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXv6-bYGpE2J4FCXwdDSoRDNl7UhseCyaURUhIEnF-ZkI12GS7UD0pM4UQIoe96EJPJJavGnCuAWbI/pub?output=csv" 

st.set_page_config(layout="wide", page_title="K2K 2026", initial_sidebar_state="collapsed")

# --- SMART MEMORY ENGINES ---

@st.cache_data(ttl=3600) # Only looks at the spreadsheet once per hour unless forced
def load_itinerary(url):
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return None

@st.cache_data # MEMORY 1: Remembers city coordinates forever
def get_city_coord(city):
    geolocator = Nominatim(user_agent="k2k_smart_navigator_2026")
    clean_name = str(city).split('/')[0].strip()
    try:
        time.sleep(1) # Only happens for NEW cities
        loc = geolocator.geocode(f"{clean_name}, India")
        return [loc.latitude, loc.longitude] if loc else None
    except: return None

@st.cache_data # MEMORY 2: Remembers the road path between two points
def get_road_path(p1, p2):
    url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: return [p1, p2]

# --- MAIN APP ---

st.title("🏔️ K2K 2026 Smart Map")

# Sidebar for controls to keep mobile screen clean
with st.sidebar:
    st.header("Settings")
    if st.button("🔄 Sync Spreadsheet"):
        # This only clears the ITINERARY, not the city coordinates!
        st.cache_data.clear() 
        st.rerun()

# 1. Load the Sheet
df = load_itinerary(CSV_URL)

if df is not None and 'From' in df.columns:
    # Initialize Map
    m = folium.Map(location=[22.0, 78.0], zoom_start=5, tiles="CartoDB positron")
    all_points = []
    
    # 2. Process the Route
    with st.status("🔗 Linking Route Segments...") as status:
        for i, row in df.iterrows():
            f_city, t_city = row['From'], row['To']
            
            # These calls are INSTANT if the city was found before
            p1 = get_city_coord(f_city)
            p2 = get_city_coord(t_city)
            
            if p1 and p2:
                all_points.extend([p1, p2])
                
                # Draw Road Path (Instant if already cached)
                path = get_road_path(p1, p2)
                folium.PolyLine(path, color="#E74C3C", weight=4, opacity=0.8).add_to(m)
                
                # Add Stop Marker
                folium.CircleMarker(
                    location=p2, radius=5, color="white", fill=True, fill_color="#2E86C1", fill_opacity=1,
                    popup=f"Day {row['SL']}: {t_city}"
                ).add_to(m)
        
        status.update(label="✅ Route Loaded", state="complete")

    # 3. Final Map Adjustments
    if all_points:
        m.fit_bounds(all_points)
    
    st_folium(m, use_container_width=True)

    # 4. Mobile List View
    st.subheader("📋 Travel Log")
    for _, row in df.iterrows():
        with st.expander(f"Day {row['SL']}: {row['From']} ➔ {row['To']}"):
            st.write(f"🏨 **Stay:** {row.get('Night Stay', 'N/A')}")
            st.write(f"🛣️ **Via:** {row.get('Via / Route', 'N/A')}")
            st.info(f"📝 {row.get('Notes', 'No notes')}")
else:
    st.error("Sheet data not found. Please check your CSV URL.")
