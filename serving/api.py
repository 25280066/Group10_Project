from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from typing import Optional
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("weather-api")

app = FastAPI(
    title="Weather Analytics API",
    description="REST API for weather data pipeline analytics",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# DB HELPERS
# ------------------------------------------------------------------

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
        sslmode="require",
    )


def fetchall(query: str, params=None) -> list[dict]:
    """Run a SELECT and return rows as dicts."""
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"DB error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


def fetchone(query: str, params=None) -> dict | None:
    rows = fetchall(query, params)
    return rows[0] if rows else None



# HEALTH
# ------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():
    """Ping the DB and confirm the API is alive."""
    try:
        conn = get_conn()
        conn.close()
        logger.info("Health check passed")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="DB unreachable")



# CITIES
# ------------------------------------------------------------------

@app.get("/cities", tags=["Reference"])
def list_cities():
    """Return all distinct city names available in the pipeline."""
    rows = fetchall("SELECT DISTINCT city_name FROM weather_features ORDER BY city_name")
    logger.info("Listed cities")
    return [r["city_name"] for r in rows]


@app.get("/locations", tags=["Reference"])
def list_locations():
    """Return all location metadata."""
    rows = fetchall(
        "SELECT location_id, city_name, latitude, longitude, timezone FROM locations ORDER BY city_name"
    )
    logger.info("Listed locations")
    return rows



# KPI
# ------------------------------------------------------------------

@app.get("/kpi/{city}", tags=["Analytics"])
def get_kpi(city: str):
    """
    Aggregate KPIs for a city:
    avg temperature, humidity, wind speed, total precipitation.
    """
    row = fetchone(
        """
        SELECT
            ROUND(AVG(temperature)::numeric, 2)         AS avg_temp,
            ROUND(AVG(humidity)::numeric, 2)            AS avg_humidity,
            ROUND(AVG(wind_speed)::numeric, 2)          AS avg_wind,
            ROUND(SUM(precipitation)::numeric, 2)       AS total_precipitation,
            COUNT(*)                                     AS record_count
        FROM weather_features
        WHERE city_name = %s
        """,
        (city,),
    )
    if row is None or row["record_count"] == 0:
        raise HTTPException(status_code=404, detail=f"No data for city: {city}")
    logger.info(f"KPI fetched for {city}")
    return row



# DAILY SUMMARY
# ------------------------------------------------------------------

@app.get("/daily-summary/{city}", tags=["Analytics"])
def get_daily_summary(
    city: str,
    days: int = Query(30, ge=1, le=365, description="Number of recent days to return"),
):
    """Daily aggregated weather summary for a city."""
    rows = fetchall(
        """
        SELECT
            date,
            ROUND(avg_temperature::numeric, 2)     AS avg_temperature,
            ROUND(avg_humidity::numeric, 2)         AS avg_humidity,
            ROUND(total_precipitation::numeric, 2)  AS total_precipitation,
            ROUND(avg_wind_speed::numeric, 2)       AS avg_wind_speed
        FROM weather_daily_summary
        WHERE city_name = %s
        ORDER BY date DESC
        LIMIT %s
        """,
        (city, days),
    )
    logger.info(f"Daily summary fetched for {city} ({days} days)")
    return rows



# TEMPERATURE TREND
# ------------------------------------------------------------------

@app.get("/temperature-trend/{city}", tags=["Analytics"])
def get_temperature_trend(
    city: str,
    days: int = Query(7, ge=1, le=90),
):
    """Hourly temperature readings for the last N days — useful for trend charts."""
    rows = fetchall(
        """
        SELECT
            timestamp,
            ROUND(temperature::numeric, 2) AS temperature,
            ROUND(apparent_temperature::numeric, 2) AS feels_like,
            season
        FROM weather_features wf
        JOIN weather_clean wc
          ON wf.location_id = wc.location_id AND wf.timestamp = wc.timestamp
        WHERE wf.city_name = %s
          AND wf.timestamp >= NOW() - INTERVAL '%s days'
        ORDER BY wf.timestamp ASC
        """,
        (city, days),
    )
    logger.info(f"Temperature trend fetched for {city}")
    return rows



# ANOMALIES
# ------------------------------------------------------------------

@app.get("/anomalies/{city}", tags=["Analytics"])
def get_anomalies(
    city: str,
    limit: int = Query(50, ge=1, le=500),
):
    """Temperature anomalies (deviation > 5 °C from location average)."""
    rows = fetchall(
        """
        SELECT
            timestamp,
            ROUND(temperature::numeric, 2)  AS temperature,
            ROUND(avg_temp::numeric, 2)     AS avg_temp,
            ROUND(deviation::numeric, 2)    AS deviation
        FROM weather_anomalies
        WHERE city_name = %s
        ORDER BY ABS(deviation) DESC
        LIMIT %s
        """,
        (city, limit),
    )
    logger.info(f"Anomalies fetched for {city}")
    return rows



# CITY RANKINGS
# ------------------------------------------------------------------

@app.get("/city-rankings", tags=["Analytics"])
def get_city_rankings():
    """All cities ranked by average temperature (hottest first)."""
    rows = fetchall(
        """
        SELECT
            city_name,
            ROUND(avg_temp::numeric, 2) AS avg_temp,
            temp_rank
        FROM city_rankings
        ORDER BY temp_rank
        """
    )
    logger.info("City rankings fetched")
    return rows



# SEASONAL ANALYSIS
# ------------------------------------------------------------------

@app.get("/seasonal/{city}", tags=["Analytics"])
def get_seasonal_stats(city: str):
    """Average temperature and humidity broken down by season."""
    rows = fetchall(
        """
        SELECT
            season,
            ROUND(AVG(temperature)::numeric, 2)  AS avg_temp,
            ROUND(AVG(humidity)::numeric, 2)      AS avg_humidity,
            ROUND(AVG(wind_speed)::numeric, 2)    AS avg_wind,
            COUNT(*)                               AS data_points
        FROM weather_features
        WHERE city_name = %s
        GROUP BY season
        ORDER BY season
        """,
        (city,),
    )
    logger.info(f"Seasonal stats fetched for {city}")
    return rows



# HOURLY PATTERN
# ------------------------------------------------------------------

@app.get("/hourly-pattern/{city}", tags=["Analytics"])
def get_hourly_pattern(city: str):
    """Average temperature by hour of day — reveals diurnal patterns."""
    rows = fetchall(
        """
        SELECT
            hour,
            ROUND(AVG(temperature)::numeric, 2) AS avg_temp,
            ROUND(AVG(humidity)::numeric, 2)     AS avg_humidity
        FROM weather_features
        WHERE city_name = %s
        GROUP BY hour
        ORDER BY hour
        """,
        (city,),
    )
    logger.info(f"Hourly pattern fetched for {city}")
    return rows