# 🌨️ Weather-Driven Supply Chain Risk Tracker

An automated, self-updating pipeline tracking daily weather conditions across key Canadian logistics hubs, and translating them into a disruption risk score — built to connect real-time environmental data to a concrete supply chain/operations use case.

🔗 **Live Dashboard:** [weather-risk-tracker.streamlit.app](https://weather-risk-tracker.streamlit.app/)

![Daily Weather Risk Fetch](https://github.com/aryankharvar/weather-risk-tracker/actions/workflows/daily_fetch.yml/badge.svg)

---

## 📊 Overview

Weather is a real, everyday input to logistics and inventory planning — extreme cold, high wind, and heavy precipitation all affect transport reliability and replenishment timing. This project pulls daily conditions for five Canadian locations relevant to a mining/logistics supply chain, classifies each into a disruption risk tier, and serves a live dashboard that updates on its own.

```
GitHub Actions (daily cron)
        │  pulls current conditions via Open-Meteo (no API key required)
        ▼
   fetch_weather.py
        │  writes to SQLite, dedups on (location, date)
        ▼
   weather_risk.db  ──── committed back to the repo daily
        │
        ▼
   SQL views (CASE-based risk scoring, RANK() ranking)
        │
        ▼
   Streamlit dashboard  ──── auto-redeploys on every new commit
```

## 📍 Tracked Locations

Sudbury, ON · Thunder Bay, ON · Vancouver, BC · Montreal, QC · Toronto, ON

Chosen as a mix of a mining hub (Sudbury), major rail/shipping corridors (Thunder Bay, Vancouver, Montreal), and a general logistics reference point (Toronto).

## 🛠️ Tech Stack

- **Data source:** [Open-Meteo](https://open-meteo.com) — free weather API, no key or registration required
- **Language:** Python (Pandas, Requests)
- **Database:** SQLite, with `UNIQUE(location_name, observation_date)` constraint to make re-runs safe
- **SQL:** `CASE`-based risk classification, `RANK() OVER (...)` for risk-frequency ranking, views for reusable logic
- **Automation:** GitHub Actions (daily scheduled cron)
- **Dashboard:** Streamlit, Plotly (line charts, bar charts, gauge indicator, geographic scatter map)

## 📁 Repository Structure

```
weather-risk-tracker/
├── .github/workflows/
│   └── daily_fetch.yml         # scheduled daily automation
├── .streamlit/
│   └── config.toml             # custom theme
├── fetch_weather.py            # daily incremental pull + view creation
├── backfill_history.py         # one-time historical backfill
├── views.sql                   # reusable SQL views (CASE, RANK)
├── app.py                      # Streamlit dashboard
├── weather_risk.db             # SQLite DB, updated daily by the pipeline
├── requirements.txt
└── README.md
```

## 🧩 What the SQL Layer Does

| View | Technique | Purpose |
|---|---|---|
| `daily_risk_scores` | `CASE WHEN ... THEN ...` | Classifies each observation into Low / Moderate / High disruption risk based on temperature, wind, and precipitation thresholds |
| `latest_risk_by_location` | Correlated subquery | Most recent risk status per location |
| `risk_frequency_last_30_days` | CTE + `RANK() OVER (...)` | Ranks locations by how many High/Moderate risk days they've had in the last 30 days |

Risk thresholds (defined once, in `views.sql`):
```sql
CASE
    WHEN temp_c < -25 OR wind_kmh > 60 OR precip_mm > 20 THEN 'High Risk'
    WHEN temp_c < -15 OR wind_kmh > 40 OR precip_mm > 10 THEN 'Moderate Risk'
    ELSE 'Low Risk'
END AS disruption_risk
```

## 📈 Dashboard Features

- **Custom-built CSS hero header and styled risk cards** (with hover interaction) — hand-coded layout, not a static image
- **Sidebar** — tracked locations, a color-coded risk legend, and methodology notes
- **Network Risk Gauge** — aggregate 0-100 risk score across all tracked locations at a glance
- **Temperature & Wind Trend** — per-location historical line chart
- **30-Day Risk Ranking** — which locations have faced the most disruption risk recently
- **Risk Map** — geographic scatter map (no Mapbox token required) colored by current risk level
- **Precipitation Comparison** — bar chart of today's precipitation across all locations

## 🚀 How It Stays "Live"

1. A GitHub Actions workflow runs daily, executes `fetch_weather.py`, and commits the updated `weather_risk.db` back to this repo
2. Streamlit Community Cloud watches this repo and automatically redeploys the app on every new commit
3. All SQL views recompute directly against the latest data on every page load — no separate caching step between "new data lands" and "dashboard reflects it"

## 🔍 Sample Insight

Sudbury and Thunder Bay show meaningfully more High/Moderate risk days than Vancouver or Toronto over a 30-day window, driven primarily by temperature extremes and wind rather than precipitation — a pattern that would matter for scheduling inbound shipments or setting safety stock buffers ahead of forecasted cold snaps.

## 🏗️ How to Reproduce

```bash
git clone https://github.com/aryankharvar/weather-risk-tracker.git
cd weather-risk-tracker
pip install -r requirements.txt

# one-time historical backfill (last 90 days)
python backfill_history.py

# manual daily pull (GitHub Actions runs this automatically going forward)
python fetch_weather.py

# run the dashboard locally
streamlit run app.py
```

## 📌 Future Improvements

- Add more locations along key rail/shipping corridors as tracked data grows
- Layer in a simple cost-impact estimate per risk tier (e.g. estimated delay cost)
- Add historical risk-day counts by season to spot recurring patterns year over year

# 👨‍💻 Author

**Aryan Kharvar**

**M.Sc. Computational Sciences**

Data Analytics | Business Intelligence | Power BI | SQL | Python

💼 LinkedIn: [Aryan Kharvar](https://www.linkedin.com/in/aryankharvar)
