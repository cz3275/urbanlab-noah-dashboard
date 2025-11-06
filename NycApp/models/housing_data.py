from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from config.database import Base

class ZipCode(Base):
    __tablename__ = "zip_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    zip = Column(String(5), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class HousingMetrics(Base):
    __tablename__ = "housing_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    zip = Column(String(5), index=True, nullable=False)
    name = Column(String(100))
    median_rent = Column(Float)
    median_income = Column(Float)
    rent_burden = Column(Float)
    rent_burden_rate = Column(Float)
    housing_units = Column(Integer)
    total_units = Column(Integer)
    occupied_units = Column(Integer)
    vacant_units = Column(Integer)
    vacancy_rate = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BuildingInfo(Base):
    __tablename__ = "building_info"
    
    id = Column(Integer, primary_key=True, index=True)
    bbl = Column(String(20), unique=True, index=True, nullable=False)
    landuse = Column(String(10))
    yearbuilt = Column(Integer)
    numfloors = Column(Integer)
    unitsres = Column(Integer)
    address = Column(String(200))
    zipcode = Column(String(5), index=True)
    borough = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BuildingStats(Base):
    __tablename__ = "building_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    zip = Column(String(5), unique=True, index=True, nullable=False)
    total_buildings = Column(Integer)
    avg_floors = Column(Float)
    avg_year_built = Column(Integer)
    total_residential_units = Column(Integer)
    buildings_pre_1950 = Column(Integer)
    buildings_1950_2000 = Column(Integer)
    buildings_post_2000 = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    sync_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    records_processed = Column(Integer, default=0)
    error_message = Column(Text)
    sync_time = Column(DateTime(timezone=True), server_default=func.now())

