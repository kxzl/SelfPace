from __future__ import annotations

from pathlib import Path

import gpxpy
import polyline


def parse_gpx(path: Path) -> tuple[list[dict], dict]:
    """Parse a GPX file into (time-series rows, summary dict)."""
    with open(path) as f:
        gpx = gpxpy.parse(f)

    rows: list[dict] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if point.time is None:
                    continue
                row: dict = {
                    "timestamp": point.time,
                    "latitude": point.latitude,
                    "longitude": point.longitude,
                }
                if point.elevation is not None:
                    row["altitude"] = float(point.elevation)

                extensions = _parse_extensions(point)
                row.update(extensions)
                rows.append(row)

    # compute cumulative distance
    _add_cumulative_distance(rows)

    summary = _build_summary(gpx, rows)
    return rows, summary


def _parse_extensions(point) -> dict:
    """Extract HR, cadence, temperature, power from Garmin TrackPointExtension."""
    result: dict = {}
    for ext in point.extensions:
        for child in ext:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "hr" and child.text:
                result["heart_rate"] = int(child.text)
            elif tag == "cad" and child.text:
                result["cadence"] = int(child.text)
            elif tag == "atemp" and child.text:
                result["temperature"] = int(float(child.text))
            elif tag == "power" and child.text:
                result["power"] = int(child.text)
    return result


def _add_cumulative_distance(rows: list[dict]) -> None:
    """Compute cumulative distance in meters from lat/lon using gpxpy."""
    if len(rows) < 2:
        return
    cumulative = 0.0
    rows[0]["distance"] = 0.0
    for i in range(1, len(rows)):
        prev, curr = rows[i - 1], rows[i]
        d = gpxpy.geo.haversine_distance(
            prev["latitude"], prev["longitude"],
            curr["latitude"], curr["longitude"],
        )
        cumulative += d
        curr["distance"] = cumulative


def _compute_speed(rows: list[dict]) -> None:
    """Compute speed (m/s) between consecutive points."""
    if len(rows) < 2:
        return
    for i in range(1, len(rows)):
        prev, curr = rows[i - 1], rows[i]
        dt = (curr["timestamp"] - prev["timestamp"]).total_seconds()
        if dt > 0 and "distance" in curr and "distance" in prev:
            curr["speed"] = float(curr["distance"] - prev["distance"]) / dt


def _build_summary(gpx, rows: list[dict]) -> dict:
    """Build summary dict from GPX data."""
    sport = "unknown"
    if gpx.tracks:
        t = gpx.tracks[0].type
        if t:
            sport = t.lower()

    start_time = rows[0]["timestamp"] if rows else None
    duration_s = 0.0
    if len(rows) >= 2:
        duration_s = (rows[-1]["timestamp"] - rows[0]["timestamp"]).total_seconds()

    total_distance = 0.0
    if rows:
        distances = [r["distance"] for r in rows if "distance" in r]
        total_distance = distances[-1] if distances else 0.0

    hrs = [r["heart_rate"] for r in rows if "heart_rate" in r]
    avg_hr = sum(hrs) / len(hrs) if hrs else None

    cads = [r["cadence"] for r in rows if "cadence" in r]
    avg_cad = sum(cads) / len(cads) if cads else None

    avg_speed = total_distance / duration_s if duration_s > 0 else None

    uphill, _ = _compute_elevation(rows)

    coords = [(r["latitude"], r["longitude"]) for r in rows if "latitude" in r and "longitude" in r]
    encoded = None
    if coords:
        if len(coords) > 500:
            step = len(coords) / 500
            coords = [coords[int(i * step)] for i in range(500)]
        encoded = polyline.encode(coords)

    return {
        "sport": sport,
        "start_time": start_time,
        "duration_s": duration_s,
        "total_distance_m": total_distance,
        "avg_heart_rate": float(avg_hr) if avg_hr is not None else None,
        "avg_cadence": float(avg_cad) if avg_cad is not None else None,
        "avg_speed_ms": float(avg_speed) if avg_speed is not None else None,
        "elevation_gain_m": float(uphill) if uphill is not None else None,
        "polyline": encoded,
        "title": None,
    }


def _compute_elevation(rows: list[dict]) -> tuple[float | None, float | None]:
    """Compute total elevation gain and loss."""
    altitudes = [r["altitude"] for r in rows if "altitude" in r]
    if len(altitudes) < 2:
        return None, None
    gain = 0.0
    loss = 0.0
    for i in range(1, len(altitudes)):
        diff = altitudes[i] - altitudes[i - 1]
        if diff > 0:
            gain += diff
        else:
            loss += abs(diff)
    return gain, loss
