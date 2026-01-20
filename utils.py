import os
import csv
import re
from math import radians, sin, cos, sqrt, atan2
from urllib.parse import quote_plus
from config import OUTPUT_DIR, PER_CATEGORY_DIR, ZOOM

def ensure_dirs():
    """Ensure output directories exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PER_CATEGORY_DIR, exist_ok=True)

def write_rows_to_csv(path, rows, header=None):
    """Write list of rows to CSV file."""
    first_time = not os.path.exists(path)
    # Create parent directory if needed
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if header and first_time:
            writer.writerow(header)
        for r in rows:
            writer.writerow(r)

def build_search_url(query, lat, lon, zoom=ZOOM):
    """Build a stable URL centered at lat,lon."""
    q = quote_plus(query)
    # Using /search/ path centered at lat,lon
    return f"https://www.google.com/maps/search/{q}/@{lat},{lon},{zoom}z"

def extract_coordinates_from_url(url: str):
    """
    Robustly extract coordinates from a Google Maps URL.
    Returns (lat, lon) or (None, None).
    """
    try:
        # Pattern: @lat,lon,...
        m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
        if m:
            return float(m.group(1)), float(m.group(2))

        # Fallback: search for any 2 floats in URL
        floats = re.findall(r'(-?\d+\.\d+)', url)
        if len(floats) >= 2:
            return float(floats[0]), float(floats[1])
    except Exception as e:
        print(f"Error parsing coordinates: {e}")
    
    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance in meters between two lat/lon points."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    
    a = sin(dphi/2)**2 + cos(phi1) * cos(phi2) * sin(dlambda/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
