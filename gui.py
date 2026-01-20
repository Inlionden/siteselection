import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import config

# Use the cleaned data file
DATA_FILE = config.CLEAN_DATA_FILE

def run_gui():
    st.set_page_config(page_title="POI Map Explorer", layout="wide")
    st.title("🗺️ POI Map Explorer (Folium)")

    @st.cache_data
    def load_data():
        if not os.path.exists(DATA_FILE):
            return None
        return pd.read_csv(DATA_FILE)

    df = load_data()

    if df is None:
        st.error(f"Data file not found at {DATA_FILE}. Please run the Cleaner first.")
        return

    # Sidebar
    st.sidebar.header("Filter Options")
    
    # 1. Search Query
    search_term = st.sidebar.text_input("Search Name/Type", "")

    # 2. Rating Filter
    min_rating = st.sidebar.slider("Min Rating", 0.0, 5.0, 0.0, 0.1)

    # Apply Filters
    filtered_df = df.copy()
    
    # Filter by search
    if search_term:
        mask = (
            filtered_df['Name'].str.contains(search_term, case=False, na=False) | 
            filtered_df['Search Query'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    # Filter by rating (handle non-numeric ratings if any)
    filtered_df['Rating'] = pd.to_numeric(filtered_df['Rating'], errors='coerce').fillna(0)
    filtered_df = filtered_df[filtered_df['Rating'] >= min_rating]

    st.sidebar.markdown(f"**Results:** {len(filtered_df)}")
    if st.sidebar.button("Reload Data"):
        st.cache_data.clear()
        st.experimental_rerun()

    # Main Display
    if not filtered_df.empty:
        # Folium Map
        avg_lat = filtered_df['Latitude'].mean()
        avg_lon = filtered_df['Longitude'].mean()
        
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)

        count = 0
        limit = 1000 # Avoid crashing browser with too many markers
        
        for _, row in filtered_df.iterrows():
            if count >= limit:
                break
                
            popup_html = f"""
            <div style="width:200px">
                <b>{row['Name']}</b><br>
                ⭐ {row['Rating']} ({row['Number of Reviews']})<br>
                <i>{row['Search Query']}</i>
            </div>
            """
            
            folium.Marker(
                [row['Latitude'], row['Longitude']],
                popup=popup_html,
                tooltip=row['Name']
            ).add_to(m)
            count += 1
            
        if len(filtered_df) > limit:
            st.warning(f"Showing first {limit} markers only (performance limit).")

        st_folium(m, width=1000, height=600)
    else:
        st.info("No POIs match your filters.")

    # Table
    with st.expander("Show Raw Data"):
        st.dataframe(filtered_df)

if __name__ == "__main__":
    run_gui()

# auto-commit
