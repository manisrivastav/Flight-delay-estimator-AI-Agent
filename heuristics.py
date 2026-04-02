"""
heuristics.py — Pure functions for departure candidate filtering and window estimation.

No external API calls — this module is kept dependency-free for easy testability.
"""


def within_bbox(lat, lon, bbox):
    """Check if a lat/lon point falls inside the given bounding box."""
    return (
        bbox["lat_min"] <= lat <= bbox["lat_max"]
        and bbox["lon_min"] <= lon <= bbox["lon_max"]
    )


def estimate_departure_window(speed_kt):
    """
    Estimate how soon a flight will depart based on its current ground speed.
    Faster taxi speed = closer to takeoff.
    """
    if speed_kt >= 25:
        return "0–15 min"
    elif speed_kt >= 15:
        return "15–30 min"
    elif speed_kt >= 5:
        return "30–60 min"
    return ">60 min"


def is_departure_candidate(state, bbox):
    """
    Determine if a flight is a likely departure candidate.
    Criteria:
      - Has a callsign
      - Located within the airport bounding box
      - Below 500 ft altitude (still on or near the ground)
      - Ground speed between 5–40 knots (taxiing, not parked or airborne)
    """
    if not state["callsign"]:
        return False

    if not within_bbox(state["lat"], state["lon"], bbox):
        return False

    alt = state["baro_altitude"] or 0
    speed_kt = (state["velocity"] or 0) * 1.94384  # m/s to knots

    return alt < 500 and 5 <= speed_kt <= 40
 