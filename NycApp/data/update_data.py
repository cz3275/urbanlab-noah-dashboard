# update_data.py
import requests
import pandas as pd
import os
import time
import math
import argparse
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True, parents=True)

ACS_YEAR = "2022"
ACS_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"

# NYC MODZCTA  to ZIP list
NYC_ZIP_URL = "https://data.cityofnewyork.us/resource/pri4-ifjk.json?$select=modzcta&$limit=300"
PLUTO_API = "https://data.cityofnewyork.us/resource/64uk-42ks.json"

def save_csv(df, name):
    out = DATA_DIR / name
    df.to_csv(out, index=False)
    print(f"✅ Saved {out} with {len(df)} rows")

def fetch_nyc_zip_list():
    r = requests.get(NYC_ZIP_URL, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["zip"] = df["modzcta"].astype(str).str.zfill(5)
    df = df[["zip"]].drop_duplicates().sort_values("zip")
    save_csv(df, "nyc_zip_list.csv")
    return set(df["zip"].tolist())

def census_fetch(vars_, rename_map):
    params = {
        "get": "NAME," + ",".join(vars_),
        "for": "zip code tabulation area:*",
    }
    r = requests.get(ACS_BASE, params=params, timeout=90)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    df["zip"] = df["zip code tabulation area"].astype(str).str.zfill(5)
    df = df.rename(columns=rename_map)
    return df

def fetch_pluto_residential(year_min=None, year_max=None, borough=None, 
                            limit=100000, page_size=5000, sleep=0.15):
    app_token = os.getenv("SOCRATA_APP_TOKEN")
    
    where_clauses = ["landuse in('01','02','03')"]
    if year_min is not None:
        where_clauses.append(f"yearbuilt >= {int(year_min)}")
    if year_max is not None:
        where_clauses.append(f"yearbuilt <= {int(year_max)}")
    if borough:
        where_clauses.append(f"upper(borough) = '{borough.upper()}'")
    where_sql = " AND ".join(where_clauses)
    
    select_fields = [
        "bbl", "landuse", "yearbuilt", "numfloors", "unitsres",
        "address", "zipcode", "borough"
    ]
    select_sql = ",".join(select_fields)
    
    frames = []
    pages = math.ceil(limit / page_size)
    for i in range(pages):
        offset = i * page_size
        params = {
            "$select": select_sql,
            "$where": where_sql,
            "$order": "yearbuilt DESC",
            "$limit": page_size,
            "$offset": offset
        }
        
        headers = {}
        if app_token:
            headers["X-App-Token"] = app_token
        
        r = requests.get(PLUTO_API, params=params, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        
        if not data:
            break
        frames.append(pd.DataFrame(data))
        print(f"Fetched page {i+1}/{pages} with {len(data)} records")
        if len(data) < page_size:
            break
        time.sleep(sleep)
    
    if not frames:
        return pd.DataFrame(columns=select_fields)
    
    df = pd.concat(frames, ignore_index=True)
    
    for col in ["yearbuilt", "numfloors", "unitsres", "zipcode"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "bbl" in df.columns:
        df["bbl"] = df["bbl"].astype(str)
    
    return df[select_fields]

def main():
    parser = argparse.ArgumentParser(description="Update NYC housing and PLUTO data")
    parser.add_argument("--year-min", type=int, default=1900, help="Minimum building year for PLUTO data")
    parser.add_argument("--year-max", type=int, default=2025, help="Maximum building year for PLUTO data")
    parser.add_argument("--skip-pluto", action="store_true", help="Skip PLUTO data fetch")
    args = parser.parse_args()
    
    print("Fetching NYC ZIP codes...")
    nyc_zips = fetch_nyc_zip_list()

    print("\nFetching Census ACS data...")
    rent = census_fetch(["B25064_001E"], {"B25064_001E": "median_rent"})
    income = census_fetch(["B19013_001E"], {"B19013_001E": "median_income"})
    burden = census_fetch(["B25070_001E"], {"B25070_001E": "rent_burden"})
    housing = census_fetch(["B25001_001E"], {"B25001_001E": "housing_units"})
    vacancy = census_fetch(
        ["B25002_001E","B25002_002E","B25002_003E"],
        {
            "B25002_001E":"total_units",
            "B25002_002E":"occupied_units",
            "B25002_003E":"vacant_units"
        }
    )
    # Vacancy rate calculation
    for c in ["total_units","occupied_units","vacant_units"]:
        vacancy[c] = pd.to_numeric(vacancy[c], errors="coerce")
    vacancy["vacancy_rate"] = (vacancy["vacant_units"]/vacancy["total_units"]).round(4)

    # NYC filtering
    print("\nSaving Census data...")
    for name, df in {
        "nyc_rent.csv": rent,
        "nyc_income.csv": income,
        "nyc_burden.csv": burden,
        "nyc_housing.csv": housing,
        "nyc_vacancy.csv": vacancy,
    }.items():
        df_nyc = df[df["zip"].isin(nyc_zips)].copy()
        save_csv(df_nyc, name)
    
    if not args.skip_pluto:
        print(f"\nFetching PLUTO building data (years {args.year_min}-{args.year_max})...")
        print("This may take several minutes...")
        pluto_df = fetch_pluto_residential(year_min=args.year_min, year_max=args.year_max, limit=100000)
        save_csv(pluto_df, "pluto_residential.csv")
    
    print("\nAll data fetched and saved successfully!")

if __name__ == "__main__":
    main()
