-- views.sql
-- Risk classification and analysis views for weather_snapshots.

CREATE VIEW IF NOT EXISTS daily_risk_scores AS
SELECT
    location_name,
    observation_date,
    temp_c,
    wind_kmh,
    precip_mm,
    weathercode,
    CASE
        WHEN temp_c < -25 OR wind_kmh > 60 OR precip_mm > 20 THEN 'High Risk'
        WHEN temp_c < -15 OR wind_kmh > 40 OR precip_mm > 10 THEN 'Moderate Risk'
        ELSE 'Low Risk'
    END AS disruption_risk
FROM weather_snapshots;

CREATE VIEW IF NOT EXISTS latest_risk_by_location AS
SELECT drs.*
FROM daily_risk_scores drs
WHERE observation_date = (
    SELECT MAX(observation_date) FROM weather_snapshots
    WHERE location_name = drs.location_name
);

-- Ranks locations by how many High/Moderate risk days they've had
-- in the last 30 days — mirrors the RANK()-based volatility/worst-route
-- queries from the other two tracker projects.
CREATE VIEW IF NOT EXISTS risk_frequency_last_30_days AS
WITH risk_counts AS (
    SELECT
        location_name,
        SUM(CASE WHEN disruption_risk = 'High Risk' THEN 1 ELSE 0 END) AS high_risk_days,
        SUM(CASE WHEN disruption_risk = 'Moderate Risk' THEN 1 ELSE 0 END) AS moderate_risk_days,
        COUNT(*) AS days_tracked
    FROM daily_risk_scores
    WHERE observation_date >= DATE('now', '-30 days')
    GROUP BY location_name
)
SELECT
    location_name,
    high_risk_days,
    moderate_risk_days,
    days_tracked,
    RANK() OVER (ORDER BY high_risk_days DESC, moderate_risk_days DESC) AS risk_rank
FROM risk_counts
ORDER BY risk_rank;