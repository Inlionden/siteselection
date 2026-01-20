import os

# Paths
OUTPUT_DIR = "Dataset"
COMBINED_CSV = os.path.join(OUTPUT_DIR, "dataset.csv")
PER_CATEGORY_DIR = os.path.join(OUTPUT_DIR, "categories")
CLEAN_DATA_FILE = os.path.join(OUTPUT_DIR, "updated_dataset1.csv")

# Scraper Settings
TAKE_SCREENSHOTS = True   # Enabled by request
HEADLESS = False          # Set True to run without browser window
PAUSE_AFTER_LOAD = 3      # Seconds to wait after searching
ZOOM = 15                 # Map zoom level

# Grid Area (Start/End Lat/Lon)
START_LAT = 38.836359
START_LON = -77.048358
END_LAT = 38.974690
END_LON = -77.013404

# Grid Spacing (~1km)
STEP_LAT = 0.02
STEP_LON = 0.02

# Search Limits
NUM_RESULTS_PER_SEARCH = 10

# Categories to search
CATEGORIES = {
    "Event Venue": [
        "Conference Center", "Convention Center", "Stadium", "Arena"
    ],
}

# auto-commit
