---
allowed-tools: Bash, Read, Write, Edit
argument-hint: [metric-name]
---

Scaffold a new DuckDB metric with a UI display card. The metric name is: **$ARGUMENTS**

---

## Step 1 — Find reference metric

```bash
ls frontend/src/lib/metrics/*.ts 2>/dev/null | head -3
```

If a reference exists, read the first one. Use it as the structural template. If none exist, use the canonical template in step 3.

---

## Step 2 — Determine SQL and interface for this metric

Use the mapping below. If the metric is not listed, ask the user to describe it, then write the SQL.

| Metric | Output fields | SQL pattern |
|---|---|---|
| `race-predictor` | `{ distance_m, predicted_time_s }` | Riegel formula: `t2 = t1 * (d2/d1)^1.06` — use best recent race time as baseline |
| `ctl-atl` | `{ date, ctl, atl, tsb }` | 42-day and 7-day rolling avg of daily TSS (duration_s * avg_hr / max_hr * 100 as proxy TSS) |
| `stride-length` | `{ date, stride_m }` | `(avg_pace_ms * 60) / (avg_cadence * 2)` grouped by month |
| `weekly-tss` | `{ week, tss }` | Proxy TSS per week: `SUM(duration_s/3600 * 100)` |
| `long-run-streak` | `{ current_streak, longest_streak }` | Count consecutive weeks with a run > 16 km |
| `aerobic-efficiency` | `{ date, ae }` | Pace (min/km) divided by avg HR — lower is better; group by month |
| `elevation-per-km` | `{ month, m_per_km }` | `SUM(elevation_gain_m) / SUM(distance_m/1000)` grouped by month |

---

## Step 3 — Create the metric module

Create `frontend/src/lib/metrics/$ARGUMENTS.ts`:

```typescript
export interface <MetricName>Result {
  // Fields from step 2
}

export async function compute<MetricName>(db: any): Promise<<MetricName>Result[]> {
  const result = await db.query(`
    <SQL from step 2>
  `);
  return result.toArray().map((r: any) => r.toJSON()) as <MetricName>Result[];
}
```

---

## Step 4 — Create the display card component

Create `frontend/src/components/metrics/$ARGUMENTS.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { compute<MetricName> } from '../../lib/metrics/$ARGUMENTS';
  import type { <MetricName>Result } from '../../lib/metrics/$ARGUMENTS';

  let data: <MetricName>Result[] = [];
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    try {
      data = await compute<MetricName>(db);
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  });
</script>

<div class="metric-card">
  <h3>$ARGUMENTS</h3>
  {#if loading}
    <p>Computing...</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if data.length === 0}
    <p>No data available.</p>
  {:else}
    <!-- Render primary value or most recent entry -->
    <p class="value">{data[data.length - 1]?.value ?? JSON.stringify(data[data.length - 1])}</p>
  {/if}
</div>

<style>
  .metric-card { padding: 1rem; border: 1px solid #e2e8f0; border-radius: 0.5rem; }
  .value { font-size: 1.5rem; font-weight: bold; }
  .error { color: red; font-size: 0.875rem; }
</style>
```

---

## Step 5 — Export from metrics index

Check if `frontend/src/lib/metrics/index.ts` exists:

```bash
ls frontend/src/lib/metrics/index.ts 2>/dev/null
```

If it exists, add the export. If it doesn't exist, create it.

Add:
```typescript
export { compute<MetricName> } from './$ARGUMENTS';
export type { <MetricName>Result } from './$ARGUMENTS';
```

---

## Step 6 — Wire into dashboard

Find the dashboard or metrics page:

```bash
ls frontend/src/routes/dashboard.svelte frontend/src/pages/dashboard.svelte frontend/src/routes/index.svelte 2>/dev/null | head -1
```

Add the import and component:

```svelte
<script>
  import <MetricName>Card from '../components/metrics/$ARGUMENTS.svelte';
</script>

<!-- In the metrics section of the template: -->
<<MetricName>Card />
```

---

## Step 7 — Verify build

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Report the build result. If it fails, fix the error before finishing.
