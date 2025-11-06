import requests
import pandas as pd
import numpy as np
import os
import time
import math
from pathlib import Path
from sqlalchemy.orm import Session
from models.housing_data import ZipCode, HousingMetrics, SyncLog, BuildingInfo, BuildingStats
from config.database import SessionLocal
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ACS_YEAR = "2022"
ACS_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
NYC_ZIP_URL = "https://data.cityofnewyork.us/resource/pri4-ifjk.json?$select=modzcta&$limit=300"
PLUTO_API = "https://data.cityofnewyork.us/resource/64uk-42ks.json"

def convert_to_native_type(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, np.bool_):
        return bool(val)
    return val

class DataSyncService:
    def __init__(self):
        self.db = SessionLocal()
    
    def __del__(self):
        self.db.close()
    
    def log_sync(self, sync_type: str, status: str, records: int = 0, error: str = None):
        log = SyncLog(
            sync_type=sync_type,
            status=status,
            records_processed=records,
            error_message=error
        )
        self.db.add(log)
        self.db.commit()
    
    def fetch_nyc_zip_list(self):
        try:
            r = requests.get(NYC_ZIP_URL, timeout=30)
            r.raise_for_status()
            df = pd.DataFrame(r.json())
            df["zip"] = df["modzcta"].astype(str).str.zfill(5)
            df = df[["zip"]].drop_duplicates().sort_values("zip")
            
            self.db.query(ZipCode).delete()
            for _, row in df.iterrows():
                zip_code = ZipCode(zip=row["zip"])
                self.db.add(zip_code)
            
            self.db.commit()
            self.log_sync("nyc_zip_list", "success", len(df))
            return set(df["zip"].tolist())
        except Exception as e:
            self.log_sync("nyc_zip_list", "failed", 0, str(e))
            raise
    
    def census_fetch(self, vars_, rename_map):
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
        df = df.drop(columns=["zip code tabulation area"], errors="ignore")
        return df
    
    def sync_all_data(self):
        try:
            nyc_zips = self.fetch_nyc_zip_list()
            
            rent = self.census_fetch(["B25064_001E"], {"B25064_001E": "median_rent"})
            income = self.census_fetch(["B19013_001E"], {"B19013_001E": "median_income"})
            burden = self.census_fetch(["B25070_001E"], {"B25070_001E": "rent_burden"})
            housing = self.census_fetch(["B25001_001E"], {"B25001_001E": "housing_units"})
            vacancy = self.census_fetch(
                ["B25002_001E","B25002_002E","B25002_003E"],
                {
                    "B25002_001E":"total_units",
                    "B25002_002E":"occupied_units",
                    "B25002_003E":"vacant_units"
                }
            )
            
            for c in ["total_units","occupied_units","vacant_units"]:
                vacancy[c] = pd.to_numeric(vacancy[c], errors="coerce")
            vacancy["vacancy_rate"] = (vacancy["vacant_units"]/vacancy["total_units"]).round(4)
            
            merged = rent.merge(income, on=["zip", "NAME"], how="outer")
            merged = merged.merge(burden, on=["zip", "NAME"], how="outer")
            merged = merged.merge(housing, on=["zip", "NAME"], how="outer")
            merged = merged.merge(vacancy, on=["zip", "NAME"], how="outer")
            
            nyc_data = merged[merged["zip"].isin(nyc_zips)].copy()
            
            self.db.query(HousingMetrics).delete()
            
            for _, row in nyc_data.iterrows():
                median_rent = pd.to_numeric(row.get("median_rent"), errors="coerce")
                median_income = pd.to_numeric(row.get("median_income"), errors="coerce")
                rent_burden = pd.to_numeric(row.get("rent_burden"), errors="coerce")
                housing_units = pd.to_numeric(row.get("housing_units"), errors="coerce")
                
                if pd.notna(median_rent) and median_rent < 0:
                    median_rent = None
                if pd.notna(median_income) and median_income < 0:
                    median_income = None
                else:
                    if pd.notna(median_income):
                        median_income = median_income / 12
                if pd.notna(rent_burden) and rent_burden < 0:
                    rent_burden = None
                if pd.notna(housing_units) and housing_units < 0:
                    housing_units = None
                
                rent_burden_rate = None
                if pd.notna(median_rent) and pd.notna(median_income) and median_income > 0:
                    rent_burden_rate = (median_rent / median_income) * 100
                
                metric = HousingMetrics(
                    zip=str(row["zip"]),
                    name=str(row.get("NAME")) if pd.notna(row.get("NAME")) else None,
                    median_rent=convert_to_native_type(median_rent),
                    median_income=convert_to_native_type(median_income),
                    rent_burden=convert_to_native_type(rent_burden),
                    rent_burden_rate=convert_to_native_type(rent_burden_rate),
                    housing_units=convert_to_native_type(housing_units),
                    total_units=convert_to_native_type(pd.to_numeric(row.get("total_units"), errors="coerce")),
                    occupied_units=convert_to_native_type(pd.to_numeric(row.get("occupied_units"), errors="coerce")),
                    vacant_units=convert_to_native_type(pd.to_numeric(row.get("vacant_units"), errors="coerce")),
                    vacancy_rate=convert_to_native_type(pd.to_numeric(row.get("vacancy_rate"), errors="coerce"))
                )
                self.db.add(metric)
            
            self.db.commit()
            self.log_sync("full_sync", "success", len(nyc_data))
            return len(nyc_data)
        except Exception as e:
            self.db.rollback()
            self.log_sync("full_sync", "failed", 0, str(e))
            raise

    def load_from_csv(self):
        try:
            zip_list_path = DATA_DIR / "nyc_zip_list.csv"
            rent_path = DATA_DIR / "nyc_rent.csv"
            income_path = DATA_DIR / "nyc_income.csv"
            burden_path = DATA_DIR / "nyc_burden.csv"
            housing_path = DATA_DIR / "nyc_housing.csv"
            vacancy_path = DATA_DIR / "nyc_vacancy.csv"
            
            if not all([p.exists() for p in [zip_list_path, rent_path, income_path, burden_path, housing_path, vacancy_path]]):
                raise FileNotFoundError("One or more CSV files not found in data directory")
            
            zip_list_df = pd.read_csv(zip_list_path)
            nyc_zips = set(zip_list_df["zip"].astype(str).str.zfill(5).tolist())
            
            self.db.query(ZipCode).delete()
            for zip_code in sorted(nyc_zips):
                zip_obj = ZipCode(zip=zip_code)
                self.db.add(zip_obj)
            self.db.commit()
            
            rent = pd.read_csv(rent_path)
            income = pd.read_csv(income_path)
            burden = pd.read_csv(burden_path)
            housing = pd.read_csv(housing_path)
            vacancy = pd.read_csv(vacancy_path)
            
            for df in [rent, income, burden, housing, vacancy]:
                df["zip"] = df["zip"].astype(str).str.zfill(5)
                df.drop(columns=["zip code tabulation area"], errors="ignore", inplace=True)
            
            merged = rent[["zip", "NAME", "median_rent"]].merge(
                income[["zip", "median_income"]], on="zip", how="outer"
            )
            merged = merged.merge(burden[["zip", "rent_burden"]], on="zip", how="outer")
            merged = merged.merge(housing[["zip", "housing_units"]], on="zip", how="outer")
            merged = merged.merge(
                vacancy[["zip", "total_units", "occupied_units", "vacant_units", "vacancy_rate"]], 
                on="zip", how="outer"
            )
            
            self.db.query(HousingMetrics).delete()
            
            for _, row in merged.iterrows():
                median_rent = pd.to_numeric(row.get("median_rent"), errors="coerce")
                median_income = pd.to_numeric(row.get("median_income"), errors="coerce")
                rent_burden = pd.to_numeric(row.get("rent_burden"), errors="coerce")
                housing_units = pd.to_numeric(row.get("housing_units"), errors="coerce")
                
                if pd.notna(median_rent) and median_rent < 0:
                    median_rent = None
                if pd.notna(median_income) and median_income < 0:
                    median_income = None
                else:
                    if pd.notna(median_income):
                        median_income = median_income / 12
                if pd.notna(rent_burden) and rent_burden < 0:
                    rent_burden = None
                if pd.notna(housing_units) and housing_units < 0:
                    housing_units = None
                
                rent_burden_rate = None
                if pd.notna(median_rent) and pd.notna(median_income) and median_income > 0:
                    rent_burden_rate = (median_rent / median_income) * 100
                
                metric = HousingMetrics(
                    zip=str(row["zip"]),
                    name=str(row.get("NAME")) if pd.notna(row.get("NAME")) else None,
                    median_rent=convert_to_native_type(median_rent),
                    median_income=convert_to_native_type(median_income),
                    rent_burden=convert_to_native_type(rent_burden),
                    rent_burden_rate=convert_to_native_type(rent_burden_rate),
                    housing_units=convert_to_native_type(housing_units),
                    total_units=convert_to_native_type(pd.to_numeric(row.get("total_units"), errors="coerce")),
                    occupied_units=convert_to_native_type(pd.to_numeric(row.get("occupied_units"), errors="coerce")),
                    vacant_units=convert_to_native_type(pd.to_numeric(row.get("vacant_units"), errors="coerce")),
                    vacancy_rate=convert_to_native_type(pd.to_numeric(row.get("vacancy_rate"), errors="coerce"))
                )
                self.db.add(metric)
            
            self.db.commit()
            self.log_sync("csv_load", "success", len(merged))
            return len(merged)
        except Exception as e:
            self.db.rollback()
            self.log_sync("csv_load", "failed", 0, str(e))
            raise
    
    def fetch_pluto_residential(self, year_min=None, year_max=None, borough=None,
                                limit=100000, page_size=5000, sleep=0.15):
        try:
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
        except Exception as e:
            raise Exception(f"Failed to fetch PLUTO data: {str(e)}")
    
    def sync_pluto_data(self, year_min=1900, year_max=2025, limit=100000):
        try:
            df = self.fetch_pluto_residential(year_min=year_min, year_max=year_max, limit=limit)
            
            self.db.query(BuildingInfo).delete()
            
            for _, row in df.iterrows():
                zipcode_val = row.get("zipcode")
                if pd.notna(zipcode_val):
                    try:
                        zipcode_str = str(int(float(zipcode_val))).zfill(5)
                    except:
                        zipcode_str = str(zipcode_val).zfill(5)
                else:
                    zipcode_str = None
                
                building = BuildingInfo(
                    bbl=str(row.get("bbl")),
                    landuse=str(row.get("landuse")) if pd.notna(row.get("landuse")) else None,
                    yearbuilt=convert_to_native_type(row.get("yearbuilt")),
                    numfloors=convert_to_native_type(row.get("numfloors")),
                    unitsres=convert_to_native_type(row.get("unitsres")),
                    address=str(row.get("address")) if pd.notna(row.get("address")) else None,
                    zipcode=zipcode_str,
                    borough=str(row.get("borough")) if pd.notna(row.get("borough")) else None
                )
                self.db.add(building)
            
            self.db.commit()
            
            self.calculate_building_stats()
            
            self.log_sync("pluto_sync", "success", len(df))
            return len(df)
        except Exception as e:
            self.db.rollback()
            self.log_sync("pluto_sync", "failed", 0, str(e))
            raise
    
    def load_pluto_from_csv(self):
        try:
            pluto_path = DATA_DIR / "pluto_residential.csv"
            
            if not pluto_path.exists():
                raise FileNotFoundError(f"PLUTO CSV file not found: {pluto_path}")
            
            df = pd.read_csv(pluto_path)
            
            self.db.query(BuildingInfo).delete()
            
            for _, row in df.iterrows():
                zipcode_val = row.get("zipcode")
                if pd.notna(zipcode_val):
                    try:
                        zipcode_str = str(int(float(zipcode_val))).zfill(5)
                    except:
                        zipcode_str = str(zipcode_val).zfill(5)
                else:
                    zipcode_str = None
                
                building = BuildingInfo(
                    bbl=str(row.get("bbl")),
                    landuse=str(row.get("landuse")) if pd.notna(row.get("landuse")) else None,
                    yearbuilt=convert_to_native_type(row.get("yearbuilt")),
                    numfloors=convert_to_native_type(row.get("numfloors")),
                    unitsres=convert_to_native_type(row.get("unitsres")),
                    address=str(row.get("address")) if pd.notna(row.get("address")) else None,
                    zipcode=zipcode_str,
                    borough=str(row.get("borough")) if pd.notna(row.get("borough")) else None
                )
                self.db.add(building)
            
            self.db.commit()
            
            self.calculate_building_stats()
            
            self.log_sync("pluto_csv_load", "success", len(df))
            return len(df)
        except Exception as e:
            self.db.rollback()
            self.log_sync("pluto_csv_load", "failed", 0, str(e))
            raise
    
    def calculate_building_stats(self):
        try:
            buildings_query = self.db.query(BuildingInfo).filter(BuildingInfo.zipcode.isnot(None))
            df = pd.read_sql(buildings_query.statement, self.db.bind)
            
            if df.empty:
                return
            
            self.db.query(BuildingStats).delete()
            
            for zip_code in df['zipcode'].unique():
                zip_df = df[df['zipcode'] == zip_code]
                
                total_buildings = len(zip_df)
                
                valid_floors = zip_df[zip_df['numfloors'].notna()]['numfloors']
                avg_floors = float(valid_floors.mean()) if not valid_floors.empty else None
                
                valid_years = zip_df[zip_df['yearbuilt'].notna()]['yearbuilt']
                avg_year_built = int(valid_years.mean()) if not valid_years.empty else None
                
                total_units = zip_df['unitsres'].sum() if 'unitsres' in zip_df.columns else 0
                
                pre_1950 = len(zip_df[(zip_df['yearbuilt'].notna()) & (zip_df['yearbuilt'] < 1950)])
                y1950_2000 = len(zip_df[(zip_df['yearbuilt'].notna()) & 
                                       (zip_df['yearbuilt'] >= 1950) & 
                                       (zip_df['yearbuilt'] <= 2000)])
                post_2000 = len(zip_df[(zip_df['yearbuilt'].notna()) & (zip_df['yearbuilt'] > 2000)])
                
                stats = BuildingStats(
                    zip=str(zip_code),
                    total_buildings=convert_to_native_type(total_buildings),
                    avg_floors=convert_to_native_type(avg_floors),
                    avg_year_built=convert_to_native_type(avg_year_built),
                    total_residential_units=convert_to_native_type(total_units) if pd.notna(total_units) else 0,
                    buildings_pre_1950=convert_to_native_type(pre_1950),
                    buildings_1950_2000=convert_to_native_type(y1950_2000),
                    buildings_post_2000=convert_to_native_type(post_2000)
                )
                self.db.add(stats)
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to calculate building stats: {str(e)}")

def manual_sync():
    service = DataSyncService()
    return service.sync_all_data()

def load_from_csv():
    service = DataSyncService()
    return service.load_from_csv()
