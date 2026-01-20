import pandas as pd
from sklearn.impute import SimpleImputer
import os

def clean_data():
    input_file = os.path.join('Dataset', 'dataset.csv')
    output_file = os.path.join('Dataset', 'updated_dataset1.csv')

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
    # Clean non-numeric values first if any "N/A" strings exist
    cols = ['Latitude', 'Longitude']
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    if df[cols].isnull().any().any():
        imputer = SimpleImputer(strategy='mean')
        df[cols] = imputer.fit_transform(df[cols])
        print("Imputation complete.")
    else:
        print("No missing values found in coordinates.")

    print(f"Saving to {output_file}...")
    df.to_csv(output_file, index=False)
    print("Done.")

if __name__ == "__main__":
    clean_data()

# auto-commit
