# 🌤️ Global Weather Analytics Pipeline

> AI620 — Data Engineering · Group 10 · SBASSE, LUMS

A fully automated, end-to-end weather data pipeline: ingestion from the Open-Meteo API → PostgreSQL storage → Prefect-orchestrated ETL → FastAPI backend → Streamlit dashboard, containerised with Docker Compose.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Option A — Docker (Recommended)](#option-a--docker-recommended)
- [Option B — Local (Manual)](#option-b--local-manual)
- [Running the Ingestion Pipeline](#running-the-ingestion-pipeline)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Project Structure

```
project/
├── ingestion/
│   └── ingestion.ipynb       # Prefect ETL pipeline (ingest → clean → features → analytics)
├── serving/
│   └── api.py                # FastAPI backend (9 endpoints)
├── dashboard/
│   └── app.py                # Streamlit frontend
├── schemas.sql               # Raw PostgreSQL schema definitions
├── Dockerfile.api            # Container spec for FastAPI
├── Dockerfile.dashboard      # Container spec for Streamlit
├── docker-compose.yml        # Orchestrates both services
├── requirements.txt          # Python dependencies
└── .env                      # Environment variables (never commit this)
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | 24+ | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (bundled) | included with Docker Desktop |
| Python | 3.12+ | https://www.python.org/downloads/ (local only) |
| PostgreSQL | any | Supabase cloud or local instance |

---

## Environment Setup

Create a `.env` file in the project root (same level as `docker-compose.yml`):

```env
DB_HOST=your-supabase-host.supabase.co
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-database-password
DB_PORT=5432
```

> **Never commit `.env` to version control.** It is already listed in `.gitignore`.

### Initialize the Database Schema

Run the schema once against your PostgreSQL instance before any pipeline runs:

```bash
psql "postgresql://<DB_USER>:<DB_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>?sslmode=require" \
  -f schemas.sql
```

Or paste the contents of `schemas.sql` directly into the Supabase SQL editor.

---

## Option A — Docker (Recommended)

### 1. Build and start all services

```bash
docker compose up --build
```

This starts:
- `weather-api` on **http://localhost:8000**
- `weather-dashboard` on **http://localhost:8501**

The dashboard container waits for the API health check to pass before starting.

### 2. Open the dashboard

```
http://localhost:8501
```

### 3. Explore the API docs

```
http://localhost:8000/docs
```

### 4. Stop everything

```bash
docker compose down
```

---

## Option B — Local (Manual)

### 1. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the FastAPI backend

```bash
uvicorn serving.api:app --reload --port 8000
```

### 4. Start the Streamlit dashboard

Open a second terminal (with the venv activated):

```bash
streamlit run dashboard/app.py
```

---

## Running the Ingestion Pipeline

The Prefect pipeline handles ingestion → cleaning → feature engineering → analytics tables. It must be run **after** the schema is initialized and **before** the dashboard is opened.

### Via Jupyter (development)

```bash
jupyter notebook ingestion/ingestion.ipynb
```

Run all cells top to bottom. The final cell triggers `weather_pipeline()` which executes these Prefect tasks in order:

```
create_weather_clean
       ↓
create_weather_features
       ↓            ↓             ↓
create_daily_summary  create_city_rankings  create_anomalies
```

Expected output (all tasks should show `Completed`):

```
weather_clean created
weather_features created
weather_daily_summary created
city_rankings view created
weather_anomalies created
```

### Via Python script (production)

Convert the notebook and run directly:

```bash
jupyter nbconvert --to script ingestion/ingestion.ipynb --output ingestion/pipeline
python ingestion/pipeline.py
```

### Scheduling recurring runs with Prefect

To schedule the pipeline to run automatically (e.g. every day at midnight):

```python
from prefect.schedules import CronSchedule

@flow(name="weather-etl-pipeline", schedule=CronSchedule(cron="0 0 * * *"))
def weather_pipeline():
    ...
```

Then deploy via the Prefect CLI:

```bash
prefect deploy ingestion/pipeline.py:weather_pipeline \
  --name "daily-weather-run" \
  --cron "0 0 * * *"

prefect worker start --pool default-agent-pool
```

---

## API Reference

All endpoints are documented interactively at **http://localhost:8000/docs**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | DB connectivity check |
| `GET` | `/cities` | List all available cities |
| `GET` | `/locations` | Full location metadata |
| `GET` | `/kpi/{city}` | Avg temp, humidity, wind, precipitation |
| `GET` | `/daily-summary/{city}?days=30` | Daily aggregates (up to 365 days) |
| `GET` | `/temperature-trend/{city}?days=7` | Hourly readings for trend charts |
| `GET` | `/anomalies/{city}?limit=50` | Readings deviating >5 °C from mean |
| `GET` | `/city-rankings` | All cities ranked by avg temperature |
| `GET` | `/seasonal/{city}` | Per-season breakdown (Winter/Spring/Summer/Autumn) |
| `GET` | `/hourly-pattern/{city}` | Avg temperature by hour of day |

**Example:**

```bash
curl http://localhost:8000/kpi/Lahore
```

```json
{
  "avg_temp": 28.4,
  "avg_humidity": 61.2,
  "avg_wind": 9.3,
  "total_precipitation": 142.5,
  "record_count": 8760
}
```

---

## Troubleshooting

**Dashboard shows "Cannot reach API"**
- Ensure the API container is running: `docker compose ps`
- Check API logs: `docker compose logs api`
- Confirm `API_BASE_URL` is set correctly (Docker sets this automatically; for local runs add `API_BASE_URL=http://localhost:8000` to `.env`)

**`psycopg2.OperationalError` / DB connection refused**
- Verify all five `DB_*` variables are present and correct in `.env`
- Confirm your IP is allowlisted in Supabase under **Project Settings → Database → Connection Pooling**

**Prefect task fails mid-pipeline**
- Each task is idempotent (`DROP TABLE IF EXISTS` before every `CREATE`), so simply re-run the pipeline from the top
- Check Prefect logs in the notebook output or the Prefect UI at `http://localhost:4200` if a server is running

**Port already in use**
```bash
# Change ports in docker-compose.yml, e.g.:
ports:
  - "8001:8000"   # API on 8001
  - "8502:8501"   # Dashboard on 8502
```