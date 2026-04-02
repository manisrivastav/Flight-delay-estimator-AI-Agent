"""
graph.py — LangGraph pipeline definition for the Airport Risk Monitor.

Defines a 3-node state machine:
  1. detect_departures  — find ground-level departure candidates at the airport
  2. get_weather        — fetch METAR/TAF via the MCP weather server
  3. estimate_delays    — run each flight through the LLM for risk assessment

The compiled graph is exported as `app` for use by the Streamlit frontend.
"""

from typing import Dict, List, TypedDict, Annotated
import operator
from langgraph.graph import StateGraph

from opensky import fetch_opensky_states
from heuristics import is_departure_candidate, estimate_departure_window
from llm import assess_delay
from weather import fetch_weather_via_mcp
from airport_bbox import compute_airport_bbox_from_opensky

# ------------------------------------------------------------
# State schema — shared across all nodes in the graph
# ------------------------------------------------------------
class FlightState(TypedDict):
    airport: str          # ICAO code of the target airport (input)
    flights: List[Dict]   # Departure candidate flights (set by node 1)
    weather: Dict         # METAR/TAF weather data (set by node 2)
    results: List[Dict]   # Final delay assessments (set by node 3)

# ------------------------------------------------------------
# Node 1: Detect departure candidates
# ------------------------------------------------------------
def detect_departure_candidates(state: FlightState) -> Dict:
    """
    Node 1: Identify flights that are likely preparing to depart.

    Steps:
      - Compute a geographic bounding box around the airport using airportsdata + live ground traffic.
      - Fetch all global flight states from OpenSky.
      - Filter for flights within the bbox that match departure heuristics (low altitude, taxi speed).
      - Estimate a departure window based on ground speed.
    """
    print(f"--- DETECTING DEPARTURES FOR: {state['airport']} ---")
    airport = state["airport"]

    bbox = compute_airport_bbox_from_opensky(airport)
    raw_states = fetch_opensky_states()

    found_flights: List[Dict] = []

    for s in raw_states:
        try:
            # Map OpenSky state vector indices to a readable dict
            flight = {
                "icao24": s[0],
                "callsign": s[1].strip() if s[1] else "UNKNOWN",
                "lon": s[5],
                "lat": s[6],
                "baro_altitude": s[7],
                "velocity": s[9],       # m/s from OpenSky
            }

            if is_departure_candidate(flight, bbox):
                # Convert velocity from m/s to knots for heuristic use
                speed_kt = (flight["velocity"] or 0) * 1.94384
                flight["speed_kt"] = round(speed_kt, 1)
                flight["window"] = estimate_departure_window(speed_kt)
                found_flights.append(flight)

        except Exception as e:
            # Skip malformed state vectors silently
            continue

    print(f"Found {len(found_flights)} candidates.")
    return {"flights": found_flights}

# ------------------------------------------------------------
# Node 2: Fetch airport weather
# ------------------------------------------------------------
def fetch_weather(state: FlightState) -> Dict:
    """
    Node 2: Retrieve current METAR and TAF weather data for the airport
    by calling the local MCP weather server over JSON-RPC.
    """
    print(f"--- FETCHING WEATHER FOR: {state['airport']} ---")
    airport = state["airport"]
    weather_data = fetch_weather_via_mcp(airport)
    return {"weather": weather_data}

# ------------------------------------------------------------
# Node 3: Estimate delay probability with LLM
# ------------------------------------------------------------
def estimate_delays(state: FlightState) -> Dict:
    """
    Node 3: For each departure candidate, send flight params + weather
    to the LLM and collect a structured delay risk assessment.
    """
    print("--- ESTIMATING DELAYS ---")
    results = []
    weather = state.get("weather", {})
    flights = state.get("flights", [])

    for flight in flights:
        # assess_delay returns { delay_probability, primary_factors, risk_level }
        assessment = assess_delay(flight, weather)
        results.append({
            "callsign": flight["callsign"],
            "departure_window": flight["window"],
            "assessment": assessment,
        })

    return {"results": results}

# ------------------------------------------------------------
# LangGraph assembly — wire the 3 nodes into a linear pipeline
# detect_departures -> get_weather -> estimate_delays
# ------------------------------------------------------------
builder = StateGraph(FlightState)

builder.add_node("detect_departures", detect_departure_candidates)
builder.add_node("get_weather", fetch_weather)
builder.add_node("estimate_delays", estimate_delays)

builder.set_entry_point("detect_departures")
builder.add_edge("detect_departures", "get_weather")
builder.add_edge("get_weather", "estimate_delays")
builder.set_finish_point("estimate_delays")

# Compiled graph — imported by app.py as the main entry point
app = builder.compile()