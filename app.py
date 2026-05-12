import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
# FIXED: Changed Locater to LocateControl
from folium.plugins import LocateControl, MousePosition, Fullscreen
from geopy.geocoders import Nominatim
import requests
import time

# --- 1. CONFIG ---
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXv6-bYGpE2J4FCXwdDSoRDNl7UhseCyaURUhIEnF-ZkI12GS7UD0pM4UQIoe96EJPJJavGnCuAWbI/pub?output=csv"

st.set_page_config(layout="wide", page_title="K2K 2026 Explorer", initial_sidebar_state="collapsed")

# Mobile Styling
st.markdown("""
    <style>
    iframe {width: 100% !important; height: 75vh !important;}
    .main > div {padding: 0rem;}
    .stMetric {background: #f0f2f6; padding: 10px; border-radius: 10px;}
    .popup-scroll { max-height: 250px; overflow-y: auto; font-size: 14px; min-width: 220px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ENGINES ---

@st.cache_data(ttl=600)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return None

@st.cache_data
def get_coords(city):
    geolocator = Nominatim(user_agent="k2k_final_pro_v2")
    clean = str(city).split('/')[0].strip()
    try:
        time.sleep(1.2)
        loc = geolocator.geocode(f"{clean}, India")
        return [loc.latitude, loc.longitude] if loc else None
    except: return None

@st.cache_data
def get_route(p1, p2):
    url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: return [p1, p2]

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.title("🧭 Navigator")
    if st.button("🔄 Sync New Data"):
        st.cache_data.clear()
        st.rerun()
    
    df = load_data(CSV_URL)
    if df is not None:
        search_query = st.selectbox("Jump to Day/City:", ["---"] + list(df['To']))

# --- 4. MAP LOGIC ---
st.title("🏔️ K2K 2026: Pro Dashboard")

if df is not None:
    coords_dict = {}
    unique_cities = pd.concat([df['From'], df['To']]).unique()
    
    with st.status("📡 Fetching GPS & Road Data...") as status:
        for city in unique_cities:
            c = get_coords(city)
            if c: coords_dict[city] = c
        status.update(label="✅ Systems Online", state="complete")

    # BASE MAPS
    m = folium.Map(location=[20.5, 78.9], zoom_start=5, tiles=None)
    folium.TileLayer('OpenStreetMap', name='Standard Map').add_to(m)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', name='Terrain (Mountains)', attr='Google').add_to(m)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', name='Satellite (Real View)', attr='Google').add_to(m)

    # ADD PLUGINS
    # FIXED: Using LocateControl instead of Locater
    LocateControl(auto_start=False).add_to(m) 
    Fullscreen().add_to(m)
    MousePosition().add_to(m) # Shows coordinates of your cursor
    folium.LayerControl().add_to(m)

    stop_groups = df.groupby('To')
    all_points = []

    for city_name, group in stop_groups:
        if city_name in coords_dict:
            pos = coords_dict[city_name]
            all_points.append(pos)
            
            popup_html = f'<div class="popup-scroll"><b>📍 {city_name}</b><hr>'
            for _, row in group.iterrows():
                # Add "Via" and "Key Stops" logic
                via_route = row.get('Via / Route', 'Direct')
                k_stops = f"❤️ {row.get('Key Stops', 'N/A')}" if str(row.get('Key Stops', '')) != 'nan' else 'N/A'
                
                popup_html += f"""
                <div style="margin-bottom:10px; border-bottom:1px solid #eee;">
                <b>Day {row['SL']}</b> | {row.get('Date','')} <br>
                <b>Via:</b> {via_route}<br>
                <b>Stops:</b> {k_stops}<br>
                <b>Stay:</b> {row.get('Night Stay','N/A')}<br>
                <small><i>{row.get('Notes','')}</i></small>
                </div>
                """
            popup_html += '</div>'
            
            # Smart Icons
            is_rest = group['Notes'].str.contains("Rest", na=False).any()
            icon = 'coffee' if is_rest else 'bed'
            color = 'orange' if is_rest else 'cadetblue'
            
            # Highlight searched city
            if city_name == search_query:
                color, icon = 'purple', 'star'

            folium.Marker(location=pos, popup=folium.Popup(popup_html, max_width=250),
                          icon=folium.Icon(color=color, icon=icon, prefix='fa')).add_to(m)

    # ROUTING
    for i in range(len(df)):
        r = df.iloc[i]
        if r['From'] in coords_dict and r['To'] in coords_dict:
            path = get_route(coords_dict[r['From']], coords_dict[r['To']])
            folium.PolyLine(path, color="#E74C3C", weight=5, opacity=0.7).add_to(m)

    if all_points:
        if search_query != "---" and search_query in coords_dict:
            m.location = coords_dict[search_query]
            m.zoom_start = 12
        else:
            m.fit_bounds(all_points)

    st_folium(m, use_container_width=True)

    # QUICK STATS
    c1, c2, c3 = st.columns(3)
    c1.metric("Trip", f"{df.iloc[0]['From']} ➔ {df.iloc[-1]['To']}")
    c2.metric("Total Days", len(df))
    c3.metric("Status", "Connected")

else:
    st.info("👋 Welcome! Paste your link to see the map.")
