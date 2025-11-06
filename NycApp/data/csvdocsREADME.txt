1.nyc_zip_list.csv
Source: NYC Open Data – Modified ZCTA Boundaries (MODZCTA)
Dataset ID: pri4-ifjk
API:
https://data.cityofnewyork.us/resource/pri4-ifjk.json?$select=modzcta&$limit=300
Description: Lists all valid NYC ZIPs (MODZCTA, equivalent to ZIP–ZCTA correspondence table).
Purpose: Used to filter ACS national ZCTA data to retain only NYC area.
Field Description:
zip: ZIP code identifying the postal area within New York City

2.nyc_rent.csv
Source: US Census Bureau – American Community Survey (ACS) 5-Year (2022)
Table: B25064 – Median Gross Rent
Variable ID: B25064_001E
API:
https://api.census.gov/data/2022/acs/acs5?get=NAME,B25064_001E&for=zip%20code%20tabulation%20area:*
Purpose: Median gross rent (monthly) at ZIP level, used to measure housing cost.
Field Description:
NAME: Area name, formatted as ZCTA5 + ZIP code
median_rent: Median rent, monthly median rent in the area (USD)
zip code tabulation area: ZIP Code Tabulation Area, standard area code used by the Census Bureau
zip: ZIP code, standard 5-digit postal code

3.nyc_income.csv
Source: US Census Bureau – ACS 5-Year (2022)
Table: B19013 – Median Household Income
Variable ID: B19013_001E
API:
https://api.census.gov/data/2022/acs/acs5?get=NAME,B19013_001E&for=zip%20code%20tabulation%20area:*
Purpose: Median household income at ZIP level, used to calculate rent affordability.
Field Description:
NAME: Area name, formatted as ZCTA5 + ZIP code
median_income: Median household income, annual household median income in the area (USD)
zip code tabulation area: ZIP Code Tabulation Area
zip: ZIP code

4.nyc_burden.csv
Source: US Census Bureau – ACS 5-Year (2022)
Table: B25070 – Gross Rent as a Percentage of Household Income
Variable ID: B25070_001E
API:
https://api.census.gov/data/2022/acs/acs5?get=NAME,B25070_001E&for=zip%20code%20tabulation%20area:*
Purpose: Rent burden indicator, measuring the share of household income spent on rent.
Field Description:
NAME: Area name
rent_burden: Rent burden rate, percentage of household income spent on rent (over 30% is considered overburdened)
zip code tabulation area: ZIP Code Tabulation Area

5.zip: ZIP code
nyc_housing.csv
Source: US Census Bureau – ACS 5-Year (2022)
Table: B25001 – Housing Units
Variable ID: B25001_001E
API:
https://api.census.gov/data/2022/acs/acs5?get=NAME,B25001_001E&for=zip%20code%20tabulation%20area:*
Purpose: Total housing stock at ZIP level (total number of housing units).
Field Description:
NAME: Area name
housing_units: Total number of housing units in the area
zip code tabulation area: ZIP Code Tabulation Area
zip: ZIP code

6.nyc_vacancy.csv
Source: US Census Bureau – ACS 5-Year (2022)
Table: B25002 – Occupancy Status
Variable ID:
B25002_001E: Total Units
B25002_002E: Occupied Units
B25002_003E: Vacant Units
API:
https://api.census.gov/data/2022/acs/acs5?get=NAME,B25002_001E,B25002_002E,B25002_003E&for=zip%20code%20tabulation%20area:*
Purpose: Used to calculate vacancy rate = Vacant ÷ Total, indicating housing market tightness.
Field Description:
NAME: Area name
total_units: Total housing units
occupied_units: Number of occupied units
vacant_units: Number of vacant units
zip code tabulation area: ZIP Code Tabulation Area
zip: ZIP code
vacancy_rate: Vacancy rate, calculated as vacant units ÷ total units, reflecting housing market supply-demand balance


