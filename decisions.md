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

### 2026-03-14 — GPS route maps via custom Leaflet component in Evidence
**Status**: decided
**Context**: Evidence's built-in map components (point, bubble, area) cover aggregate geo views but have no polyline/route layer. Run activity maps require rendering GPS tracks from encoded polyline strings stored in Parquet.
**What we did**: Decided to write a single custom Svelte component (`RouteMap.svelte`) wrapping Leaflet.js. Evidence supports custom components in `/components/` that can use any npm package. The component decodes the polyline column from a DuckDB query result and renders it on an OpenStreetMap tile layer via `L.polyline().addTo(map)`.
**Outcome**: Not yet implemented.
**Decision**: Use Leaflet + `@mapbox/polyline` for decoding. Component receives query results as a prop (`data={query_result}`), so the SQL stays in Evidence markdown pages and the component stays generic. OpenStreetMap tiles require no API key. If a multi-activity heatmap is needed later, evaluate deck.gl or MapLibre GL at that point.

### 2026-03-14 — Evidence.dev as the frontend framework (replaces hand-rolled Svelte SPA)
**Status**: decided
**Context**: The original plan was a custom Svelte SPA with manual DuckDB WASM setup, Parquet fetching, and Observable Plot charts. Evidence.dev is an open-source BI-as-code framework built on SvelteKit + DuckDB WASM + Parquet — the exact same core stack — that eliminates most of that boilerplate.
**What we did**: Evaluated Evidence against all project requirements. Evidence builds to a static site served by nginx, uses DuckDB WASM natively, queries Parquet files over HTTP, and allows custom Svelte components for anything outside its built-in component library.
**Outcome**: Not yet implemented.
**Decision**: Use Evidence as the frontend. Write analytics pages as SQL + Markdown. Use Evidence's built-in components (ECharts-backed) for charts and aggregate maps. Write custom Svelte components only for GPS route rendering (Leaflet) and OAuth connection UI. FastAPI backend is unchanged — it still owns all data ingestion, OAuth flows, and Parquet writing. After each sync, FastAPI triggers an Evidence rebuild so the static site reflects new data.

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
| Hand-rolled Svelte SPA + DuckDB WASM setup | Evidence.dev already provides this entire layer; building it manually adds weeks of work for no gain |
| Evidence built-in map components for GPS routes | Built-in components only support points/bubbles/areas — no polyline layer; custom Leaflet component required |
