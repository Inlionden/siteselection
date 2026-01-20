import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import config
import utils

def parse_left_panel_pois(page_source, max_results=config.NUM_RESULTS_PER_SEARCH):
    """
    Parse POI items from the left result panel.
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
            if card.get('aria-label'):
                name = card['aria-label']
            elif card.name == 'a' and card.get('aria-label'):
                name = card['aria-label']
            
            if not name:
                name_tag = card.find('div', class_='qBF1Pd') or card.find('div', class_='fontHeadlineSmall')
                if name_tag:
                    name = name_tag.get_text(strip=True)
            
            if not name:
                name = card.get_text(strip=True)[:200]

            # Extract Rating
            rating_tag = card.find('span', class_='MW4etd') or card.find('span', {'aria-label': True})
            rating = rating_tag.get_text(strip=True) if rating_tag else ''

            # Extract Reviews
            reviews_tag = card.find('span', class_='UY7F9') or card.find('span', {'aria-hidden': True})
            raw_reviews = reviews_tag.get_text(strip=True) if reviews_tag else ''
            reviews = raw_reviews.strip('()')

            if name:
                candidates.append({
                    "name": name,
                    "link": link,
                    "rating": rating,
                    "reviews": reviews
                })
        except Exception:
            continue

    return candidates

def scrape_for_query(driver, query, lat, lon, max_results=config.NUM_RESULTS_PER_SEARCH, take_screenshot=False, row_idx=None, col_idx=None):
    url = utils.build_search_url(query, lat, lon)
    driver.get(url)
    time.sleep(config.PAUSE_AFTER_LOAD)

    page_source = driver.page_source
    pois = parse_left_panel_pois(page_source, max_results=max_results)

    rows = []
    for p in pois:
        plat, plon = utils.extract_coordinates_from_url(p.get('link', ''))
        
        if (plat is None) or (plon is None):
            plat, plon = lat, lon

        dist_m = utils.haversine_distance(lat, lon, plat, plon) if (plat and plon) else None

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

    # Screenshot handling (explicit Request)
    if take_screenshot:
        try:
            fname = f"shot_r{row_idx}_c{col_idx}_{lat:.6f}_{lon:.6f}.png"
            path = os.path.join(config.PER_CATEGORY_DIR, fname)
            driver.save_screenshot(path)
        except Exception as e:
            print(f"Screenshot failed: {e}")

    return rows

def run_scraper():
    print("Initializing Scraper...")
    utils.ensure_dirs()
    
    header = ["Name", "Rating", "Number of Reviews", "Latitude", "Longitude", "Search Query", "CenterLat", "CenterLon", "Distance_m"]
    # Initialize combined CSV if needed
    if not os.path.exists(config.COMBINED_CSV):
        utils.write_rows_to_csv(config.COMBINED_CSV, [], header=header)

    chrome_opts = Options()
    if config.HEADLESS:
        chrome_opts.add_argument("--headless=new")
    else:
        chrome_opts.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=chrome_opts)

    try:
        driver.get("https://www.google.com/maps")
        time.sleep(2)

        lat = config.START_LAT
        row = 0
        while lat <= config.END_LAT + 1e-12:
            lon = config.START_LON
            col = 0
            while lon <= config.END_LON + 1e-12:
                print(f"\n--- Grid ({row}, {col}) Center: {lat:.6f}, {lon:.6f} ---")
                
                for cat, subcats in config.CATEGORIES.items():
                    cat_dir = os.path.join(config.PER_CATEGORY_DIR, cat.replace(" ", "_"))
                    os.makedirs(cat_dir, exist_ok=True)

                    for subcat in subcats:
                        print(f" Searching: {subcat}")
                        rows = scrape_for_query(
                            driver, subcat, lat, lon,
                            max_results=config.NUM_RESULTS_PER_SEARCH,
                            take_screenshot=config.TAKE_SCREENSHOTS,
                            row_idx=row, col_idx=col
                        )
                        
                        if rows:
                            # Save subcategory file
                            safe_subcat = subcat.replace(' ', '_')
                            filename = os.path.join(cat_dir, f"{safe_subcat}.csv")
                            utils.write_rows_to_csv(filename, rows, header=header)
                            
                            # Save to combined
                            utils.write_rows_to_csv(config.COMBINED_CSV, rows)
                            print(f"  -> Found {len(rows)} POIs")
                        else:
                            print("  -> No results")
                        
                        time.sleep(1)

                lon += config.STEP_LON
                col += 1
            lat += config.STEP_LAT
            row += 1
            
        print("Scraping Completed!")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()

# auto-commit
