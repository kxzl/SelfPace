---
allowed-tools: Bash, Read
---

You are loading context for a new SelfPace development session. Run all blocks below, then deliver a 150-word situational summary.

## 1. Recent git history

```bash
git log --oneline -8
```

## 2. Working tree status

```bash
git status --short
```

## 3. Docker service state

```bash
docker compose ps 2>/dev/null || echo "[docker not running or no compose file yet]"
```

## 4. Data volume stats

```bash
find /data/parquet -name '*.parquet' 2>/dev/null | wc -l && echo "parquet files found" || echo "[/data/parquet not mounted]"
```

## 5. What Not to Do (ruled-out approaches)

```bash
sed -n '/^## What Not to Do/,/^---/p' decisions.md
```

## 6. Integration priority (hardcoded — do not re-read agents.md)

Build order:
1. **Intervals.icu** — API key auth, no OAuth, normalizes data from many upstream devices
2. **Strava** — largest user base, well-documented OAuth
3. **Runalyze** (export) — bulk historical import, covers Garmin/Polar/Suunto users
4. **Manual drop zone** — universal fallback, always needed
5. **Garmin Connect** (`garth`) — highest data richness but unofficial API risk
6. **Runalyze** (API sync) — incremental sync on top of bulk export
7. **Polar Flow** — OAuth-gated, lower user base
8. **TrainingPeaks** — manual approval gate; export fallback adequate
9. **Suunto** — low priority; manual export covers most users
10. **Coros** — manual export only, no API exists

## 7. Key architecture facts (hardcoded)

- Two Docker services: `frontend` (nginx SPA on :3000) + `backend` (FastAPI on :8000)
- DuckDB WASM queries Parquet files served as static files from nginx — no backend query layer
- APScheduler runs inside FastAPI — no Celery/Redis
- Data layout: `/data/raw/`, `/data/parquet/`, `/data/db/`, `/data/imports/`
- Canonical activity schema: `activity_id, source, source_id, started_at, distance_m, duration_s, activity_type, avg_hr, avg_cadence, avg_pace_ms, elevation_gain_m, polyline`

---

Now give a **150-word situational summary**: what stage the project is at, what the most recent work touched, which integration is next, and any open blockers visible from the above output.
