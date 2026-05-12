import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limit import RateLimiter
import requests

# --- SETTINGS ---
# Replace this with your actual Published CSV link
CSV_URL = "https://docs.google.com/spreadsheets/d/1EzJ4cRVo-qj0ciKSfd1dWFLKh3zzH60HMDWh9GDmtJY/edit?gid=327253181#gid=327253181"

st.set_page_config(layout="wide", page_title="Ladakh 2026 Map", initial_sidebar_state="collapsed")

# Mobile CSS Tweak
st.markdown("<style>iframe {width: 100% !important; height: 65vh !important;} .main > div {padding: 0rem;}</style>", unsafe_allow_html=True)

@st.cache_data(ttl=600) # Refreshes every 10 mins if you don't hit manual sync
def load_data(url):
    df = pd.read_csv(url)
    # Clean up column names in case of leading/trailing spaces
    df.columns = [c.strip() for c in df.columns]
    return df

@st.cache_data
def get_coords(city_list):
    geolocator = Nominatim(user_agent="ladakh_trip_navigator")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    coords = {}
    for city in city_list:
        # Clean city name (e.g. "Salem / Hosur" -> "Salem")
        clean_name = str(city).split('/')[0].split(',')[0].strip()
        try:
            loc = geocode(f"{clean_name}, India")
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
st.title("🏔️ Ladakh Route")

if st.button("🔄 Sync with Google Sheet"):
    st.cache_data.clear()
    st.rerun()

try:
    df = load_data(CSV_URL)
    unique_cities = pd.concat([df['From'], df['To']]).unique()
    coords_dict = get_coords(unique_cities)

    # Start map at the first coordinate found
    start_loc = next(iter(coords_dict.values())) if coords_dict else [20.5, 78.9]
    m = folium.Map(location=start_loc, zoom_start=5, tiles="CartoDB positron")

    for _, row in df.iterrows():
        f, t = row['From'], row['To']
        if f in coords_dict and t in coords_dict:
            p1, p2 = coords_dict[f], coords_dict[t]
            
            # Draw Route Lines
            route = get_osrm_route(p1, p2)
            folium.PolyLine(route, color="#3498DB", weight=4, opacity=0.8).add_to(m)
            
            # Add Marker for Destination
            popup_text = f"<b>Day {row['SL']}</b>: {t}<br>Stay: {row['Night Stay']}<br>Notes: {row['Notes']}"
            folium.Marker(location=p2, popup=folium.Popup(popup_text, max_width=200)).add_to(m)

    st_folium(m, use_container_width=True)

    st.subheader("📋 Itinerary")
    for i, row in df.iterrows():
        with st.expander(f"Day {row['SL']}: {row['From']} ➔ {row['To']}"):
            st.write(f"**Distance:** {row['Distance']} | **Time:** {row['Drive Time']}")
            st.write(f"**Hotel:** {row['Night Stay']}")
            st.info(f"**Notes:** {row['Notes']}")

except Exception as e:
    st.error(f"Wait! Make sure your CSV link is correct. Error: {e}")
