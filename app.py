import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time  # <--- Added this for manual delay

# --- SETTINGS ---
# Replace this with your actual Published CSV link
CSV_URL = "https://docs.google.com/spreadsheets/d/1EzJ4cRVo-qj0ciKSfd1dWFLKh3zzH60HMDWh9GDmtJY/edit?gid=327253181#gid=327253181"

st.set_page_config(layout="wide", page_title="Ladakh 2026 Map", initial_sidebar_state="collapsed")

# Mobile CSS Tweak
st.markdown("<style>iframe {width: 100% !important; height: 65vh !important;} .main > div {padding: 0rem;}</style>", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = [c.strip() for c in df.columns]
    return df

@st.cache_data
def get_coords(city_list):
    geolocator = Nominatim(user_agent="k2k_navigator_2026")
    coords = {}
    for city in city_list:
        clean_name = str(city).split('/')[0].split(',')[0].strip()
        try:
            # We manually wait 1 second to follow OpenStreetMap rules
            time.sleep(1) 
            loc = geolocator.geocode(f"{clean_name}, India")
            if loc: 
                coords[city] = [loc.latitude, loc.longitude]
        except: 
            continue
    return coords

def get_osrm_route(p1, p2):
    url = f"http://router.project-osrm.org/route/v1/driving/{p1[1]},{p1[0]};{p2[1]},{p2[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: 
        return [p1, p2]

# --- APP LAYOUT ---
st.title("🏔️ K2K 2026 Route")

if st.button("🔄 Sync with Google Sheet"):
    st.cache_data.clear()
    st.rerun()

try:
    df = load_data(CSV_URL)
    unique_cities = pd.concat([df['From'], df['To']]).unique()
    
    with st.spinner("Calculating route coordinates..."):
        coords_dict = get_coords(unique_cities)

    # Center map in India
    m = folium.Map(location=[22.0, 78.0], zoom_start=5, tiles="CartoDB positron")

    for _, row in df.iterrows():
        f, t = row['From'], row['To']
        if f in coords_dict and t in coords_dict:
            p1, p2 = coords_dict[f], coords_dict[t]
            
            # Draw Route Lines
            route = get_osrm_route(p1, p2)
            folium.PolyLine(route, color="#E74C3C", weight=4, opacity=0.8).add_to(m)
            
            # Add Marker for Destination
            popup_text = f"<b>Day {row['SL']}</b>: {t}<br>Stay: {row['Night Stay']}<br>Notes: {row['Notes']}"
            folium.Marker(location=p2, popup=folium.Popup(popup_text, max_width=200)).add_to(m)

    st_folium(m, use_container_width=True)

    st.subheader("📋 Travel Log")
    for i, row in df.iterrows():
        with st.expander(f"Day {row['SL']}: {row['From']} ➔ {row['To']}"):
            st.write(f"**Drive:** {row['Distance']} km | {row['Drive Time']}")
            st.write(f"**Stay:** {row['Night Stay']}")
            st.info(f"**Notes:** {row['Notes']}")

except Exception as e:
    st.error(f"Waiting for valid data... (Make sure CSV link is correct). Details: {e}")
