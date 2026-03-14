---
allowed-tools: Bash
---

Run a DuckDB audit of the activity data in `/data/parquet/`. Then write a 3–5 sentence data health summary.

## Step 1 — Guard: check for data

```bash
find /data/parquet -name '*.parquet' 2>/dev/null | wc -l
```

If the count is 0, stop and tell the user: "No Parquet files found in /data/parquet/. Run a sync first (e.g. `/dev up` then trigger a sync from the UI or `POST /integrations/<source>/sync`)."

---

## Step 2 — Run all five audit queries

```bash
python3 - << 'EOF'
import duckdb, sys

PARQUET = "/data/parquet/*.parquet"

try:
    con = duckdb.connect()

    print("=== 1. Activity count by source ===")
    print(con.execute(f"""
        SELECT source, COUNT(*) AS activities
        FROM read_parquet('{PARQUET}')
        GROUP BY source
        ORDER BY activities DESC
    """).df().to_string(index=False))

    print("\n=== 2. Date range by source ===")
    print(con.execute(f"""
        SELECT source,
               MIN(started_at)::DATE AS earliest,
               MAX(started_at)::DATE AS latest,
               COUNT(*) AS total
        FROM read_parquet('{PARQUET}')
        GROUP BY source
        ORDER BY source
    """).df().to_string(index=False))

    print("\n=== 3. Activity type breakdown ===")
    print(con.execute(f"""
        SELECT activity_type, COUNT(*) AS count
        FROM read_parquet('{PARQUET}')
        GROUP BY activity_type
        ORDER BY count DESC
    """).df().to_string(index=False))

    print("\n=== 4. Null rates for key fields ===")
    print(con.execute(f"""
        SELECT
            ROUND(100.0 * SUM(CASE WHEN avg_hr IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS hr_null_pct,
            ROUND(100.0 * SUM(CASE WHEN avg_cadence IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS cadence_null_pct,
            ROUND(100.0 * SUM(CASE WHEN polyline IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS gps_null_pct,
            ROUND(100.0 * SUM(CASE WHEN distance_m IS NULL OR distance_m = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS distance_null_pct
        FROM read_parquet('{PARQUET}')
    """).df().to_string(index=False))

    print("\n=== 5. Potential duplicates (same date + distance, different source) ===")
    print(con.execute(f"""
        SELECT
            started_at::DATE AS date,
            ROUND(distance_m) AS distance_m,
            COUNT(DISTINCT source) AS sources,
            LIST(DISTINCT source) AS source_list,
            COUNT(*) AS total_records
        FROM read_parquet('{PARQUET}')
        GROUP BY date, ROUND(distance_m)
        HAVING COUNT(DISTINCT source) > 1
        ORDER BY date DESC
        LIMIT 20
    """).df().to_string(index=False))

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
```

---

## Step 3 — Write a data health summary

Based on the query output above, write a **3–5 sentence data health summary** covering:
- Total activity count and source breakdown
- Date range of data
- Any notable null rate issues (flag if HR or GPS null rate > 20%)
- Any duplicate concerns found
