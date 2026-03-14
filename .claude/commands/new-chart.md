---
allowed-tools: Bash, Read, Write, Edit
argument-hint: [ComponentName]
---

Scaffold a new Svelte chart component. The component name is: **$ARGUMENTS**

---

## Step 1 — Find reference component

```bash
ls frontend/src/components/charts/*.svelte 2>/dev/null | head -3
```

If a reference exists, read the first one found. Use it as the structural template. If none exist, use the canonical template below.

---

## Step 2 — Determine SQL for this chart

Use the mapping below. If the component name is not listed, ask the user to describe the query, then write it.

| Component | SQL pattern |
|---|---|
| `WeeklyMileage` | `SELECT date_trunc('week', started_at) AS week, SUM(distance_m)/1000 AS km FROM activities GROUP BY week ORDER BY week` |
| `PaceZones` | `SELECT CASE WHEN avg_pace_ms < 3.5 THEN 'Fast' WHEN avg_pace_ms < 4.5 THEN 'Moderate' ELSE 'Easy' END AS zone, COUNT(*) FROM activities WHERE activity_type='run' GROUP BY zone` |
| `HRDistribution` | `SELECT FLOOR(avg_hr/10)*10 AS hr_bucket, COUNT(*) AS count FROM activities WHERE avg_hr IS NOT NULL GROUP BY hr_bucket ORDER BY hr_bucket` |
| `MonthlyVolume` | `SELECT date_trunc('month', started_at) AS month, SUM(distance_m)/1000 AS km, SUM(duration_s)/3600 AS hours FROM activities GROUP BY month ORDER BY month` |
| `LongRunProgression` | `SELECT started_at::DATE AS date, distance_m/1000 AS km FROM activities WHERE activity_type='run' AND distance_m > 16000 ORDER BY date` |
| `CadenceTrend` | `SELECT date_trunc('month', started_at) AS month, AVG(avg_cadence) AS cadence FROM activities WHERE avg_cadence IS NOT NULL GROUP BY month ORDER BY month` |
| `ElevationGain` | `SELECT date_trunc('week', started_at) AS week, SUM(elevation_gain_m) AS gain FROM activities WHERE elevation_gain_m IS NOT NULL GROUP BY week ORDER BY week` |

---

## Step 3 — Create the component

Create `frontend/src/components/charts/$ARGUMENTS.svelte`:

```svelte
<script>
  import { onMount } from 'svelte';
  import * as Plot from '@observablehq/plot';

  let container;
  let error = null;

  onMount(async () => {
    try {
      // db is the DuckDB WASM instance initialized in the app root
      const result = await db.query(`
        <SQL from step 2>
      `);
      const data = result.toArray().map(r => r.toJSON());

      const chart = Plot.plot({
        // Configure marks based on chart type
        marks: [
          Plot.barY(data, { x: '<x-field>', y: '<y-field>', fill: 'steelblue' })
        ],
        width: container.clientWidth,
        marginBottom: 40
      });

      container.replaceChildren(chart);
    } catch (e) {
      error = e.message;
    }
  });
</script>

{#if error}
  <p class="error">Chart error: {error}</p>
{:else}
  <div bind:this={container} class="chart-container"></div>
{/if}

<style>
  .chart-container { width: 100%; min-height: 200px; }
  .error { color: red; font-size: 0.875rem; }
</style>
```

Adjust the `Plot.plot()` marks to match the chart type:
- Time series → `Plot.lineY` + `Plot.dot`
- Histogram / bar → `Plot.barY`
- Distribution → `Plot.rectY` with `Plot.binX`

---

## Step 4 — Wire into the appropriate page

Find the most relevant page file:

```bash
ls frontend/src/routes/*.svelte 2>/dev/null || ls frontend/src/pages/*.svelte 2>/dev/null
```

Add the import and component tag to the appropriate page:

```svelte
<script>
  import $ARGUMENTS from '../components/charts/$ARGUMENTS.svelte';
</script>

<!-- In the template: -->
<$ARGUMENTS />
```

---

## Step 5 — Verify build

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Report the build result. If it fails, fix the error before finishing.
