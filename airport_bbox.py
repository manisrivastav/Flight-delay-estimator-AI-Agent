"""
airport_bbox.py — Computes a geographic bounding box around an airport.

Uses the `airportsdata` library for official airport coordinates, then
samples live ground traffic from OpenSky to refine the bbox to the
actual active area. Results are cached in-memory (resets on restart).
"""

import math
import airportsdata
from opensky import fetch_opensky_states

# Load the full ICAO airport database once at import time
AIRPORT_DB = airportsdata.load('ICAO')

# In-memory cache: avoids recomputing the bbox for the same airport
_BBOX_CACHE = {}

def compute_airport_bbox_from_opensky(
    airport_icao: str,
    buffer_deg: float = 0.01,
    max_samples: int = 5
) -> dict:
    """
    Build a lat/lon bounding box around an airport by:
      1. Looking up official coordinates from airportsdata.
      2. Sampling live OpenSky states for aircraft near the airport that are
         on the ground (alt < 50ft) and nearly stationary (< 5kt).
      3. Creating a bbox from those sample points + a small buffer.

    Args:
        airport_icao: 4-letter ICAO code (e.g. "KSFO").
        buffer_deg:   Degrees of padding around the sampled points.
        max_samples:  Stop after collecting this many ground points.

    Returns:
        dict with lat_min, lat_max, lon_min, lon_max.

    Raises:
        ValueError if the ICAO code is unknown or no ground traffic is found.
    """
    # 1. Return cached result if available
    if airport_icao in _BBOX_CACHE:
        return _BBOX_CACHE[airport_icao]

    print("AIRPORT CODE:*****", airport_icao)

    # 2. Get official airport coordinates from the database
    airport_info = AIRPORT_DB.get(airport_icao.upper())
    if not airport_info:
        raise ValueError(f"Airport ICAO '{airport_icao}' not found in database.")

    ref_lat = airport_info['lat']
    ref_lon = airport_info['lon']

    # 3. Fetch live global states and find aircraft on the ground near the airport
    states = fetch_opensky_states()
    points = []

    for s in states:
        lat, lon = s[6], s[5]
        alt = s[7] or 0
        speed = (s[9] or 0) * 1.94384  # Convert m/s to knots

        if lat and lon:
            # Rough Euclidean distance in degrees (~0.05 deg ≈ 5.5 km)
            dist = math.sqrt((lat - ref_lat)**2 + (lon - ref_lon)**2)

            # Keep only aircraft that are near the airport, on the ground, and nearly stopped
            if dist < 0.05 and alt < 50 and speed < 5:
                points.append((lat, lon))
                if len(points) >= max_samples:
                    break

    if not points:
        raise ValueError(f"No ground traffic observed at {airport_icao} right now.")

    # 4. Build the bounding box from sampled points + buffer
    lats, lons = zip(*points)
    bbox = {
        "lat_min": min(lats) - buffer_deg,
        "lat_max": max(lats) + buffer_deg,
        "lon_min": min(lons) - buffer_deg,
        "lon_max": max(lons) + buffer_deg,
    }

    _BBOX_CACHE[airport_icao] = bbox
    return bbox

