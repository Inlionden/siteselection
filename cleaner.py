import pandas as pd
from sklearn.impute import SimpleImputer
import os
import config

def run_cleaner():
    input_file = config.COMBINED_CSV
    output_file = config.CLEAN_DATA_FILE

    print(f"Reading from {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: {input_file} not found. Run the scraper first.")
        return

    print("Removing duplicates...")
    initial_len = len(df)
    df = df.drop_duplicates()
    print(f"Removed {initial_len - len(df)} duplicate rows.")

    print("Imputing missing Latitude/Longitude...")
    cols = ['Latitude', 'Longitude']
    # Ensure numeric
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Impute if needed
    if df[cols].isnull().any().any():
        imputer = SimpleImputer(strategy='mean')
        df[cols] = imputer.fit_transform(df[cols])
        print("Imputation information: Filled missing coordinates with column mean.")
    else:
        print("No missing values found in coordinates.")

    print(f"Saving cleaned data to {output_file}...")
    df.to_csv(output_file, index=False)
    print("Cleaning Done.")

if __name__ == "__main__":
    run_cleaner()
