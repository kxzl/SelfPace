select
    sport,
    title,
    start_time,
    round(total_distance_m / 1000, 2) as distance_km,
    round(duration_s / 60, 1) as duration_min,
    round(avg_heart_rate, 0) as avg_hr,
    round(avg_cadence, 0) as avg_cadence,
    round(avg_speed_ms * 3.6, 1) as avg_speed_kmh,
    round(elevation_gain_m, 0) as elevation_gain_m
from read_parquet('/data/parquet/manifest.parquet')
order by start_time desc
