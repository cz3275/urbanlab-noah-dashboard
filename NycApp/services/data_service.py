import pandas as pd
from sqlalchemy.orm import Session
from models.housing_data import HousingMetrics, ZipCode, SyncLog, BuildingInfo, BuildingStats
from config.database import SessionLocal

class DataService:
    def __init__(self):
        self.db = SessionLocal()
    
    def __del__(self):
        self.db.close()
    
    def get_all_metrics(self) -> pd.DataFrame:
        metrics = self.db.query(HousingMetrics).all()
        data = []
        for m in metrics:
            data.append({
                "zip": m.zip,
                "name": m.name,
                "median_rent": m.median_rent,
                "median_income": m.median_income,
                "rent_burden": m.rent_burden,
                "rent_burden_rate": m.rent_burden_rate,
                "housing_units": m.housing_units,
                "total_units": m.total_units,
                "occupied_units": m.occupied_units,
                "vacant_units": m.vacant_units,
                "vacancy_rate": m.vacancy_rate
            })
        df = pd.DataFrame(data)
        
        for col in ['median_rent', 'median_income', 'rent_burden', 'rent_burden_rate', 'housing_units', 
                    'total_units', 'occupied_units', 'vacant_units', 'vacancy_rate']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def get_metrics_by_zip(self, zip_code: str) -> dict:
        metric = self.db.query(HousingMetrics).filter(HousingMetrics.zip == zip_code).first()
        if metric:
            return {
                "zip": metric.zip,
                "name": metric.name,
                "median_rent": metric.median_rent,
                "median_income": metric.median_income,
                "rent_burden": metric.rent_burden,
                "rent_burden_rate": metric.rent_burden_rate,
                "housing_units": metric.housing_units,
                "total_units": metric.total_units,
                "occupied_units": metric.occupied_units,
                "vacant_units": metric.vacant_units,
                "vacancy_rate": metric.vacancy_rate
            }
        return None
    
    def get_summary_stats(self) -> dict:
        metrics = self.db.query(HousingMetrics).all()
        if not metrics:
            return {}
        
        df = self.get_all_metrics()
        
        valid_rent = pd.to_numeric(df["median_rent"], errors='coerce').dropna()
        valid_income = pd.to_numeric(df["median_income"], errors='coerce').dropna()
        valid_vacancy = pd.to_numeric(df["vacancy_rate"], errors='coerce').dropna()
        valid_housing = pd.to_numeric(df["housing_units"], errors='coerce').dropna()
        
        return {
            "total_zips": len(df),
            "avg_median_rent": float(valid_rent.mean()) if not valid_rent.empty else 0,
            "avg_median_income": float(valid_income.mean()) if not valid_income.empty else 0,
            "avg_vacancy_rate": float(valid_vacancy.mean()) if not valid_vacancy.empty else 0,
            "total_housing_units": int(valid_housing.sum()) if not valid_housing.empty else 0
        }
    
    def get_last_sync_info(self) -> dict:
        last_sync = self.db.query(SyncLog).order_by(SyncLog.sync_time.desc()).first()
        if last_sync:
            return {
                "sync_type": last_sync.sync_type,
                "status": last_sync.status,
                "records": last_sync.records_processed,
                "time": last_sync.sync_time,
                "error": last_sync.error_message
            }
        return None
    
    def get_building_stats_by_zip(self, zip_code: str) -> dict:
        stats = self.db.query(BuildingStats).filter(BuildingStats.zip == zip_code).first()
        if stats:
            return {
                "zip": stats.zip,
                "total_buildings": stats.total_buildings,
                "avg_floors": stats.avg_floors,
                "avg_year_built": stats.avg_year_built,
                "total_residential_units": stats.total_residential_units,
                "buildings_pre_1950": stats.buildings_pre_1950,
                "buildings_1950_2000": stats.buildings_1950_2000,
                "buildings_post_2000": stats.buildings_post_2000
            }
        return None
    
    def get_all_building_stats(self) -> pd.DataFrame:
        stats = self.db.query(BuildingStats).all()
        data = []
        for s in stats:
            data.append({
                "zip": s.zip,
                "total_buildings": s.total_buildings,
                "avg_floors": s.avg_floors,
                "avg_year_built": s.avg_year_built,
                "total_residential_units": s.total_residential_units,
                "buildings_pre_1950": s.buildings_pre_1950,
                "buildings_1950_2000": s.buildings_1950_2000,
                "buildings_post_2000": s.buildings_post_2000
            })
        return pd.DataFrame(data)
    
    def get_buildings_by_zip(self, zip_code: str, limit: int = 100) -> pd.DataFrame:
        buildings = self.db.query(BuildingInfo).filter(
            BuildingInfo.zipcode == zip_code
        ).limit(limit).all()
        
        data = []
        for b in buildings:
            data.append({
                "bbl": b.bbl,
                "address": b.address,
                "landuse": b.landuse,
                "yearbuilt": b.yearbuilt,
                "numfloors": b.numfloors,
                "unitsres": b.unitsres,
                "borough": b.borough
            })
        return pd.DataFrame(data)
    
    def get_buildings_by_zip_filtered(self, zip_code: str, year_min: int = None, year_max: int = None, limit: int = 100) -> pd.DataFrame:
        query = self.db.query(BuildingInfo).filter(BuildingInfo.zipcode == zip_code)
        
        if year_min is not None:
            query = query.filter(BuildingInfo.yearbuilt >= year_min)
        if year_max is not None:
            query = query.filter(BuildingInfo.yearbuilt <= year_max)
        
        buildings = query.limit(limit).all()
        
        data = []
        for b in buildings:
            data.append({
                "bbl": b.bbl,
                "address": b.address,
                "landuse": b.landuse,
                "yearbuilt": b.yearbuilt,
                "numfloors": b.numfloors,
                "unitsres": b.unitsres,
                "borough": b.borough
            })
        return pd.DataFrame(data)
    
    def get_combined_metrics(self, zip_code: str) -> dict:
        housing_metrics = self.get_metrics_by_zip(zip_code)
        building_stats = self.get_building_stats_by_zip(zip_code)
        
        result = {}
        if housing_metrics:
            result.update(housing_metrics)
        if building_stats:
            result.update({
                "building_" + k: v for k, v in building_stats.items() if k != "zip"
            })
        
        return result if result else None
    
    def get_all_combined_metrics(self) -> pd.DataFrame:
        housing_df = self.get_all_metrics()
        building_df = self.get_all_building_stats()
        
        if housing_df.empty:
            return building_df
        if building_df.empty:
            return housing_df
        
        combined = housing_df.merge(building_df, on="zip", how="outer")
        return combined

