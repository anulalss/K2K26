import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time

# --- 1. COORDINATE BANK (Instant Load) ---
# We store these here so the app doesn't have to "find" them every time.
COORD_BANK = {
    "Trivandrum": [8.5241, 76.9366],
    "Bangalore": [12.9716, 77.5946],
    "Hyderabad": [17.3850, 78.4867],
    "Nagpur": [21.1458, 79.0882],
    "Kota": [25.2138, 75.8648],
    "Jaipur": [26.9124, 75.7873],
    "Amritsar": [31.6340, 74.8723],
    "Srinagar": [34.0837, 74.7973],
    "Kargil": [34.5539, 76.1349],
    "Leh": [34.1526, 77.5771],
    "Nubra": [34.6863, 77.5673],
    "Pangong": [33.7595, 78.6674],
    "Jispa": [32.6415, 77.1892],
    "Manali": [32.2432, 77.1892],
    "Shimla": [31.1048, 77.1734],
    "Agra": [27.1767, 78.0081],
    "Jhansi": [25.4484, 78.5685]
}

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXv6-bYGpE2J4FCXwdDSoRDNl7UhseCyaURUhIEnF-ZkI12GS7UD0pM4UQIoe96EJPJJavGnCuAWbI/pub?output=csv"

st.set_page_config(layout="wide", page_title="K2K 2026")

def get_coords(city):
    """Checks the bank first, then the sheet, then the internet."""
    # 1. Check Hardcoded Bank
    if city in COORD_BANK:
        return COORD_BANK[city]
    
    # 2. If not found, use Geocoder (1 second delay)
    try:
        geolocator = Nominatim(user_agent="k2k_final_nav")
        time.sleep(1)
        loc = geolocator.geocode(f"{city}, India")
        if loc:
            return [loc.latitude, loc.longitude]
    except:
        return None

# --- APP LOGIC ---
st.title("🏔️ K2K 2026: Fast Map")

@st.cache_data(ttl=300)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    return df

df = load_data(CSV_URL)

if df is not None and 'From' in df.columns:
    # Check if we have saved coordinates in the sheet already
    m = folium.Map(location=[20.5, 78.9], zoom_start=5, tiles="CartoDB positron")
    all_points = []
    
    # Pre-calculate all coordinates
    with st.spinner("Loading Route..."):
        for _, row in df.iterrows():
            f_city = str(row['From']).split('/')[0].strip()
            t_city = str(row['To']).split('/')[0].strip()
            
            # Get Lat/Lon
            p1 = get_coords(f_city)
            p2 = get_coords(t_city)
            
            if p1 and p2:
                all_points.extend([p1, p2])
                folium.PolyLine([p1, p2], color="#E74C3C", weight=4).add_to(m)
                folium.CircleMarker(location=p2, radius=5, color="#2E86C1", fill=True).add_to(m)

    if all_points:
        m.fit_bounds(all_points)
    
    st_folium(m, use_container_width=True)

    # --- THE "HIDDEN DATA" TOOL ---
    with st.expander("🛠️ Admin: Export Coordinates to Google Sheet"):
        st.write("If you want the app to be even faster, copy these into your Sheet's Lat/Lon columns:")
        export_data = []
        for _, row in df.iterrows():
            f_city = str(row['From']).split('/')[0].strip()
            t_city = str(row['To']).split('/')[0].strip()
            p1 = get_coords(f_city)
            p2 = get_coords(t_city)
            export_data.append({
                "Day": row['SL'],
                "Start_Lat": p1[0] if p1 else "",
                "Start_Lon": p1[1] if p1 else "",
                "End_Lat": p2[0] if p2 else "",
                "End_Lon": p2[1] if p2 else ""
            })
        st.dataframe(pd.DataFrame(export_data))

else:
    st.error("Sheet not found or headers mismatch.")
