# -*- coding: utf-8 -*-
import os
import time
import math
import argparse
import requests
import pandas as pd

PLUTO_API = "https://data.cityofnewyork.us/resource/64uk-42ks.json"


def socrata_get(url, params=None, app_token=None, timeout=60):
    headers = {}
    if app_token:
        headers["X-App-Token"] = app_token
    r = requests.get(url, params=params or {}, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_pluto_residential(year_min=None, year_max=None, borough=None,
                            limit=100000, page_size=5000, app_token=None, sleep=0.15):

    # Land use
    where_clauses = ["landuse in('01','02','03')"]
    if year_min is not None:
        where_clauses.append(f"yearbuilt >= {int(year_min)}")
    if year_max is not None:
        where_clauses.append(f"yearbuilt <= {int(year_max)}")
    if borough:
        # 可选值：MANHATTAN, BRONX, BROOKLYN, QUEENS, STATEN ISLAND
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
        data = socrata_get(PLUTO_API, params=params, app_token=app_token)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        if len(data) < page_size:
            break
        time.sleep(sleep)  # 温和一点

    if not frames:
        return pd.DataFrame(columns=select_fields)

    df = pd.concat(frames, ignore_index=True)

    # Clean
    for col in ["yearbuilt", "numfloors", "unitsres", "zipcode"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "bbl" in df.columns:
        df["bbl"] = df["bbl"].astype(str)

    return df[select_fields]


def main():
    parser = argparse.ArgumentParser(description="Fetch NYC PLUTO residential attributes via API.")
    parser.add_argument("--year-min", type=int, default=None, help="最小建成年份（含）")
    parser.add_argument("--year-max", type=int, default=None, help="最大建成年份（含）")
    parser.add_argument("--borough", type=str, default=None,
                        help="行政区，如 MANHATTAN/BRONX/BROOKLYN/QUEENS/STATEN ISLAND")
    parser.add_argument("--limit", type=int, default=100000, help="最大抓取条数（自动分页）")
    parser.add_argument("--page-size", type=int, default=5000, help="分页大小")
    parser.add_argument("--out", type=str, default="pluto_residential.csv", help="输出 CSV 文件名")
    args = parser.parse_args()

    token = os.getenv("SOCRATA_APP_TOKEN")  # 可选
    df = fetch_pluto_residential(
        year_min=args.year_min,
        year_max=args.year_max,
        borough=args.borough,
        limit=args.limit,
        page_size=args.page_size,
        app_token=token
    )
    df.to_csv(args.out, index=False)
    print(f"✅ Saved {args.out} with {len(df):,} rows")
    print(f"Year range: {args.year_min or 'all'} - {args.year_max or 'all'}")


if __name__ == "__main__":
    main()
