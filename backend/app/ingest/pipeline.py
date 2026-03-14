from __future__ import annotations

import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from .schemas import MANIFEST_DDL, RUNALYZE_SPORT_MAP_SQL

logger = logging.getLogger(__name__)

DB_PATH = "/data/db/selfpace.db"


@dataclass
class IngestResult:
    processed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def get_db() -> duckdb.DuckDBPyConnection:
    """Return a connection to the persistent DuckDB database."""
    con = duckdb.connect(DB_PATH)
    con.execute(MANIFEST_DDL)
    return con


def run_ingest(
    imports_dir: Path,
    raw_dir: Path,
    parquet_dir: Path,
) -> IngestResult:
    """Scan imports_dir, ingest files via DuckDB, write parquet."""
    result = IngestResult()
    manifest_path = parquet_dir / "manifest.parquet"

    # Unzip any ZIPs first
    _unzip_all(imports_dir)

    con = get_db()

    # Load existing manifest into DuckDB if parquet exists but table is empty
    _sync_manifest_from_parquet(con, manifest_path)

    # Handle CSV files
    for csv_path in list(imports_dir.glob("*.csv")):
        csv_result = _ingest_csv(con, csv_path)
        result.processed += csv_result.processed
        result.skipped += csv_result.skipped
        result.errors.extend(csv_result.errors)
        # Move to raw
        shutil.move(str(csv_path), str(raw_dir / csv_path.name))

    # Handle FIT/GPX files (keep Python parsers for binary formats)
    files = _collect_files(imports_dir)
    for file_path, source in files:
        source_file = file_path.name
        existing = con.execute(
            "SELECT 1 FROM manifest WHERE source_file = ?", [source_file]
        ).fetchone()
        if existing:
            result.skipped += 1
            continue

        try:
            from .fit_parser import parse_fit
            from .gpx_parser import parse_gpx

            suffix = file_path.suffix.lower()
            if suffix == ".fit":
                rows, summary = parse_fit(file_path)
            elif suffix == ".gpx":
                rows, summary = parse_gpx(file_path)
            else:
                continue

            if not rows:
                result.errors.append(f"{source_file}: no data points")
                continue

            _ingest_activity(con, rows, summary, source, source_file, parquet_dir)
            result.processed += 1

            dest = raw_dir / source_file
            if dest.exists():
                dest = raw_dir / f"{summary.get('activity_id', '')}_{source_file}"
            shutil.move(str(file_path), str(dest))

        except Exception as e:
            result.errors.append(f"{source_file}: {e}")
            logger.error("Parse error: %s: %s", source_file, e)

    # Export manifest to parquet
    if result.processed > 0:
        con.execute(f"COPY manifest TO '{manifest_path}' (FORMAT PARQUET)")

    con.close()
    _cleanup_empty_dirs(imports_dir)
    return result


def _sync_manifest_from_parquet(con: duckdb.DuckDBPyConnection, manifest_path: Path) -> None:
    """Load manifest from parquet into DuckDB table if table is empty and file exists."""
    count = con.execute("SELECT count(*) FROM manifest").fetchone()[0]
    if count == 0 and manifest_path.exists():
        con.execute(f"INSERT INTO manifest SELECT * FROM read_parquet('{manifest_path}')")


def _ingest_csv(con: duckdb.DuckDBPyConnection, csv_path: Path) -> IngestResult:
    """Ingest a Runalyze CSV export using DuckDB SQL."""
    result = IngestResult()
    sport_map = RUNALYZE_SPORT_MAP_SQL

    try:
        # Count what's already in manifest for dedup
        count_before = con.execute("SELECT count(*) FROM manifest").fetchone()[0]

        con.execute(f"""
            INSERT INTO manifest
            SELECT
                uuid()                          AS activity_id,
                'runalyze'                      AS source,
                'runalyze_' || CAST(id AS VARCHAR) AS source_file,
                {sport_map}                     AS sport,
                to_timestamp(CAST(time AS BIGINT))
                    AT TIME ZONE 'UTC'          AS start_time,
                COALESCE(CAST(NULLIF(elapsedTime, '') AS DOUBLE),
                         CAST(NULLIF(s, '') AS DOUBLE), 0) AS duration_s,
                COALESCE(
                    TRY_CAST(replace(distance, 'km', '') AS DOUBLE) * 1000,
                    0
                )                               AS total_distance_m,
                TRY_CAST(NULLIF(pulseAvg, '') AS FLOAT) AS avg_heart_rate,
                TRY_CAST(NULLIF(cadence, '') AS FLOAT)  AS avg_cadence,
                CASE
                    WHEN TRY_CAST(replace(distance, 'km', '') AS DOUBLE) > 0
                         AND COALESCE(CAST(NULLIF(s, '') AS DOUBLE), 0) > 0
                    THEN (TRY_CAST(replace(distance, 'km', '') AS DOUBLE) * 1000)
                         / CAST(NULLIF(s, '') AS DOUBLE)
                    ELSE NULL
                END                             AS avg_speed_ms,
                TRY_CAST(NULLIF(elevationUp, '') AS FLOAT) AS elevation_gain_m,
                NULL                            AS polyline,
                NULLIF(title, '')               AS title,
                now()                           AS ingested_at
            FROM read_csv_auto('{csv_path}', header=true, all_varchar=true) csv
            WHERE ('runalyze_' || CAST(csv.id AS VARCHAR)) NOT IN (
                SELECT source_file FROM manifest
            )
        """)

        count_after = con.execute("SELECT count(*) FROM manifest").fetchone()[0]
        result.processed = count_after - count_before
        logger.info("CSV ingest: %d rows from %s", result.processed, csv_path.name)

    except Exception as e:
        result.errors.append(f"{csv_path.name}: {e}")
        logger.error("CSV ingest error: %s", e)

    return result


def _ingest_activity(
    con: duckdb.DuckDBPyConnection,
    rows: list[dict],
    summary: dict,
    source: str,
    source_file: str,
    parquet_dir: Path,
) -> None:
    """Write a single FIT/GPX activity's time-series to parquet and add to manifest."""
    activity_id = con.execute("SELECT uuid()").fetchone()[0]
    activities_dir = parquet_dir / "activities"
    activities_dir.mkdir(parents=True, exist_ok=True)

    # Write time-series via DuckDB
    con.execute("CREATE OR REPLACE TEMP TABLE ts_staging AS SELECT * FROM unnest(?)", [rows])
    out_path = activities_dir / f"{activity_id}.parquet"
    con.execute(f"COPY ts_staging TO '{out_path}' (FORMAT PARQUET)")
    con.execute("DROP TABLE ts_staging")

    # Insert manifest row
    con.execute(
        """INSERT INTO manifest VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())""",
        [
            activity_id,
            source,
            source_file,
            summary.get("sport", "unknown"),
            summary.get("start_time"),
            summary.get("duration_s", 0.0),
            summary.get("total_distance_m", 0.0),
            summary.get("avg_heart_rate"),
            summary.get("avg_cadence"),
            summary.get("avg_speed_ms"),
            summary.get("elevation_gain_m"),
            summary.get("polyline"),
            summary.get("title"),
        ],
    )


def _unzip_all(imports_dir: Path) -> None:
    """Unzip all ZIP files in imports_dir."""
    for zip_path in list(imports_dir.glob("*.zip")):
        extract_dir = imports_dir / zip_path.stem
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
        zip_path.unlink()


def _detect_source(filename: str) -> str:
    name_lower = filename.lower()
    if "runalyze" in name_lower:
        return "runalyze"
    if "coros" in name_lower:
        return "coros"
    return "manual"


def _collect_files(imports_dir: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for ext in ("*.fit", "*.FIT", "*.gpx", "*.GPX"):
        for f in imports_dir.rglob(ext):
            files.append((f, _detect_source(f.name)))
    return sorted(files, key=lambda x: x[0].name)


def _cleanup_empty_dirs(directory: Path) -> None:
    for d in sorted(directory.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
