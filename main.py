import os
import sys
import subprocess

def main():
    while True:
        print("\n=== Google Maps Scraper Project ===")
        print("1. Run Scraper (collect data + screenshots)")
        print("2. Run Cleaner (remove duplicates + impute)")
        print("3. Run GUI (Streamlit + Folium)")
        print("4. Exit")
        
        choice = input("Enter choice (1-4): ").strip()

        if choice == '1':
            import scraper
            scraper.run_scraper()
            
        elif choice == '2':
            import cleaner
            cleaner.run_cleaner()
            
        elif choice == '3':
            print("Launching Streamlit GUI...")
            # Streamlit needs to run as a subprocess command
            subprocess.run(["streamlit", "run", "gui.py"])
            
        elif choice == '4':
            print("Exiting.")
            sys.exit(0)
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()
