#!/usr/bin/env python3
"""
maps_grid_poi_scrape.py

Stable-ish Google Maps grid POI scraper using URL-based navigation.

Notes:
 - Requires: pip install selenium beautifulsoup4
 - Selenium >= 4.6 recommended (Selenium Manager auto-manages chromedriver)
 - This is for demo / research only. Respect Terms of Service & robots.txt.
"""

import time
import csv
import os
import re
import math
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# ---------------------------
# Config (edit these)
# ---------------------------
OUTPUT_DIR = "Dataset"
COMBINED_CSV = os.path.join(OUTPUT_DIR, "dataset.csv")
PER_CATEGORY_DIR = os.path.join(OUTPUT_DIR, "categories")

TAKE_SCREENSHOTS = False   # optional: set True if you want screenshots
HEADLESS = False          # headless mode
PAUSE_AFTER_LOAD = 3      # seconds to wait after loading a search URL
ZOOM = 15                 # google maps zoom level

# Grid area / steps (in degrees)
START_LAT = 38.8363592557036
START_LON = -77.04835828729044
END_LAT = 38.97469056279769
END_LON = -77.01340485076507

# grid spacing (approx ~ 1km per 0.009 degree lat; tune as needed)
STEP_LAT = 0.02
STEP_LON = 0.02

# choice: how many results to collect from the left-side panel (approx)
NUM_RESULTS_PER_SEARCH = 10

# Categories and subcategories to search (example)
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
    Tries patterns like: /@lat,lon,zoom or ?q=lat,lon
    Returns (lat, lon) or (None, None)
    """
    try:
        # pattern @lat,lon,... (most common)
        m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
        if m:
            return float(m.group(1)), float(m.group(2))

        # pattern /search/.../.../data=!3m1!4b1!4m5!3m4! etc - fallback: find first two floats
        floats = re.findall(r'(-?\d+\.\d+)', url)
        if len(floats) >= 2:
            # choose first two as fallback (not ideal but better than nothing)
            return float(floats[0]), float(floats[1])

    except Exception as e:
        print("coord parse error:", e)

    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance in meters between two lat/lon points (consistent signature)."""
    R = 6371000  # meters
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1) * cos(phi2) * sin(dlambda/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# ---------------------------
# Scraping logic
# ---------------------------
def build_search_url(query, lat, lon, zoom=ZOOM):
    """Build a stable URL that centers the map at lat,lon and runs the search."""
    # encode query for URL path
    q = quote_plus(query)
    # use the /search/ path and center by @lat,lon,zoom to keep it stable
    return f"https://www.google.com/maps/search/{q}/@{lat},{lon},{zoom}z"

def parse_left_panel_pois(page_source, max_results=NUM_RESULTS_PER_SEARCH):
    """
    Parse POI items from the left result panel.
    Returns list of dicts: {name, rating, reviews, link}
    """
    soup = BeautifulSoup(page_source, "html.parser")

    # The left cards often have class 'Nv2PK' (dynamic), but we'll look for common structures:
    candidates = []

    # Try specific known card class
    cards = soup.find_all('div', class_='Nv2PK')
    if not cards:
        # fallback: find anchor elements that look like place links
        cards = soup.find_all('a', href=True)
        # filter anchors that include '/place/' or '/maps' path and have text
        cards = [a for a in cards if ('/place/' in a['href'] or '/maps' in a['href']) and a.get_text(strip=True)]

    for card in cards:
        if len(candidates) >= max_results:
            break

        try:
            # attempt to get name and link
            if card.name == 'a' and card.get('href'):
                link = card['href']
                name = card.get_text(strip=True)[:200]
            else:
                link_tag = card.find('a', href=True)
                link = link_tag['href'] if link_tag else ''
                # name often in div with role heading inside the card
                name_tag = card.find(['div', 'h3'], recursive=True)
                name = name_tag.get_text(strip=True) if name_tag else card.get_text(strip=True)[:200]

            # rating and reviews - best-effort
            rating_tag = card.find('span', class_='MW4etd') or card.find('span', {'aria-label': True})
            rating = rating_tag.get_text(strip=True) if rating_tag else ''

            reviews_tag = card.find('span', class_='UY7F9') or card.find('span', {'aria-hidden': True})
            reviews = reviews_tag.get_text(strip=True) if reviews_tag else ''

            candidates.append({
                "name": name,
                "link": link,
                "rating": rating,
                "reviews": reviews
            })
        except Exception:
            continue

    return candidates

def scrape_for_query(driver, query, lat, lon, max_results=NUM_RESULTS_PER_SEARCH, take_screenshot=False, row_idx=None, col_idx=None):
    url = build_search_url(query, lat, lon)
    driver.get(url)
    time.sleep(PAUSE_AFTER_LOAD)

    page_source = driver.page_source
    pois = parse_left_panel_pois(page_source, max_results=max_results)

    rows = []
    for idx, p in enumerate(pois):
        plat, plon = extract_coordinates_from_url(p.get('link', ''))
        if (plat is None) or (plon is None):
            # fallback: sometimes link is relative; try to find coordinates in page (not robust)
            plat, plon = lat, lon

        dist_m = haversine_distance(lat, lon, plat, plon) if (plat and plon) else None

        rows.append([
            p.get('name', 'N/A'),
            p.get('rating', ''),
            p.get('reviews', ''),
            plat if plat is not None else 'N/A',
            plon if plon is not None else 'N/A',
            query,
            datetime.utcnow().isoformat(),
            f"{lat:.6f}",
            f"{lon:.6f}",
            f"{dist_m:.1f}" if dist_m is not None else ""
        ])

    # optional screenshot
    if take_screenshot:
        try:
            fname = f"shot_r{row_idx}_c{col_idx}_{lat:.6f}_{lon:.6f}.png"
            path = os.path.join(PER_CATEGORY_DIR, fname)
            driver.save_screenshot(path)
        except Exception as e:
            print("Screenshot failed:", e)

    return rows

# ---------------------------
# Grid traversal
# ---------------------------
def run_grid_scrape(driver,
                    start_lat, start_lon, end_lat, end_lon,
                    step_lat=STEP_LAT, step_lon=STEP_LON,
                    categories=CATEGORIES):
    ensure_dirs()
    # prepare combined CSV header
    header = ["Name", "Rating", "Number of Reviews", "Latitude", "Longitude", "Search Query", "UTC_Time", "CenterLat", "CenterLon", "Distance_m"]
    # ensure combined CSV exists with header
    if not os.path.exists(COMBINED_CSV):
        write_rows_to_csv(COMBINED_CSV, [], header=header)

    lat = start_lat
    row = 0
    while lat <= end_lat + 1e-12:
        lon = start_lon
        col = 0
        while lon <= end_lon + 1e-12:
            print(f"\n--- Grid point row {row} col {col} -> center ({lat:.6f}, {lon:.6f}) ---")
            for cat, subcats in categories.items():
                cat_dir = os.path.join(PER_CATEGORY_DIR, cat.replace(" ", "_"))
                os.makedirs(cat_dir, exist_ok=True)

                for subcat in subcats:
                    try:
                        rows = scrape_for_query(driver, subcat, lat, lon, max_results=NUM_RESULTS_PER_SEARCH,
                                                take_screenshot=TAKE_SCREENSHOTS, row_idx=row, col_idx=col)
                        if rows:
                            # save per-subcategory
                            filename = os.path.join(cat_dir, f"{subcat.replace(' ','_')}.csv")
                            write_rows_to_csv(filename, rows, header=header)

                            # append to combined
                            write_rows_to_csv(COMBINED_CSV, rows)
                            print(f"Saved {len(rows)} results for '{subcat}'")
                        else:
                            print(f"No results parsed for '{subcat}' at {lat:.6f},{lon:.6f}")
                    except Exception as e:
                        print(f"Error scraping '{subcat}' at {lat},{lon}: {e}")

                    # small pause between searches to be polite
                    time.sleep(1)

            lon += step_lon
            col += 1

        lat += step_lat
        row += 1

# ---------------------------
# Main entrypoint
# ---------------------------
def main():
    print("Starting grid POI scrape...")
    ensure_dirs()

    chrome_opts = Options()
    if HEADLESS:
        chrome_opts.add_argument("--headless=new")
        chrome_opts.add_argument("--window-size=1920,1080")
    else:
        chrome_opts.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=chrome_opts)  # Selenium Manager should auto-handle chromedriver

    try:
        # open maps once
        driver.get("https://www.google.com/maps")
        time.sleep(2)

        run_grid_scrape(
            driver,
            start_lat=START_LAT,
            start_lon=START_LON,
            end_lat=END_LAT,
            end_lon=END_LON,
            step_lat=STEP_LAT,
            step_lon=STEP_LON,
            categories=CATEGORIES
        )

        print("Grid scraping finished.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

# auto-commit
