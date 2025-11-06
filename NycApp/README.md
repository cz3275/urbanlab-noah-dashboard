# NYC Housing Data Explorer

Professional data visualization application for exploring New York City housing metrics and building information.

## Quick Start

```bash
conda activate nyc
cd D:\CodeSpace\Python\NewNycHouseApp
python init_db.py
streamlit run app.py
```

Visit: http://localhost:8501

## Features

### Interactive Map with 3-Tab Popup
Click any ZIP marker to view detailed information in 3 tabs:
- **Housing**: Rent, income, vacancy rate, housing units
- **Building Stats**: Total buildings, average floors, construction years
- **Buildings**: List of actual buildings with details

### Year Range Filter
Filter buildings by construction year (1800-2025) in Data Filters section.

### Auto Data Sync
- Configure in sidebar: Data Management
- Choose interval: 6h / 12h / 24h / 48h / 7 days
- Select data sources: Census (fast) / PLUTO (slow)

### Manual Sync Options
- Sync Census: Housing metrics only (1-2 min)
- Sync PLUTO: Building data only (5-10 min)
- Sync All: Complete data update

## Data Metrics

### Housing (Census ACS 2022)
- Median Rent
- Median Income
- Vacancy Rate
- Housing Units

### Buildings (NYC PLUTO)
- Total Buildings
- Average Floors
- Average Year Built
- By Era: Pre-1950 / 1950-2000 / Post-2000

## Project Structure

```
NewNycHouseApp/
├── app.py                    Main application
├── init_db.py               Database initialization
├── components/
│   ├── map_layers.py       Map with 3-tab popup
│   ├── sidebar.py          Controls and filters
│   └── statistics.py       Charts and analytics
├── services/
│   ├── data_service.py     Data queries
│   ├── data_sync.py        API integration
│   └── auto_sync.py        Auto sync manager
├── models/
│   └── housing_data.py     Database models
├── data/
│   ├── nyc_housing.db      SQLite database
│   ├── update_data.py      Data fetcher
│   └── *.csv               Data files
```

## Database Schema

- zip_codes: NYC ZIP code list
- housing_metrics: Census ACS data (177 ZIPs)
- building_info: PLUTO buildings (100K records)
- building_stats: Aggregated stats (179 ZIPs)
- sync_logs: Sync history

## Data Sources

- Census Bureau: American Community Survey 5-Year 2022
- NYC Open Data: PLUTO (Primary Land Use Tax Lot Output)
- NYC Open Data: Modified ZCTA Boundaries

## Technical Stack

- Python 3.x + Streamlit 1.31.0
- Folium 0.14.0 + Plotly 5.18.0
- SQLAlchemy 2.0.25 + Pandas 2.1.4
- Schedule 1.2.1

## Configuration

### Auto Sync Config

```json
{
  "enabled": true,
  "interval_hours": 24,
  "sync_census": true,
  "sync_pluto": false
}
```

### API Token (Optional)

```bash
set SOCRATA_APP_TOKEN=your_token_here
```

Get token at: https://data.cityofnewyork.us/profile/app_tokens

## Update Data

### Full Update

```bash
python data/update_data.py
python init_db.py
```

### PLUTO Only

```bash
cd data
python fetch_pluto_residential.py --year-min 1900 --year-max 2025 --limit 100000
```

### Custom Year Range

```bash
python data/update_data.py --year-min 1950 --year-max 2020
python data/update_data.py --skip-pluto
```

## Usage Tips

### View Building Information
1. Click any ZIP marker on the map
2. Click tabs to switch between Housing, Building Stats, and Buildings

### Configure Year Filter
1. Sidebar: Data Filters
2. Enable "Enable Building Year Filter"
3. Adjust year range slider
4. Building list in popup shows filtered results

### Configure Auto Sync
1. Sidebar: Data Management
2. Enable Auto Sync
3. Select interval (recommend 24 hours)
4. Choose Census Data (lightweight)
5. Optionally select PLUTO Data (large dataset)

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Popup load | <100ms | Instant |
| Tab switch | Instant | JavaScript |
| Census sync | 1-2 min | Lightweight |
| PLUTO sync | 5-10 min | 100K records |

## Troubleshooting

**Database not found**
```bash
python init_db.py
```

**Tabs not clicking**
- Clear browser cache (Ctrl+Shift+R)
- Restart Streamlit
- Check browser console for errors

**Sync fails**
- Check internet connection
- Set SOCRATA_APP_TOKEN
- Use pre-fetched CSV files

**No building data in popup**
- Normal for commercial/industrial ZIPs
- Only residential buildings included

## Testing

Test with conda environment:
```bash
cd C:\Users\win\miniconda3
conda activate nyc
cd D:\CodeSpace\Python\NewNycHouseApp
streamlit run app.py
```

## License

Educational and research use only.

## Credits

- US Census Bureau (ACS data)
- NYC Department of City Planning (PLUTO)
- NYC Open Data (APIs and datasets)

---

**Version**: 2.5
**Last Updated**: 2025-10-07

**Latest Fixes (v2.5)**:
- Fixed PostgreSQL sync errors (numpy type adaptation and error message length)
- Added automatic numpy to Python native type conversion
- Changed error_message field from VARCHAR(500) to TEXT
- All data types now compatible with both SQLite and PostgreSQL
- Manual and automatic sync now work reliably with both databases

**Previous Fixes (v2.4)**:
- Fixed tab clicking with IIFE (Immediately Invoked Function Expression)
- Fixed ZIP code format in BuildingInfo (was 11427.0, now 11427)
- Regenerated BuildingStats with correct ZIP matching
- All 179 ZIPs now have correct building statistics
- Data sync scripts ensure proper ZIP format for future imports
