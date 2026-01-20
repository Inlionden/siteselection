#!/usr/bin/env python3
"""
new_scraper.py

A robust Google Maps grid POI scraper.
Features:
- URL-based navigation
- Robust name extraction
- Screenshot capability
- Clean CSV output (no UTC_Time)
"""

import time
import csv
import os
import re
import math
from math import radians, sin, cos, sqrt, atan2
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# ---------------------------
# Config
# ---------------------------
OUTPUT_DIR = "Dataset"
COMBINED_CSV = os.path.join(OUTPUT_DIR, "dataset.csv")
PER_CATEGORY_DIR = os.path.join(OUTPUT_DIR, "categories")

TAKE_SCREENSHOTS = True   # Enabled by default as requested
HEADLESS = False          # Set to True for headless mode
PAUSE_AFTER_LOAD = 3      # Seconds to wait after loading a search URL
ZOOM = 15                 # Map zoom level

# Grid area / steps (example coordinates)
START_LAT = 38.836359
START_LON = -77.048358
END_LAT = 38.974690
END_LON = -77.013404

# Grid spacing (~1km)
STEP_LAT = 0.02
STEP_LON = 0.02

# Search limits
NUM_RESULTS_PER_SEARCH = 10

# Categories
CATEGORIES = {
    "Event Venue": [
        "Conference Center", "Convention Center", "Stadium", "Arena"
    ],
}

# ---------------------------
# Helpers
# ---------------------------
def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PER_CATEGORY_DIR, exist_ok=True)

def write_rows_to_csv(path, rows, header=None):
    first_time = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if header and first_time:
            writer.writerow(header)
        for r in rows:
            writer.writerow(r)

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

        # Fallback pattern: first two floats in URL
        floats = re.findall(r'(-?\d+\.\d+)', url)
        if len(floats) >= 2:
            return float(floats[0]), float(floats[1])
    except Exception as e:
        print(f"Error parsing coordinates from URL: {e}")
    
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

# ---------------------------
# Scraping Logic
# ---------------------------
def build_search_url(query, lat, lon, zoom=ZOOM):
    """Build a stable URL centered at lat,lon."""
    q = quote_plus(query)
    return f"https://www.google.com/maps/search/{q}/@{lat},{lon},{zoom}z"

def parse_left_panel_pois(page_source, max_results=NUM_RESULTS_PER_SEARCH):
    """
    Parse POI items from the left result panel with robust selectors.
    """
    soup = BeautifulSoup(page_source, "html.parser")
    candidates = []

    # 1. Try finding card containers
    cards = soup.find_all('div', class_='Nv2PK')
    
    # 2. Fallback: Find links that look like places
    if not cards:
        cards = [a for a in soup.find_all('a', href=True) 
                 if ('/place/' in a['href'] or '/maps' in a['href']) and a.get_text(strip=True)]

    for card in cards:
        if len(candidates) >= max_results:
            break

        try:
            # Extract Link
            if card.name == 'a' and card.get('href'):
                link = card['href']
            else:
                link_tag = card.find('a', href=True)
                link = link_tag['href'] if link_tag else ''

            # Extract Name (Robust)
            name = None
            # Priority 1: aria-label on the card or link
            if card.get('aria-label'):
                name = card['aria-label']
            elif card.name == 'a' and card.get('aria-label'):
                name = card['aria-label']
            
            # Priority 2: Specific classes
            if not name:
                name_tag = card.find('div', class_='qBF1Pd') or card.find('div', class_='fontHeadlineSmall')
                if name_tag:
                    name = name_tag.get_text(strip=True)
            
            # Priority 3: Fallback text
            if not name:
                name = card.get_text(strip=True)[:200]

            # Extract Rating
            rating_tag = card.find('span', class_='MW4etd') or card.find('span', {'aria-label': True})
            rating = rating_tag.get_text(strip=True) if rating_tag else ''

            # Extract Reviews
            reviews_tag = card.find('span', class_='UY7F9') or card.find('span', {'aria-hidden': True})
            raw_reviews = reviews_tag.get_text(strip=True) if reviews_tag else ''
            # Clean reviews format e.g. "(100)" -> "100"
            reviews = raw_reviews.strip('()')

            if name:
                candidates.append({
                    "name": name,
                    "link": link,
                    "rating": rating,
                    "reviews": reviews
                })
        except Exception as e:
            continue

    return candidates

def scrape_for_query(driver, query, lat, lon, max_results=NUM_RESULTS_PER_SEARCH, take_screenshot=False, row_idx=None, col_idx=None):
    url = build_search_url(query, lat, lon)
    driver.get(url)
    time.sleep(PAUSE_AFTER_LOAD)

    page_source = driver.page_source
    pois = parse_left_panel_pois(page_source, max_results=max_results)

    rows = []
    for p in pois:
        plat, plon = extract_coordinates_from_url(p.get('link', ''))
        
        # Fallback to center if extraction fails (mark as approx)
        if (plat is None) or (plon is None):
            plat, plon = lat, lon

        dist_m = haversine_distance(lat, lon, plat, plon) if (plat and plon) else None

        rows.append([
            p.get('name', 'N/A'),
            p.get('rating', ''),
            p.get('reviews', ''),
            f"{plat:.6f}" if plat else 'N/A',
            f"{plon:.6f}" if plon else 'N/A',
            query,
            f"{lat:.6f}",
            f"{lon:.6f}",
            f"{dist_m:.1f}" if dist_m is not None else ""
        ])

    if take_screenshot:
        try:
            fname = f"shot_r{row_idx}_c{col_idx}_{lat:.6f}_{lon:.6f}.png"
            path = os.path.join(PER_CATEGORY_DIR, fname)
            driver.save_screenshot(path)
        except Exception as e:
            print(f"Screenshot failed: {e}")

    return rows

# ---------------------------
# Main Grid Loop
# ---------------------------
def run_grid_scrape(driver):
    ensure_dirs()
    header = ["Name", "Rating", "Number of Reviews", "Latitude", "Longitude", "Search Query", "CenterLat", "CenterLon", "Distance_m"]
    
    if not os.path.exists(COMBINED_CSV):
        write_rows_to_csv(COMBINED_CSV, [], header=header)

    lat = START_LAT
    row = 0
    while lat <= END_LAT + 1e-12:
        lon = START_LON
        col = 0
        while lon <= END_LON + 1e-12:
            print(f"\n--- Grid ({row}, {col}) Center: {lat:.6f}, {lon:.6f} ---")
            
            for cat, subcats in CATEGORIES.items():
                cat_dir = os.path.join(PER_CATEGORY_DIR, cat.replace(" ", "_"))
                os.makedirs(cat_dir, exist_ok=True)

                for subcat in subcats:
                    print(f" searching: {subcat}")
                    rows = scrape_for_query(
                        driver, subcat, lat, lon,
                        max_results=NUM_RESULTS_PER_SEARCH,
                        take_screenshot=TAKE_SCREENSHOTS,
                        row_idx=row, col_idx=col
                    )
                    
                    if rows:
                        # Save category-specific file
                        safe_subcat = subcat.replace(' ', '_')
                        filename = os.path.join(cat_dir, f"{safe_subcat}.csv")
                        write_rows_to_csv(filename, rows, header=header)
                        
                        # Append to combined dataset
                        write_rows_to_csv(COMBINED_CSV, rows)
                        print(f"  -> Found {len(rows)} POIs")
                    else:
                        print("  -> No results")
                    
                    time.sleep(1) # Polite delay

            lon += STEP_LON
            col += 1
        lat += STEP_LAT
        row += 1

def main():
    print("Starting Main Scraper...")
    chrome_opts = Options()
    if HEADLESS:
        chrome_opts.add_argument("--headless=new")
    else:
        chrome_opts.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=chrome_opts)
    try:
        driver.get("https://www.google.com/maps")
        time.sleep(2)
        run_grid_scrape(driver)
        print("\nDone! Check the 'Dataset' folder.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
