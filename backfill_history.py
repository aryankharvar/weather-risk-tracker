"""
backfill_history.py

One-time script to populate weather_risk.db with historical daily
weather, so you don't have to wait weeks for fetch_weather.py to
accumulate rows. Uses Open-Meteo's free Historical Weather (Archive)
API — no key, no registration: https://open-meteo.com/en/docs/historical-weather-api

Run this ONCE, then let fetch_weather.py handle daily updates going forward.

Requires: requests, pandas
    pip install requests pandas

NOTE ON DATA CONSISTENCY: the live daily pipeline (fetch_weather.py)
records a single instantaneous "current weather" reading at whatever
time the job runs. This backfill instead uses each day's MAX temperature
and MAX wind speed from the historical archive (that's what the archive
API provides at daily resolution). The two aren't perfectly apples-to-
apples — backfilled days will tend to show slightly more extreme values
than a single daily snapshot would. Fine for trend/risk analysis, but
worth knowing if you ever compare a backfilled day directly against a
live-polled day.
"""

import sqlite3
from pathlib import Path

import requests

DB_PATH = Path(__file__).parent / "weather_risk.db"

LOCATIONS = {
    "Sudbury, ON":     (46.49, -80.99),
    "Thunder Bay, ON": (48.38, -89.25),
    "Vancouver, BC":   (49.28, -123.12),
    "Montreal, QC":    (45.50, -73.57),
    "Toronto, ON":     (43.65, -79.38),
}

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# How far back to backfill.
BACKFILL_DAYS = 90


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS weather_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT NOT NULL,
            observation_date DATE NOT NULL,
            temp_c REAL,
            wind_kmh REAL,
            precip_mm REAL,
            weathercode INTEGER,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(location_name, observation_date)
        )
        """
    )
    views_path = Path(__file__).parent / "views.sql"
    if views_path.exists():
        conn.executescript(views_path.read_text())
    conn.commit()


def fetch_history(name: str, lat: float, lon: float, days: int) -> list[dict]:
    import datetime

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode",
        "timezone": "auto",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if not dates:
        print(f"WARNING: no historical data returned for {name}")
        return []

    rows = []
    for i, date in enumerate(dates):
        tmax = daily["temperature_2m_max"][i]
        tmin = daily["temperature_2m_min"][i]
        if tmax is None or tmin is None:
            continue  # some recent days may not be finalized yet in the archive
        rows.append(
            {
                "location_name": name,
                "observation_date": date,
                "temp_c": round((tmax + tmin) / 2, 1),
                "wind_kmh": daily["windspeed_10m_max"][i],
                "precip_mm": daily["precipitation_sum"][i],
                "weathercode": daily["weathercode"][i],
            }
        )
    return rows


def save_rows(rows: list[dict], conn: sqlite3.Connection) -> int:
    inserted = 0
    for row in rows:
        try:
            conn.execute(
                """
                INSERT INTO weather_snapshots
                    (location_name, observation_date, temp_c, wind_kmh, precip_mm, weathercode)
                VALUES
                    (:location_name, :observation_date, :temp_c, :wind_kmh, :precip_mm, :weathercode)
                """,
                row,
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # already have this location/date
    conn.commit()
    return inserted


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_inserted = 0
    for name, (lat, lon) in LOCATIONS.items():
        rows = fetch_history(name, lat, lon, BACKFILL_DAYS)
        inserted = save_rows(rows, conn)
        total_inserted += inserted
        print(f"{name}: {len(rows)} days fetched, {inserted} new rows inserted")

    print(f"\nBackfill complete. Total new rows: {total_inserted}")

    import pandas as pd
    summary = pd.read_sql(
        "SELECT location_name, COUNT(*) AS rows, MIN(observation_date) AS earliest, MAX(observation_date) AS latest "
        "FROM weather_snapshots GROUP BY location_name",
        conn,
    )
    print("\nCurrent DB contents:")
    print(summary.to_string(index=False))

    conn.close()


if __name__ == "__main__":
    main()
