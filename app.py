import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time

# --- CONFIGURATION ---
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXv6-bYGpE2J4FCXwdDSoRDNl7UhseCyaURUhIEnF-ZkI12GS7UD0pM4UQIoe96EJPJJavGnCuAWbI/pub?output=csv" # <--- Ensure it ends in output=csv

st.set_page_config(layout="wide", page_title="K2K 2026", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    iframe {width: 100% !important; height: 70vh !important;}
    .main > div {padding: 0rem;}
    .stButton>button {width: 100%; border-radius: 20px; background-color: #FF4B4B; color: white;}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return None

def get_road_path(p1, p2):
    """Fetches the real highway path between two points"""
    url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: return [p1, p2] # Fallback to straight line

@st.cache_data
def get_all_coords(cities):
    geolocator = Nominatim(user_agent="k2k_final_navigator")
    coords = {}
    for city in cities:
        clean_name = str(city).split('/')[0].strip()
        try:
            time.sleep(1) 
            loc = geolocator.geocode(f"{clean_name}, India")
            if loc: coords[city] = [loc.latitude, loc.longitude]
        except: continue
    return coords

# --- MAIN APP ---
df = load_data(CSV_URL)

if df is not None and 'From' in df.columns:
    st.title("🏔️ K2K 2026: Trivandrum to Ladakh")
    
    if st.button("🔄 Refresh Data from Sheet"):
        st.cache_data.clear()
        st.rerun()

    unique_cities = pd.concat([df['From'], df['To']]).unique()
    
    with st.status("🗺️ Building your route... (Takes ~30 seconds)", expanded=False) as status:
        coords_dict = get_all_coords(unique_cities)
        status.update(label="✅ Map Ready!", state="complete")

    # Create Map centered on India
    m = folium.Map(location=[20.5, 78.9], zoom_start=5, tiles="CartoDB positron")

    all_points = []
    for _, row in df.iterrows():
        f, t = row['From'], row['To']
        if f in coords_dict and t in coords_dict:
            p1, p2 = coords_dict[f], coords_dict[t]
            all_points.extend([p1, p2])
            
            # 1. Real Road Lines
            path = get_road_path(p1, p2)
            folium.PolyLine(path, color="#E74C3C", weight=4, opacity=0.8).add_to(m)
            
            # 2. Simplified Circle Markers (Way more reliable on mobile)
            folium.CircleMarker(
                location=p2,
                radius=6,
                color="white",
                fill=True,
                fill_color="#2E86C1",
                fill_opacity=1,
                popup=f"<b>Day {row['SL']}</b>: {t}<br>Stay: {row.get('Night Stay', 'N/A')}"
            ).add_to(m)

    # Auto-zoom to fit the entire route
    if all_points:
        m.fit_bounds(all_points)

    st_folium(m, use_container_width=True)

    # 3. Mobile-friendly Logs
    for _, row in df.iterrows():
        with st.expander(f"Day {row['SL']}: {row['From']} ➔ {row['To']}"):
            col1, col2 = st.columns(2)
            col1.metric("Distance", f"{row.get('Distance', '0')} km")
            col2.metric("Time", row.get('Drive Time', 'N/A'))
            st.write(f"🏨 **Stay:** {row.get('Night Stay', 'N/A')}")
            st.info(f"📝 **Notes:** {row.get('Notes', 'None')}")

else:
    st.error("Checking CSV structure...")
