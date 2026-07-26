"""
fetch_weather.py

Pulls current weather + today's precipitation for a set of Canadian
locations relevant to mining/logistics supply chains, and stores it for
daily risk analysis. Uses Open-Meteo, which needs no API key and no
registration — https://open-meteo.com

Requires: requests, pandas
    pip install requests pandas
"""

import sqlite3
from pathlib import Path

import requests

DB_PATH = Path(__file__).parent / "weather_risk.db"

# Locations relevant to a mining/logistics supply chain: Sudbury (Vale HQ),
# major Canadian rail/shipping hubs, and Toronto as a logistics reference point.
LOCATIONS = {
    "Sudbury, ON":     (46.49, -80.99),
    "Thunder Bay, ON": (48.38, -89.25),
    "Vancouver, BC":   (49.28, -123.12),
    "Montreal, QC":    (45.50, -73.57),
    "Toronto, ON":     (43.65, -79.38),
}

BASE_URL = "https://api.open-meteo.com/v1/forecast"


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


def fetch_location(name: str, lat: float, lon: float) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "daily": "precipitation_sum",
        "timezone": "auto",
        "forecast_days": 1,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    current = data.get("current_weather")
    daily = data.get("daily", {})

    if not current:
        print(f"WARNING: no current_weather data for {name}")
        return None

    observation_date = current["time"][:10]  # "2026-07-20T14:00" -> "2026-07-20"
    precip_list = daily.get("precipitation_sum", [])
    precip_mm = precip_list[0] if precip_list else None

    return {
        "location_name": name,
        "observation_date": observation_date,
        "temp_c": current.get("temperature"),
        "wind_kmh": current.get("windspeed"),
        "precip_mm": precip_mm,
        "weathercode": current.get("weathercode"),
    }


def save_snapshot(row: dict, conn: sqlite3.Connection) -> bool:
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
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # already have this location/date, expected on re-runs


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    inserted = 0
    for name, (lat, lon) in LOCATIONS.items():
        row = fetch_location(name, lat, lon)
        if row is None:
            continue
        if save_snapshot(row, conn):
            inserted += 1
        print(f"{name}: temp={row['temp_c']}C wind={row['wind_kmh']}km/h precip={row['precip_mm']}mm")

    print(f"\nInserted {inserted} new rows.")
    conn.close()


if __name__ == "__main__":
    main()
