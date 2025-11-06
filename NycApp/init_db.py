import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from config.database import init_db
from services.data_sync import manual_sync, load_from_csv, DataSyncService


def initialize():
    print("Initializing database...")
    init_db()
    print("Database initialized successfully")

    print("\nChecking for existing CSV data...")
    data_dir = Path(__file__).parent / "data"
    csv_files_exist = all([
        (data_dir / "nyc_zip_list.csv").exists(),
        (data_dir / "nyc_rent.csv").exists(),
        (data_dir / "nyc_income.csv").exists(),
        (data_dir / "nyc_burden.csv").exists(),
        (data_dir / "nyc_housing.csv").exists(),
        (data_dir / "nyc_vacancy.csv").exists()
    ])

    pluto_csv_exists = (data_dir / "pluto_residential.csv").exists()

    if csv_files_exist:
        print("CSV files found. Loading data from CSV...")
        try:
            records = load_from_csv()
            print(f"Successfully loaded {records} records from CSV files")

            if pluto_csv_exists:
                print("\nLoading PLUTO building data from CSV...")
                try:
                    sync_service = DataSyncService()
                    pluto_records = sync_service.load_pluto_from_csv()
                    print(f"Successfully loaded {pluto_records} building records from PLUTO CSV")
                except Exception as e:
                    print(f"Warning: Failed to load PLUTO data: {e}")

            return True
        except Exception as e:
            print(f"Error loading from CSV: {e}")
            print("Falling back to API sync...")
    else:
        print("CSV files not found. Will sync from APIs...")

    print("\nSyncing data from APIs...")
    try:
        records = manual_sync()
        print(f"Successfully synced {records} records from APIs")
    except Exception as e:
        print(f"Error syncing data: {e}")
        return False

    return True


if __name__ == "__main__":
    success = initialize()
    if success:
        print("\nInitialization complete! You can now run: streamlit run app.py")
    else:
        print("\nInitialization failed. Please check the errors above.")
