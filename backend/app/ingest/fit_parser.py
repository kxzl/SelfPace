from __future__ import annotations

from pathlib import Path

import polyline
from fitparse import FitFile

SEMICIRCLES_TO_DEGREES = 180 / 2**31

RECORD_FIELD_MAP = {
    "timestamp": "timestamp",
    "position_lat": "latitude",
    "position_long": "longitude",
    "altitude": "altitude",
    "distance": "distance",
    "heart_rate": "heart_rate",
    "cadence": "cadence",
    "speed": "speed",
    "temperature": "temperature",
    "power": "power",
}


def parse_fit(path: Path) -> tuple[list[dict], dict]:
    """Parse a FIT file into (time-series rows, summary dict)."""
    fit = FitFile(str(path))
    rows: list[dict] = []

    for message in fit.get_messages("record"):
        row: dict = {}
        for field in message.fields:
            col = RECORD_FIELD_MAP.get(field.name)
            if col is None or field.value is None:
                continue
            value = field.value
            if field.name in ("position_lat", "position_long"):
                value = value * SEMICIRCLES_TO_DEGREES
            row[col] = value
        if "timestamp" in row:
            rows.append(row)

    summary = _extract_summary(fit, rows)
    return rows, summary


def _extract_summary(fit: FitFile, rows: list[dict]) -> dict:
    """Build summary from session message, falling back to computed values."""
    session: dict = {}
    for message in fit.get_messages("session"):
        for field in message.fields:
            session[field.name] = field.value
        break  # use first session

    sport = session.get("sport", "unknown")
    if hasattr(sport, "value"):
        sport = sport.value
    sport = str(sport).lower()

    start_time = session.get("start_time") or (rows[0]["timestamp"] if rows else None)
    total_elapsed = session.get("total_elapsed_time")
    if total_elapsed is None and len(rows) >= 2:
        delta = rows[-1]["timestamp"] - rows[0]["timestamp"]
        total_elapsed = delta.total_seconds()

    total_distance = session.get("total_distance")
    if total_distance is None and rows:
        distances = [r["distance"] for r in rows if "distance" in r]
        total_distance = distances[-1] if distances else 0.0

    avg_hr = session.get("avg_heart_rate")
    if avg_hr is None and rows:
        hrs = [r["heart_rate"] for r in rows if "heart_rate" in r]
        avg_hr = sum(hrs) / len(hrs) if hrs else None

    avg_cadence = session.get("avg_cadence")
    avg_speed = session.get("avg_speed") or session.get("enhanced_avg_speed")
    elevation_gain = session.get("total_ascent")

    encoded = _encode_polyline(rows)

    return {
        "sport": sport,
        "start_time": start_time,
        "duration_s": float(total_elapsed) if total_elapsed is not None else 0.0,
        "total_distance_m": float(total_distance) if total_distance is not None else 0.0,
        "avg_heart_rate": float(avg_hr) if avg_hr is not None else None,
        "avg_cadence": float(avg_cadence) if avg_cadence is not None else None,
        "avg_speed_ms": float(avg_speed) if avg_speed is not None else None,
        "elevation_gain_m": float(elevation_gain) if elevation_gain is not None else None,
        "polyline": encoded,
        "title": None,
    }


def _encode_polyline(rows: list[dict], max_points: int = 500) -> str | None:
    """Encode sampled lat/lon points as a polyline string."""
    coords = [
        (r["latitude"], r["longitude"])
        for r in rows
        if "latitude" in r and "longitude" in r
    ]
    if not coords:
        return None
    # sample down if too many points
    if len(coords) > max_points:
        step = len(coords) / max_points
        coords = [coords[int(i * step)] for i in range(max_points)]
    return polyline.encode(coords)
