# SelfPace — Decisions & Lessons Log

A running record of decisions made, approaches tried, and outcomes. The goal is to prevent future contributors from re-litigating settled questions or repeating dead ends.

Each entry has a date, a status, and a clear "what we decided / what we learned" conclusion. Add new entries at the top of each section.

---

## How to Add an Entry

```
### YYYY-MM-DD — Short title
**Status**: decided | tried-worked | tried-failed | reversed
**Context**: Why this came up.
**What we did**: The approach taken.
**Outcome**: What happened, what didn't work and why.
**Decision**: What to do going forward.
```

---

## Architecture

### 2026-03-14 — DuckDB WASM for all client-side querying
**Status**: decided
**Context**: Needed a way to run analytics on potentially large activity datasets without running a database server.
**What we did**: Chose DuckDB WASM — queries run entirely in the browser against Parquet files served as static files from nginx. No backend query layer needed.
**Outcome**: Not yet implemented.
**Decision**: Proceed. Avoids a database service, keeps the backend stateless for queries, and lets the frontend own the analytics entirely. If WASM performance on mobile proves too slow, revisit with a lightweight server-side DuckDB query endpoint as an opt-in fallback.

### 2026-03-14 — Two-service Docker Compose (frontend + backend only)
**Status**: decided
**Context**: Considered whether to add dedicated services for a task queue (Celery + Redis), a database server, or a separate data-processing worker.
**What we did**: Deliberately kept it to two services. APScheduler runs inside the FastAPI process. Parquet files on a shared volume replace a database server.
**Outcome**: Not yet implemented.
**Decision**: Resist adding services until a concrete bottleneck forces it. A third service (e.g., a Redis broker) adds operational overhead that is not justified at this scale.

### 2026-03-14 — Parquet as the canonical storage format
**Status**: decided
**Context**: Needed a format that DuckDB WASM can query directly over HTTP without a server-side layer, while also being efficient for time-series activity data.
**What we did**: Chose Parquet. Raw source files (FIT, GPX) are preserved in `/data/raw/` and never modified. Backend converts to Parquet on ingest.
**Outcome**: Not yet implemented.
**Decision**: One Parquet file per activity. A small manifest JSON (or single catalog Parquet) tracks which activities have been imported and their source IDs for deduplication.

---

## Integrations

### 2026-03-14 — Integration build order
**Status**: decided
**Context**: Multiple data sources with varying complexity. Needed to avoid building OAuth flows for low-traffic sources before validating the core pipeline.
**What we did**: Ranked integrations by effort-to-coverage ratio. Intervals.icu first (API key, no OAuth), then Strava (OAuth but large user base), then Runalyze export (bulk historical data with no API needed), then manual drop zone, then Garmin.
**Outcome**: Not yet implemented.
**Decision**: Do not start TrainingPeaks or Suunto OAuth flows until there is demonstrated user demand. Manual export fallback is sufficient for both.

### 2026-03-14 — Garmin Connect via `garth` (unofficial SSO)
**Status**: decided (with risk flag)
**Context**: Garmin's official Health API requires approval and is designed for enterprise integrations. The `garth` Python library implements Garmin's SSO flow to give programmatic access without approval.
**What we did**: Chose `garth` as the primary Garmin sync method, with manual ZIP export as the documented fallback.
**Outcome**: Not yet implemented.
**Decision**: Treat `garth` as a best-effort integration. If Garmin changes their SSO and breaks `garth`, fall back to export-only without spending time reverse-engineering the new flow. Document this clearly in the UI so users are not surprised.

### 2026-03-14 — Coros: export-only, no API integration
**Status**: decided
**Context**: Coros has no public API and no unofficial API library with meaningful adoption.
**What we did**: Decided not to invest time in reverse-engineering Coros's mobile/web API. Instead, the UI will show step-by-step export instructions.
**Outcome**: N/A — this is a non-decision to avoid wasted effort.
**Decision**: Revisit only if an official API is announced or a well-maintained community library emerges.

### 2026-03-14 — Runalyze API vs. export
**Status**: decided (export first)
**Context**: Runalyze has an undocumented `/api/v1/` endpoint. It could enable incremental sync, but its stability is unknown.
**What we did**: Prioritized the bulk ZIP export path first. Incremental API sync is listed as a later enhancement.
**Outcome**: Not yet implemented.
**Decision**: Build export ingestion first. Only add API sync if the export workflow is actively painful for users (e.g., they re-export weekly). Validate the API endpoints manually before building against them.

### 2026-03-14 — Intervals.icu as highest-priority API integration
**Status**: decided
**Context**: Evaluated all source integrations for ease of implementation vs. data coverage. Intervals.icu stood out: API key auth (no OAuth), free, well-documented, and already aggregates data from Garmin, Strava, Wahoo, and others for many serious runners.
**What we did**: Moved Intervals.icu to the top of the integration priority list.
**Outcome**: Not yet implemented.
**Decision**: Implement Intervals.icu first. A user already on Intervals.icu may not need Garmin or Strava integrations at all, reducing total integration surface significantly.

---

## Frontend

### 2026-03-14 — Svelte as the frontend framework
**Status**: decided
**Context**: Needed a framework that compiles to a small, fast static bundle with minimal runtime overhead, since the app will be self-hosted and performance on lower-end hardware matters.
**What we did**: Chose Svelte (with Vite) built inside a Node container, output served by nginx.
**Outcome**: Not yet implemented.
**Decision**: If the team is more comfortable with Vue or React, the switch is low-cost at this stage — the architecture does not depend on the specific framework. The important constraint is that it produces a static build deployable to nginx.

---

## What Not to Do

A short list of specific approaches that were explicitly ruled out and why, so they don't get re-proposed:

| Approach | Reason ruled out |
|---|---|
| Database server (Postgres, SQLite service) | DuckDB WASM + Parquet makes a query server unnecessary; adds a service with no benefit |
| Celery + Redis for background jobs | APScheduler inside FastAPI is sufficient; two extra services not justified |
| Garmin official Health API | Requires enterprise approval process; `garth` + manual export covers the same use case |
| Suunto / TrainingPeaks OAuth (now) | Manual export fallback is adequate; OAuth approval gates add friction with no near-term payoff |
| Building a custom auth system | Single-user app; HTTP basic auth via nginx is sufficient if hosted beyond localhost |
| Reverse-engineering Coros API | No stable community library; not worth the maintenance burden |
