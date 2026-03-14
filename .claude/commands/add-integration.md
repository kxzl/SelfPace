---
allowed-tools: Bash, Read, Write, Edit
argument-hint: [intervals|strava|garmin|runalyze|polar|coros]
---

Scaffold a new data source integration. The source is: **$ARGUMENTS**

Work through each step in order.

---

## Step 1 — Discover existing pattern

```bash
ls backend/integrations/ 2>/dev/null || echo "[no integrations yet]"
```

If an existing integration directory is found, read its `connector.py` as the reference pattern:

```bash
ls backend/integrations/*/connector.py 2>/dev/null | head -1
```

Read that file if it exists.

---

## Step 2 — Determine source-specific details

Use the details below for the requested source. Do not read agents.md.

### intervals
- **Auth**: API key — Base64 Basic auth (`Basic base64(athlete_id:api_key)`)
- **Env vars**: `INTERVALS_ATHLETE_ID`, `INTERVALS_API_KEY`
- **Base URL**: `https://intervals.icu/api/v1/athlete/{athlete_id}/`
- **Key endpoints**: `activities`, `activities/{id}/streams`
- **Rate limits**: generous, no strict throttling needed
- **Files to create**: `__init__.py`, `connector.py`, `converter.py`, `scheduler.py`
- **OAuth routes**: none

### strava
- **Auth**: OAuth 2.0, token refresh via `https://www.strava.com/oauth/token`
- **Env vars**: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REDIRECT_URI`
- **Rate limits**: 100 req/15 min, 1000 req/day — implement token bucket
- **Files to create**: `__init__.py`, `connector.py`, `converter.py`, `scheduler.py`
- **OAuth routes**: `/connect`, `/callback`

### garmin
- **Auth**: `garth` library — SSO email/password (unofficial, best-effort)
- **Env vars**: `GARMIN_EMAIL`, `GARMIN_PASSWORD`
- **Note**: Mark as best-effort; if `garth` raises, log and skip without retrying
- **Files to create**: `__init__.py`, `connector.py`, `converter.py`, `scheduler.py`
- **OAuth routes**: none

### runalyze
- **Auth**: export-only — watch `/data/imports/` for ZIP drops; no connector/scheduler
- **Env vars**: none required (optional: `RUNALYZE_API_KEY` for future incremental sync)
- **Files to create**: `__init__.py`, `converter.py` only
- **OAuth routes**: none

### polar
- **Auth**: OAuth 2.0 via Polar AccessLink v3
- **Env vars**: `POLAR_CLIENT_ID`, `POLAR_CLIENT_SECRET`, `POLAR_REDIRECT_URI`
- **Base URL**: `https://www.polaraccesslink.com/v3/`
- **Files to create**: `__init__.py`, `connector.py`, `converter.py`, `scheduler.py`
- **OAuth routes**: `/connect`, `/callback`

### coros
- **Auth**: none — manual export only, no connector
- **Files to create**: `__init__.py`, `converter.py` only
- **Note**: UI should show step-by-step export instructions; backend only needs the converter

---

## Step 3 — Create integration files

Create the directory `backend/integrations/$ARGUMENTS/` and the required files.

### `__init__.py`
Empty or exports the connector class.

### `connector.py` (if applicable)
- Class: `<Name>Connector`
- Methods: `authenticate()`, `fetch_activities(since: datetime) -> list[dict]`, `fetch_streams(activity_id: str) -> dict`
- For OAuth sources: `get_auth_url() -> str`, `handle_callback(code: str) -> None`
- For garmin: wrap all calls in try/except, log failures, return empty list on error

### `converter.py`
- Function: `convert(raw: dict) -> dict`
- Must output the canonical schema:
  ```
  activity_id: str        # "{source}_{source_id}"
  source: str             # e.g. "intervals", "strava"
  source_id: str          # provider's native ID
  started_at: datetime    # UTC
  distance_m: float
  duration_s: int
  activity_type: str      # "run", "ride", "swim", etc.
  avg_hr: float | None
  avg_cadence: float | None
  avg_pace_ms: float | None   # meters per second
  elevation_gain_m: float | None
  polyline: str | None    # encoded polyline or None
  ```

### `scheduler.py` (if applicable)
- Function: `schedule_sync(scheduler: APScheduler, connector: <Name>Connector)`
- Default interval: every 6 hours
- Calls `connector.fetch_activities(since=last_sync_time)`, runs through `converter.convert()`, writes Parquet to `/data/parquet/`

---

## Step 4 — Wire FastAPI routes

In `backend/main.py` (or `backend/routers/<source>.py`), add:

- `GET /integrations/<source>/status` — returns connection status and last sync time
- `POST /integrations/<source>/sync` — triggers an immediate sync
- `GET /integrations/<source>/connect` — OAuth only: redirects to provider auth URL
- `GET /integrations/<source>/callback` — OAuth only: handles the OAuth callback

---

## Step 5 — Create frontend integration card

Create `frontend/src/components/integrations/<Name>Card.svelte`:

```svelte
<script>
  let status = null;
  async function loadStatus() {
    const r = await fetch('/api/integrations/<source>/status');
    status = await r.json();
  }
  async function sync() {
    await fetch('/api/integrations/<source>/sync', { method: 'POST' });
    await loadStatus();
  }
  loadStatus();
</script>

<div class="integration-card">
  <h3><Name></h3>
  {#if status}
    <p>Status: {status.connected ? 'Connected' : 'Not connected'}</p>
    <p>Last sync: {status.last_sync ?? 'Never'}</p>
    <button on:click={sync}>Sync now</button>
  {:else}
    <p>Loading...</p>
  {/if}
</div>
```

For OAuth sources, add a "Connect" button that links to `/api/integrations/<source>/connect`.
For coros/runalyze (export-only), replace the connect flow with step-by-step export instructions.

---

## Step 6 — Update `.env.example`

Append the required env vars for this source to `.env.example` with placeholder values. If `.env.example` doesn't exist, create it.

---

## Step 7 — Confirm

List all files created and any routes added. Tell the user what manual steps remain (e.g. registering OAuth app credentials with the provider).
