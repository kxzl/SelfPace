# SelfPace

A self-hosted running analytics platform. Ingests activity data from Strava, Garmin Connect, Intervals.icu, Runalyze, and manual FIT/GPX exports. Stores everything locally as Parquet files and delivers interactive analytics via Evidence.dev running DuckDB WASM entirely in the browser.

No cloud dependency. No database server. Everything runs in Docker.

---

## How it works

```
Data sources (Strava, Garmin, Intervals.icu, ...)
        ↓  OAuth / API key / file drop
  FastAPI backend
        ↓  writes Parquet files + triggers rebuild
  Evidence.dev (static site build)
        ↓  nginx serves HTML + Parquet files
  Browser
        ↓  DuckDB WASM queries Parquet files over HTTP
  Interactive dashboards + GPS route maps
```

---

## Stack

| Layer | Technology |
|---|---|
| Analytics UI | [Evidence.dev](https://evidence.dev) — SQL + Markdown → static site |
| Query engine | DuckDB WASM (built into Evidence, runs in browser) |
| GPS route maps | Leaflet.js — custom Svelte component in Evidence |
| Backend | FastAPI (Python 3.12) |
| Scheduler | APScheduler (runs inside FastAPI, no Redis/Celery) |
| FIT/GPX parsing | `fitparse`, `gpxpy` |
| Parquet writing | `pyarrow` |
| Storage | Named Docker volume at `/data` |
| Serving | nginx (multi-stage Docker build) |

---

## Services

```yaml
evidence:   # Evidence static site → nginx, port 3000
backend:    # FastAPI data ingestion + OAuth, port 8000
```

Both share a single Docker volume at `/data`.

---

## Data layout

```
/data/
  raw/        # Original FIT/GPX files — never modified
  parquet/    # One Parquet file per activity
  db/         # Optional DuckDB catalog
  imports/    # Drop zone for manual file uploads
```

---

## Integrations (build order)

| # | Source | Method |
|---|---|---|
| 1 | **Intervals.icu** | API key — no OAuth |
| 2 | **Strava** | OAuth 2.0 |
| 3 | **Runalyze** | Bulk ZIP export → `/data/imports/` |
| 4 | **Manual drop zone** | FIT / GPX / TCX / ZIP |
| 5 | **Garmin Connect** | `garth` library (unofficial SSO, best-effort) |
| 6 | **Runalyze** API | Incremental sync (after export path is stable) |
| 7 | **Polar Flow** | OAuth 2.0 via AccessLink v3 |
| 8 | **TrainingPeaks** | Deferred — export fallback sufficient |
| 9 | **Suunto** | Deferred — export fallback sufficient |
| 10 | **Coros** | Manual export only — no API exists |

---

## Getting started

```bash
cp .env.example .env
# Fill in API keys / OAuth credentials for the integrations you want

docker compose up --build
```

- Dashboard: http://localhost:3000
- Backend API: http://localhost:8000/docs

---

## Development

```bash
# Session context (run this first in any new Claude Code session)
/ctx

# Docker management
/dev up
/dev status
/dev logs

# Scaffold a new integration
/add-integration intervals

# Add a chart component
/new-chart WeeklyMileage

# Add a metric
/new-metric race-predictor

# Audit data quality
/inspect-data

# Log a decision
/log-decision
```

---

## Activity schema

All activities are normalized to this canonical Parquet schema:

| Field | Type | Notes |
|---|---|---|
| `activity_id` | string | `"{source}_{source_id}"` |
| `source` | string | e.g. `"intervals"`, `"strava"` |
| `source_id` | string | Provider's native ID |
| `started_at` | timestamp (UTC) | |
| `distance_m` | float | |
| `duration_s` | int | |
| `activity_type` | string | `"run"`, `"ride"`, `"swim"`, … |
| `avg_hr` | float | nullable |
| `avg_cadence` | float | nullable |
| `avg_pace_ms` | float | meters per second, nullable |
| `elevation_gain_m` | float | nullable |
| `polyline` | string | encoded polyline, nullable |

---

## Key decisions

See [`decisions.md`](decisions.md) for the full log. Short version:

- **Evidence.dev** replaces a hand-rolled Svelte SPA — DuckDB WASM, Parquet querying, and charting are all built in.
- **GPS maps** use a custom Leaflet component — Evidence's built-in map components don't support polylines.
- **No database server** — DuckDB WASM + Parquet makes one unnecessary.
- **No Celery/Redis** — APScheduler inside FastAPI is sufficient.
- **Garmin via `garth`** is best-effort; manual ZIP export is the documented fallback.
- **TrainingPeaks and Suunto** are deferred until there is demonstrated demand.
