"""DuckDB schema definitions for SelfPace parquet files."""

MANIFEST_DDL = """
CREATE TABLE IF NOT EXISTS manifest (
    activity_id     VARCHAR NOT NULL,
    source          VARCHAR NOT NULL,
    source_file     VARCHAR NOT NULL,
    sport           VARCHAR NOT NULL,
    start_time      TIMESTAMPTZ NOT NULL,
    duration_s      DOUBLE NOT NULL,
    total_distance_m DOUBLE NOT NULL,
    avg_heart_rate  FLOAT,
    avg_cadence     FLOAT,
    avg_speed_ms    FLOAT,
    elevation_gain_m FLOAT,
    polyline        VARCHAR,
    title           VARCHAR,
    ingested_at     TIMESTAMPTZ NOT NULL
);
"""

TIMESERIES_DDL = """
CREATE TABLE IF NOT EXISTS activity (
    timestamp   TIMESTAMPTZ NOT NULL,
    latitude    DOUBLE,
    longitude   DOUBLE,
    altitude    FLOAT,
    distance    DOUBLE,
    heart_rate  UTINYINT,
    cadence     UTINYINT,
    speed       FLOAT,
    temperature TINYINT,
    power       USMALLINT
);
"""

RUNALYZE_SPORT_MAP_SQL = """
CASE sportid
    WHEN '851796' THEN 'running'
    WHEN '851798' THEN 'cycling'
    WHEN '851800' THEN 'strength'
    WHEN '851801' THEN 'other'
    WHEN '851802' THEN 'yoga'
    WHEN '851803' THEN 'walking'
    WHEN '851804' THEN 'rowing'
    WHEN '851805' THEN 'climbing'
    WHEN '851812' THEN 'cycling_indoor'
    WHEN '1033822' THEN 'hiit'
    WHEN '1267418' THEN 'hiking'
    WHEN '1453451' THEN 'skiing'
    WHEN '1965506' THEN 'skiing'
    ELSE 'other'
END
"""
