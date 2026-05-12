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

# Mobile UI Styling
st.markdown("""
    <style>
    iframe {width: 100% !important; height: 75vh !important;}
    .main > div {padding: 0rem;}
    [data-testid="stMetricValue"] {font-size: 1.5rem;}
    </style>
    """, unsafe_allow_html=True)

# --- THE "MEMORY" ENGINE ---
# This function is only ever run once, until you clear the cache.
@st.cache_data(show_spinner=False)
def get_full_trip_data(url):
    """Fetches data, finds coordinates, and bundles them for storage."""
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
    except Exception as e:
        return None, str(e)

    geolocator = Nominatim(user_agent="k2k_final_memory_engine")
    coords_dict = {}
    
    # Get unique cities from the itinerary
    unique_cities = pd.concat([df['From'], df['To']]).unique()
    
    # Process cities one by one
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, city in enumerate(unique_cities):
        status_text.text(f"🌍 Mapping: {city}")
        # Clean name (e.g., 'Salem / Hosur' -> 'Salem')
        clean_name = str(city).split('/')[0].strip()
        try:
            time.sleep(1) # Mandated 1-sec delay for the free geocoder
            loc = geolocator.geocode(f"{clean_name}, India")
            if loc:
                coords_dict[city] = [loc.latitude, loc.longitude]
        except:
            pass
        progress_bar.progress((i + 1) / len(unique_cities))
    
    status_text.empty()
    progress_bar.empty()
    
    return {"df": df, "coords": coords_dict}, "Success"

# --- APP LAYOUT ---
st.title("🏔️ K2K 2026 Route")

# The only way to trigger a fresh download from the Spreadsheet
if st.button("🔄 Resync & Fetch Fresh Data"):
    st.cache_data.clear()
    st.rerun()

# This call retrieves the "Saved" version if it exists
bundle, status_msg = get_full_trip_data(CSV_URL)

if bundle:
    df = bundle["df"]
    coords_dict = bundle["coords"]

    # 1. Generate Map
    m = folium.Map(location=[22.0, 78.0], zoom_start=5, tiles="CartoDB positron")
    all_points = []

    for _, row in df.iterrows():
        f, t = row['From'], row['To']
        if f in coords_dict and t in coords_dict:
            p1, p2 = coords_dict[f], coords_dict[t]
            all_points.extend([p1, p2])
            
            # Simple direct lines for high-speed loading
            folium.PolyLine([p1, p2], color="#E74C3C", weight=3, opacity=0.7).add_to(m)
            
            # Circle markers are best for mobile performance
            folium.CircleMarker(
                location=p2,
                radius=5,
                color="white",
                fill=True,
                fill_color="#2E86C1",
                fill_opacity=1,
                popup=f"Day {row['SL']}: {t}"
            ).add_to(m)

    if all_points:
        m.fit_bounds(all_points)

    st_folium(m, use_container_width=True)

    # 2. Itinerary Summary
    st.subheader("📅 Your Itinerary")
    for _, row in df.iterrows():
        with st.expander(f"Day {row['SL']}: {row['From']} ➔ {row['To']}"):
            st.write(f"🏨 Stay: {row.get('Night Stay', 'N/A')}")
            st.write(f"🛣️ Route: {row.get('Via / Route', 'N/A')}")
            st.info(f"📝 Notes: {row.get('Notes', 'None')}")

else:
    st.error(f"Waiting for your initial fetch... Please ensure your CSV URL is correct. Error: {status_msg}")
