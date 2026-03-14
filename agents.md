# SelfPace — Project Blueprint

## Vision

A locally-hosted (optionally web-hosted) running analytics platform. It ingests activity data from first-party services (Strava, Garmin Connect, Coros) and aggregator platforms (Runalyze, Intervals.icu, TrainingPeaks), stores everything locally, and delivers deep metrics and visualizations via DuckDB WASM running entirely in the browser. Minimal setup friction for the user; minimal operational complexity overall.

---

## Core Principles

- **All services run in Docker containers** via Docker Compose. No host dependencies beyond Docker itself.
- **DuckDB WASM does the heavy lifting** — queries and aggregations run client-side in the browser against local Parquet files. No database server required.
- **Pragmatic integrations** — prefer official APIs with OAuth where feasible. Fall back to guided manual export when an API is too complex or requires paid access.
- **Data stays local** — all activity data is stored on-disk inside a mounted volume. Nothing is sent to external services beyond the initial sync.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose                      │
│                                                     │
│  ┌──────────────┐      ┌──────────────────────┐    │
│  │   frontend   │      │      backend         │    │
│  │  (nginx SPA) │      │  (FastAPI / Python)  │    │
│  │              │      │                      │    │
│  │ DuckDB WASM  │      │  OAuth flows         │    │
│  │ Charting lib │      │  Data sync jobs      │    │
│  │              │      │  File conversion     │    │
│  └──────┬───────┘      └──────────┬───────────┘    │
│         │                         │                 │
│         └─────────┬───────────────┘                 │
│                   │  shared volume                  │
│            ┌──────▼──────┐                          │
│            │  /data      │                          │
│            │  (Parquet)  │                          │
│            └─────────────┘                          │
└─────────────────────────────────────────────────────┘
```

### Services

| Service | Image | Role |
|---|---|---|
| `frontend` | nginx + built SPA | Serves the static app; also serves `/data` directory so DuckDB WASM can fetch Parquet files via HTTP |
| `backend` | Python (FastAPI) | Handles OAuth callbacks, API sync, file ingestion, FIT→Parquet conversion |

### Data Flow

1. User triggers a sync (or uploads a file) via the UI.
2. Backend fetches raw activity data from the provider API or reads from the upload drop zone.
3. Backend converts raw data (FIT, GPX, JSON) → Parquet and writes to `/data` volume.
4. Frontend uses DuckDB WASM to `SELECT` directly from those Parquet files served over HTTP.
5. Query results feed into the charting layer rendered in the browser.

---

## Data Sources

### Strava
- **Method**: OAuth 2.0 API (official, free tier).
- **Flow**: User clicks "Connect Strava" → backend redirects to Strava OAuth → callback stores `access_token` + `refresh_token` → background job pages through `/athlete/activities` and fetches streams (GPS, HR, cadence, pace) per activity.
- **Complexity**: Medium. Token refresh is straightforward. Rate limits (100 req/15 min, 1000/day) require simple throttling.
- **Data richness**: Good. Laps, HR, cadence, power, pace, elevation.

### Garmin Connect
- **Method**: Unofficial API via [`garth`](https://github.com/matin/garth) Python library (SSO login with username/password stored locally).
- **Fallback**: Guide user to export full data archive from Garmin Connect website → place ZIP in `/data/imports/` → backend auto-ingests on next startup.
- **Complexity**: Low-medium with `garth`. Avoid the official Garmin Health API (requires approval).
- **Data richness**: Excellent. Full FIT files, HRV, sleep, body battery.

### Coros
- **Method**: Manual export only. Coros has no public API.
- **Flow**: UI displays step-by-step instructions for exporting from Coros app or website → user drops FIT/GPX files into `/data/imports/` → backend auto-ingests.
- **Complexity**: Low (no integration code needed).

### Runalyze
- **Method**: Runalyze is itself an aggregator — users may already have years of data consolidated there from Garmin, Polar, Suunto, and others. Treat it as a high-value bulk export source.
- **Flow**: UI guides user to export their full Runalyze archive (Account → Export → "Export all activities as FIT/GPX") → drop ZIP into `/data/imports/` → backend auto-ingests.
- **API**: Runalyze has an unofficial REST API (`/api/v1/`) requiring a personal API key from account settings. Worth implementing for incremental sync if the user is an active Runalyze user; deduplication is by Runalyze activity ID.
- **Complexity**: Low (export) / Medium (API sync). API is undocumented but stable enough to use.
- **Why it matters**: A user connected to Runalyze may already have data flowing in from Garmin, Polar, and Strava — connecting here can replace all three individual integrations.

### Intervals.icu
- **Method**: Official API with API key authentication (no OAuth needed — key lives in user's account settings).
- **Flow**: User pastes their athlete ID and API key into settings → backend calls `GET /api/v1/athlete/{id}/activities` and fetches streams per activity.
- **Complexity**: Low. Well-documented, stable, free API. Rate limits are generous.
- **Data richness**: Excellent. Exposes all data Intervals.icu has received from connected sources (Garmin, Strava, Wahoo, etc.), plus its own fitness/fatigue model data.
- **Why it matters**: Many serious runners already use Intervals.icu as their analytics hub. Connecting here is often the single easiest way to pull in clean, normalized data.

### TrainingPeaks
- **Method**: OAuth 2.0 API (official). Requires registering an app on their developer portal; approval is manual but generally granted.
- **Flow**: Standard OAuth callback → sync workouts via `/v1/athlete/workouts`.
- **Complexity**: Medium-high. OAuth approval gate and rate limits make this lower priority.
- **Fallback**: Guide user to export `.fit` or `.pwx` files and drop into `/data/imports/`.
- **Decision deferred**: Implement only if there is demand; manual export fallback covers most cases.

### Polar Flow
- **Method**: Official Polar AccessLink API v3, OAuth 2.0.
- **Flow**: OAuth → pull exercises and physical information. Polar provides full FIT-equivalent data via the API.
- **Complexity**: Medium. API is well-documented but requires registering a client.
- **Fallback**: Export from Polar Flow website as FIT/GPX files.

### Suunto
- **Method**: Official Suunto API with OAuth 2.0 (Suunto Developer Program).
- **Fallback**: Export from Suunto app as FIT/GPX files → `/data/imports/`.
- **Complexity**: Medium. API approval required; fallback is sufficient for most users.
- **Decision deferred**: Low priority given manual export fallback works well.

### Manual / Generic
- Drop zone in the UI accepting `.fit`, `.gpx`, `.tcx`, `.pwx` files and ZIP archives of any of the above.
- Backend unpacks ZIPs, converts all supported formats, and ingests immediately.
- This is the universal fallback for any source not directly integrated.

---

## Technology Choices

### Frontend
- **Framework**: [Evidence.dev](https://evidence.dev) — open-source BI-as-code framework built on SvelteKit. Write SQL + Markdown; Evidence generates a static site with interactive charts.
- **DuckDB WASM**: Built into Evidence — queries run client-side against Parquet files served as static files. No separate setup needed.
- **Charting**: Evidence's built-in component library (backed by ECharts) covers standard analytics charts. Custom Svelte components handle anything outside Evidence's built-in set.
- **Maps**: Custom Svelte component wrapping Leaflet.js for GPS route/polyline rendering. Evidence's built-in map components (point, bubble, area) handle aggregate geo views.
- **Build**: Evidence build (`npm run build`) produces a static site. Multi-stage Docker: Node builder → nginx image. Evidence build is triggered by FastAPI after each sync completes.

### Backend
- **Framework**: FastAPI (Python 3.12).
- **FIT parsing**: [`fitparse`](https://github.com/dtcooper/python-fitparse) or [`garmin-fit-sdk`](https://developer.garmin.com/fit/overview/).
- **GPX/TCX parsing**: `gpxpy`.
- **Parquet writing**: `pyarrow` or `duckdb` Python library.
- **Scheduler**: APScheduler (lightweight, no Celery/Redis needed) for periodic syncs.
- **Config/secrets**: `.env` file mounted into the container; never committed.

### Storage
- All data in a single named Docker volume mounted at `/data`.
- Directory layout:
  ```
  /data/
    raw/          # Original FIT/GPX files, never modified
    parquet/      # Converted activity files, one per activity
    db/           # Optional: persistent DuckDB catalog file
    imports/      # Drop zone for manual uploads
  ```

---

## Docker Compose Layout

```yaml
services:
  evidence:
    build: ./evidence      # Node builder → nginx; runs `npm run build`
    ports:
      - "3000:80"
    volumes:
      - data:/usr/share/nginx/html/data:ro   # Parquet files served as static files
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - data:/data
    env_file:
      - .env

volumes:
  data:
```

**Data refresh flow**: FastAPI writes Parquet files to `/data/parquet/` → calls `POST /internal/build` (or a file watcher) → triggers `npm run build` inside the Evidence container → nginx serves the updated static site.

The Evidence nginx config exposes `/data` as a static path so DuckDB WASM can `fetch()` Parquet files directly from the browser.

---

## Key Metrics & Analyses to Build

- Weekly / monthly mileage trends
- Pace zones and time-in-zone
- HR zones and aerobic vs. anaerobic distribution
- TSS / CTL / ATL training load (Banister model)
- Long run progression
- Cadence, stride length trends
- Elevation gain over time
- Race predictor (Riegel formula)
- Activity map (Leaflet.js, GPS polyline overlay — custom Svelte component in Evidence)

---

## Integration Priority

Build integrations in this order to maximize coverage with minimum effort:

| Priority | Source | Why |
|---|---|---|
| 1 | **Intervals.icu** | Simple API key auth, no OAuth dance, normalizes data from many upstream devices |
| 2 | **Strava** | Largest user base; OAuth is well-documented |
| 3 | **Runalyze** (export) | Bulk historical import, covers Garmin/Polar/Suunto users at once |
| 4 | **Manual drop zone** | Universal fallback, always needed |
| 5 | **Garmin Connect** (`garth`) | Highest data richness but unofficial API risk |
| 6 | **Runalyze** (API sync) | Incremental sync on top of bulk export |
| 7 | **Polar Flow** | OAuth-gated, lower user base |
| 8 | **TrainingPeaks** | Manual approval gate; fallback export is adequate |
| 9 | **Suunto** | Low priority; manual export covers most users |
| 10 | **Coros** | Manual export only, no API exists |

---

## Open Questions / Decisions Deferred

- **Auth for hosted mode**: If deployed beyond localhost, add a simple single-user password (HTTP basic auth via nginx) rather than building a full auth system.
- **Garmin sync strategy**: `garth` SSO is unofficial and can break. Decide at integration time whether to implement it or lean on manual export.
- **Data deduplication**: Need a stable activity ID per source to avoid re-importing on repeated syncs. Each source must map to a canonical `(source, source_id)` pair stored in a manifest file.
- **Runalyze API stability**: The `/api/v1/` endpoint is undocumented — evaluate at implementation time whether it is reliable enough for incremental sync or if export-only is the safer path.
- **TrainingPeaks and Suunto**: Defer entirely until there is demonstrated user demand.
- **Mobile support**: DuckDB WASM works on mobile browsers but performance on large datasets is unknown — test before optimizing.
