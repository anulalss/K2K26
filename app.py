import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time

# --- 1. CONFIGURATION ---
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXv6-bYGpE2J4FCXwdDSoRDNl7UhseCyaURUhIEnF-ZkI12GS7UD0pM4UQIoe96EJPJJavGnCuAWbI/pub?output=csv"

st.set_page_config(layout="wide", page_title="K2K 2026", initial_sidebar_state="collapsed")

# Mobile UI Optimization with better Popup styling
st.markdown("""
    <style>
    iframe {width: 100% !important; height: 70vh !important;}
    .main > div {padding: 0rem;}
    .stButton>button {width: 100%; border-radius: 15px; height: 3em; background-color: #2E86C1; color: white; font-weight: bold;}
    .leaflet-popup-content-wrapper { border-radius: 10px; padding: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CACHED ENGINES ---

@st.cache_data(ttl=300)
def load_itinerary(url):
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return None

@st.cache_data
def get_city_coord(city):
    geolocator = Nominatim(user_agent="k2k_final_navigator_2026")
    clean_name = str(city).split('/')[0].strip()
    for query in [f"{clean_name}, India", clean_name]:
        try:
            time.sleep(1.2)
            loc = geolocator.geocode(query, timeout=10)
            if loc: return [loc.latitude, loc.longitude]
        except: continue
    return None

@st.cache_data
def get_road_path(p1, p2):
    url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        if 'routes' in r and len(r['routes']) > 0:
            return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: pass
    return [p1, p2]

# --- 3. MAIN APP LOGIC ---

st.title("🏔️ K2K 2026 Dashboard")

df = load_itinerary(CSV_URL)

if df is not None and 'From' in df.columns:
    
    if st.button("🔄 Sync Spreadsheet"):
        st.cache_data.clear()
        st.rerun()

    coords_dict = {}
    unique_cities = pd.concat([df['From'], df['To']]).unique()
    
    with st.status("🗺️ Updating Map...", expanded=False) as status:
        for city in unique_cities:
            c = get_city_coord(city)
            if c: coords_dict[city] = c
        status.update(label="✅ Ready", state="complete")

    m = folium.Map(location=[20.5, 78.9], zoom_start=5, tiles="OpenStreetMap")
    all_points = []
    
    for i, row in df.iterrows():
        f_name, t_name = row['From'], row['To']
        if f_name in coords_dict and t_name in coords_dict:
            p1, p2 = coords_dict[f_name], coords_dict[t_name]
            all_points.extend([p1, p2])
            
            path = get_road_path(p1, p2)
            folium.PolyLine(path, color="#E74C3C", weight=5, opacity=0.7).add_to(m)
            
            # --- POPUP CONTENT ---
            # Formatting the data for the popup window
            notes = str(row.get('Notes', 'None'))
            warning_style = "color: red; font-weight: bold;" if "Tough" in notes or "Long" in notes or "Rough" in notes else "color: black;"
            
            popup_html = f"""
            <div style="font-family: Arial; min-width: 200px;">
                <h4 style="margin-bottom: 5px;">Day {row['SL']}: {t_name}</h4>
                <p style="margin: 2px 0;"><b>📅 Date:</b> {row.get('Day', '')} {row.get('Date', '')}</p>
                <p style="margin: 2px 0;"><b>🚀 From:</b> {f_name}</p>
                <p style="margin: 2px 0;"><b>🏁 Halt:</b> {row.get('Night Stay', 'N/A')}</p>
                <hr style="margin: 5px 0;">
                <p style="margin: 2px 0;"><b>🛣️ Dist/Time:</b> {row.get('Distance', '0')}km / {row.get('Drive Time', 'N/A')}</p>
                <p style="margin: 2px 0; {warning_style}"><b>⚠️ Note:</b> {notes}</p>
            </div>
            """
            
            # Icon Logic
            is_rest = "Rest" in notes
            marker_icon = 'coffee' if is_rest else 'bed'
            marker_color = 'orange' if is_rest else 'cadetblue'
            if i == 0: marker_icon, marker_color = 'play', 'green'
            elif i == len(df) - 1: marker_icon, marker_color = 'flag-checkered', 'red'

            folium.Marker(
                location=p2,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"Day {row['SL']}: {t_name}",
                icon=folium.Icon(color=marker_color, icon=marker_icon, prefix='fa')
            ).add_to(m)

    if all_points:
        m.fit_bounds(all_points)
    
    st_folium(m, use_container_width=True)

    # 4. ITINERARY LIST
    st.subheader("📋 Detailed Travel Log")
    for _, row in df.iterrows():
        with st.expander(f"Day {row['SL']}: {row['From']} ➔ {row['To']}"):
            col1, col2 = st.columns(2)
            col1.metric("Distance", f"{row.get('Distance', '0')} km")
            col2.metric("Drive Time", row.get('Drive Time', 'N/A'))
            st.write(f"🏨 **Stay:** {row.get('Night Stay', 'N/A')}")
            st.info(f"📝 **Highlight:** {row.get('Notes', 'None')}")

else:
    st.error("⚠️ Ensure CSV URL is correct in app.py")
