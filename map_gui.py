import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# Config
DATA_FILE = os.path.join('Dataset', 'updated_dataset1.csv')

st.set_page_config(page_title="POI Map Viewer", layout="wide")

st.title("📍 Google Maps POI Visualizer")

@st.cache_data
def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    return pd.read_csv(DATA_FILE)

df = load_data()

if df is None:
    st.error(f"Data file not found at {DATA_FILE}. Please run `data_cleaner.py` first.")
else:
    # Sidebar Filters
    st.sidebar.header("Filters")
    
    # Text Search
    search_term = st.sidebar.text_input("Search Name/Category", "")
    
    # Filter Logic
    filtered_df = df.copy()
    if search_term:
        mask = (
            filtered_df['Name'].str.contains(search_term, case=False, na=False) | 
            filtered_df['Search Query'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    st.sidebar.markdown(f"**Results:** {len(filtered_df)}")

    # Map
    if not filtered_df.empty:
        # Center map on the average location of filtered results
        avg_lat = filtered_df['Latitude'].mean()
        avg_lon = filtered_df['Longitude'].mean()
        
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

        # Marker Cluster could be added, but keeping it simple for now
        for _, row in filtered_df.iterrows():
            popup_html = f"""
            <b>{row['Name']}</b><br>
            Rating: {row['Rating']}<br>
            Reviews: {row['Number of Reviews']}<br>
            Type: {row['Search Query']}
            """
            folium.Marker(
                [row['Latitude'], row['Longitude']],
                popup=popup_html,
                tooltip=row['Name']
            ).add_to(m)

        st_folium(m, width=1000, height=600)
    else:
        st.warning("No results found matching your search.")

    # Data Table
    st.subheader("Raw Data")
    st.dataframe(filtered_df)
