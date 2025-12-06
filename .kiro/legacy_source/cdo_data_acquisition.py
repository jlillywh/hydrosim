"""
NOAA CDO API Data Acquisition for Pacific Northwest Precipitation

- Authenticates using .env API key
- Discovers stations with daily PRCP data for 2000–2025 in the PNW west of Cascades
- Downloads, checks completeness, and saves tidy CSVs
"""
import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import time
MAX_RETRIES = 5
INITIAL_DELAY_SECONDS = 2

# Load API key from .env
load_dotenv()
CDO_TOKEN = os.getenv("NOAA_CDO_API_TOKEN")

CDO_BASE = "https://www.ncdc.noaa.gov/cdo-web/api/v2/"
HEADERS = {"token": CDO_TOKEN}

REGION_EXTENT = f"-125.0,42.0,-121.0,49.0"  # minLon,minLat,maxLon,maxLat (west of Cascades)
START_DATE = "2000-01-01"
END_DATE = "2025-12-31"
MIN_YEARS = 20
MIN_COMPLETENESS = 0.9  # 90%

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def get_stations():
    print("🔍 Querying CDO API for candidate stations...")
    stations = []
    offset = 1
    limit = 1000
    while True:
        params = {
            "datasetid": "GHCND",
            "datatypeid": "PRCP",
            "startdate": START_DATE,
            "enddate": END_DATE,
            "limit": limit,
            "offset": offset,
            "extent": REGION_EXTENT
        }
        retries = 0
        delay = INITIAL_DELAY_SECONDS
        while True:
            try:
                resp = requests.get(CDO_BASE + "stations", headers=HEADERS, params=params)
                if resp.status_code == 200:
                    break
                elif resp.status_code in (429, 503):
                    print(f"API Error {resp.status_code}, retrying in {delay} seconds...")
                    time.sleep(delay)
                    retries += 1
                    delay *= 2
                    if retries > MAX_RETRIES:
                        print(f"❌ Max retries exceeded for stations query. Aborting.")
                        return stations
                else:
                    print(f"❌ Error: {resp.status_code} {resp.text}")
                    return stations
            except Exception as e:
                print(f"❌ Exception during stations query: {e}")
                return stations
        data = resp.json()
        stations.extend(data.get("results", []))
        if len(data.get("results", [])) < limit:
            break
        offset += limit
    print(f"✅ Found {len(stations)} candidate stations.")
    return stations

def get_station_data(station_id):
    print(f"📥 Downloading data for {station_id}...")
    records = []
    year = 2000
    while year <= 2025:
        params = {
            "datasetid": "GHCND",
            "datatypeid": "PRCP",
            "stationid": station_id,
            "startdate": f"{year}-01-01",
            "enddate": f"{year}-12-31",
            "limit": 1000
        }
        retries = 0
        delay = INITIAL_DELAY_SECONDS
        while True:
            try:
                resp = requests.get(CDO_BASE + "data", headers=HEADERS, params=params)
                if resp.status_code == 200:
                    break
                elif resp.status_code in (429, 503):
                    print(f"  API Error {resp.status_code} for {station_id} {year}, retrying in {delay} seconds...")
                    time.sleep(delay)
                    retries += 1
                    delay *= 2
                    if retries > MAX_RETRIES:
                        print(f"  ❌ Max retries exceeded for {station_id} {year}. Skipping year.")
                        break
                else:
                    print(f"  ❌ Error for {station_id} {year}: {resp.status_code} {resp.text}")
                    break
            except Exception as e:
                print(f"  ❌ Exception for {station_id} {year}: {e}")
                break
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("results", []):
                records.append({
                    "date": item["date"][:10],
                    "prcp": item["value"] / 10.0  # tenths of mm to mm
                })
        year += 1
    if not records:
        print(f"  ❌ No data for {station_id}")
        return None
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df

def main():
    stations = get_stations()
    results = []
    for i, st in enumerate(stations, 1):
        sid = st["id"]
        name = st.get("name", sid)
        print(f"\n[{i}/{len(stations)}] {name} ({sid})")
        df = get_station_data(sid)
        if df is None or len(df) < MIN_YEARS * 365:
            print(f"  ❌ Skipping {name}: insufficient data.")
            continue
        # Completeness check
        years = df.index.year.unique()
        if len(years) < MIN_YEARS:
            print(f"  ❌ Skipping {name}: only {len(years)} years of data.")
            continue
        completeness = df["prcp"].notna().sum() / ((END_DATE[:4] - START_DATE[:4] + 1) * 365)
        if completeness < MIN_COMPLETENESS:
            print(f"  ❌ Skipping {name}: completeness {completeness:.2%} < {MIN_COMPLETENESS:.0%}")
            continue
        # Save
        raw_path = os.path.join(RAW_DIR, f"{sid.replace(':','_')}_cdo_raw.csv")
        df.to_csv(raw_path)
        print(f"  ✅ Saved raw data: {raw_path}")
        results.append({"id": sid, "name": name, "years": len(years), "completeness": completeness})
        if len(results) >= 100:
            break
    print(f"\n🎉 Done. {len(results)} stations saved.")

if __name__ == "__main__":
    main()
