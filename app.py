"""
app.py — Weather-Driven Supply Chain Risk Dashboard

Requires: streamlit, pandas, plotly
Run locally with: streamlit run app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = Path(__file__).parent / "weather_risk.db"

RISK_COLORS = {"Low Risk": "#2E8B57", "Moderate Risk": "#E3A857", "High Risk": "#C0392B"}

LOCATIONS = {
    "Sudbury, ON":     (46.49, -80.99),
    "Thunder Bay, ON": (48.38, -89.25),
    "Vancouver, BC":   (49.28, -123.12),
    "Montreal, QC":    (45.50, -73.57),
    "Toronto, ON":     (43.65, -79.38),
}

st.set_page_config(page_title="Supply Chain Weather Risk Tracker", layout="wide")

WEATHER_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️",
    56: "🌧️", 57: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    66: "🌧️", 67: "🌧️",
    71: "❄️", 73: "❄️", 75: "❄️", 77: "🌨️",
    80: "🌦️", 81: "🌦️", 82: "⛈️",
    85: "🌨️", 86: "🌨️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


def weather_icon(code) -> str:
    if pd.isna(code):
        return "🌡️"
    return WEATHER_ICONS.get(int(code), "🌡️")


RISK_SCORE_MAP = {"Low Risk": 0, "Moderate Risk": 50, "High Risk": 100}
RISK_BORDER = {"Low Risk": "#2E8B57", "Moderate Risk": "#E3A857", "High Risk": "#C0392B"}

st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(120deg, #0F2E2C 0%, #143935 45%, #1A4541 100%);
        border-radius: 16px;
        padding: 36px 40px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -60px; right: -60px;
        width: 260px; height: 260px;
        background: radial-gradient(circle, rgba(127,216,206,0.18), transparent 70%);
        border-radius: 50%;
    }
    .hero-eyebrow {
        color: #7FD8CE;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        display: flex; align-items: center; gap: 8px;
    }
    .hero-eyebrow .tick { width: 22px; height: 2px; background: #7FD8CE; display: inline-block; }
    .hero-title { color: #F4FBFA; font-size: 2.1rem; font-weight: 700; margin: 10px 0 4px 0; }
    .hero-subtitle { color: #A9C7C3; font-size: 1rem; }

    .risk-card {
        background: white;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        border-left: 6px solid #ccc;
        margin-bottom: 8px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .risk-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }
    .risk-card h4 { margin: 0 0 4px 0; font-size: 1.0rem; color: #1B2B34; }
    .risk-card .risk-label { font-weight: 700; font-size: 1.05rem; }
    .risk-card .risk-meta { color: #55686B; font-size: 0.85rem; margin-top: 6px; }

    .legend-dot {
        display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px;
    }
    </style>

    <div class="hero">
        <div class="hero-eyebrow"><span class="tick"></span>SUPPLY CHAIN RISK INTELLIGENCE</div>
        <div class="hero-title">🌨️ Weather Disruption Tracker</div>
        <div class="hero-subtitle">Live conditions across Canadian logistics hubs — updated daily, automatically</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 📍 Tracked Locations")
    for name in LOCATIONS:
        st.markdown(f"- {name}")

    st.markdown("---")
    st.markdown("### 🎨 Risk Legend")
    for label, color in RISK_COLORS.items():
        st.markdown(
            f'<span class="legend-dot" style="background:{color};"></span>{label}',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.caption(
        "Risk is classified from temperature, wind speed, and precipitation "
        "thresholds relevant to logistics disruption. Data refreshes daily "
        "via an automated GitHub Actions pipeline — no manual updates."
    )
    st.caption("Data source: [Open-Meteo](https://open-meteo.com) — free, no API key required.")


@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    views_path = Path(__file__).parent / "views.sql"
    if views_path.exists():
        conn.executescript(views_path.read_text())
        conn.commit()
    return conn


def load(query: str) -> pd.DataFrame:
    return pd.read_sql(query, get_connection())


latest = load("SELECT * FROM latest_risk_by_location ORDER BY location_name")

if not latest.empty:
    header_col, gauge_col = st.columns([3, 1])

    with header_col:
        st.markdown("### Current Conditions")
        card_cols = st.columns(len(latest))
        for col, (_, row) in zip(card_cols, latest.iterrows()):
            risk = row["disruption_risk"]
            icon = weather_icon(row.get("weathercode"))
            border = RISK_BORDER.get(risk, "#ccc")
            col.markdown(
                f"""
                <div class="risk-card" style="border-left-color:{border};">
                    <h4>{icon} {row['location_name']}</h4>
                    <div class="risk-label" style="color:{border};">{risk}</div>
                    <div class="risk-meta">{row['temp_c']}°C · {row['wind_kmh']} km/h wind · {row['precip_mm']}mm</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.caption(f"Last updated: {latest['observation_date'].max()}")

    with gauge_col:
        network_score = latest["disruption_risk"].map(RISK_SCORE_MAP).mean()
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=network_score,
            title={"text": "Network Risk", "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#2F7A78"},
                "steps": [
                    {"range": [0, 33], "color": "#DFF3EE"},
                    {"range": [33, 66], "color": "#FCEACB"},
                    {"range": [66, 100], "color": "#F6D5D0"},
                ],
            },
        ))
        gauge.update_layout(height=220, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(gauge, width='stretch')
else:
    st.info("No weather data yet — waiting on the first pipeline run.")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🌡️ Temperature & Wind Trend", "⚠️ 30-Day Risk Ranking", "🗺️ Risk Map", "🌧️ Precipitation"])

with tab1:
    st.subheader("Conditions Over Time")
    history = load("SELECT * FROM weather_snapshots ORDER BY observation_date")
    if not history.empty:
        location_choice = st.selectbox("Select location", history["location_name"].unique())
        subset = history[history["location_name"] == location_choice]

        fig = px.line(
            subset,
            x="observation_date",
            y=["temp_c", "wind_kmh"],
            labels={"value": "Value", "observation_date": "Date", "variable": "Metric"},
            title=f"{location_choice} — Temperature (°C) & Wind Speed (km/h)",
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Not enough history yet for a trend chart.")

with tab2:
    st.subheader("Which Locations Face the Most Disruption Risk?")
    st.caption("Ranked by number of High/Moderate risk days in the last 30 days.")
    ranking = load("SELECT * FROM risk_frequency_last_30_days")
    st.dataframe(ranking, width='stretch', hide_index=True)

with tab3:
    st.subheader("Current Risk by Location")
    st.caption("Geographic view of today's disruption risk across tracked logistics hubs.")

    if not latest.empty:
        map_df = latest.copy()
        map_df["lat"] = map_df["location_name"].map(lambda n: LOCATIONS.get(n, (None, None))[0])
        map_df["lon"] = map_df["location_name"].map(lambda n: LOCATIONS.get(n, (None, None))[1])
        map_df["risk_color"] = map_df["disruption_risk"].map(RISK_COLORS)

        fig_map = px.scatter_map(
            map_df,
            lat="lat",
            lon="lon",
            color="disruption_risk",
            color_discrete_map=RISK_COLORS,
            hover_name="location_name",
            hover_data={"temp_c": True, "wind_kmh": True, "precip_mm": True, "lat": False, "lon": False},
            zoom=2.5,
            size=[18] * len(map_df),
            map_style="open-street-map",  # no token required
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=450)
        st.plotly_chart(fig_map, width='stretch')
    else:
        st.info("No data yet for the risk map.")

with tab4:
    st.subheader("Today's Precipitation by Location")
    if not latest.empty:
        fig_precip = px.bar(
            latest.sort_values("precip_mm", ascending=False),
            x="location_name",
            y="precip_mm",
            color="disruption_risk",
            color_discrete_map=RISK_COLORS,
            labels={"precip_mm": "Precipitation (mm)", "location_name": "Location"},
        )
        st.plotly_chart(fig_precip, width='stretch')
    else:
        st.info("No data yet for precipitation comparison.")