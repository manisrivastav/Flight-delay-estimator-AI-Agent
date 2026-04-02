"""
opensky.py — Client for the OpenSky Network REST API.

Fetches live global aircraft state vectors (position, altitude, velocity, etc.).
The API is unauthenticated and rate-limited; avoid unnecessary calls.

Note: OpenSky is crowdsourced — coverage depends on volunteer ADS-B receivers
and may be incomplete for some airports/regions.
"""

import requests

# OpenSky REST endpoint for all current aircraft states
OPENSKY_URL = "https://opensky-network.org/api/states/all"

def fetch_opensky_states():
    """
    Fetch all current aircraft state vectors from OpenSky.
    Returns a list of state arrays (see OpenSky docs for field indices).
    Raises on HTTP errors or timeouts.
    """
    resp = requests.get(OPENSKY_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()["states"]
