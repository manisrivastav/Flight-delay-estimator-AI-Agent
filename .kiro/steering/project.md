---
inclusion: always
---

# Airport Risk Monitor — Project Steering

## Overview

This is a real-time airport departure delay risk monitor. It combines live flight telemetry from the OpenSky Network, aviation weather data (METAR/TAF) via an MCP server, and LLM-based risk assessment to estimate departure delay probabilities for flights at a given airport.

The frontend is a Streamlit app. The backend pipeline is orchestrated with LangGraph.

## Architecture

The system follows a 3-node LangGraph pipeline:

1. `detect_departures` — Fetches global flight states from OpenSky, computes a bounding box around the target airport using `airportsdata`, and filters for ground-level departure candidates using speed/altitude heuristics.
2. `get_weather` — Calls a local MCP weather server (`http://127.0.0.1:3333/mcp`) to retrieve METAR and TAF data for the airport's ICAO code.
3. `estimate_delays` — Sends each candidate flight + weather data to an LLM (Hugging Face Qwen 2.5 7B) for structured delay risk assessment.

## Key Files

- `app.py` — Streamlit UI. Accepts IATA or ICAO codes, invokes the LangGraph pipeline, renders risk results.
- `graph.py` — LangGraph state machine definition. Wires the 3 nodes together.
- `opensky.py` — Fetches live global aircraft states from the OpenSky Network REST API.
- `airport_bbox.py` — Computes a geographic bounding box for an airport using `airportsdata` + live ground traffic from OpenSky. Caches results.
- `heuristics.py` — Pure functions for departure candidate filtering (`is_departure_candidate`) and departure window estimation. No external dependencies.
- `weather.py` — HTTP client that calls the local MCP weather server using JSON-RPC.
- `mcp_weather_server.py` — Deprecated. Original Python MCP server, no longer in use.
- `MCP-Node/` — Active Node.js MCP weather server. Exposes `get_aviation_weather` (METAR + TAF) over JSON-RPC at `http://127.0.0.1:3333/mcp`. Uses the `@modelcontextprotocol/sdk` with a stateless HTTP POST handler (no Express). Entry point: `MCP-Node/index.js`.
- `llm.py` — LLM integration for delay assessment. Currently uses Hugging Face Inference API with `Qwen/Qwen2.5-7B-Instruct`. Contains commented-out alternatives for Ollama (local) and Groq (cloud).
- `test.py` — Manual test script for the OpenSky departures API.

## Tech Stack

- Python 3.14
- LangGraph / LangChain for pipeline orchestration
- Streamlit for the web UI
- OpenSky Network API for live flight data
- Aviation Weather API (via MCP Node.js server) for METAR/TAF
- Node.js + `@modelcontextprotocol/sdk` for the MCP weather server
- Hugging Face Inference API (Qwen 2.5 7B) for LLM risk assessment
- `airportsdata` for ICAO airport lookups

## Environment

- Requires a `.env` file with `HUGGINGFACEHUB_API_TOKEN`
- The MCP weather server must be running on `http://127.0.0.1:3333` before starting the app
- Virtual environment: `python3.14 -m venv venv_3.14`
- Run: `streamlit run app.py`

## Conventions

- Airport codes: The app normalizes 3-letter IATA codes to ICAO by prepending "K" (US airports only). All internal logic uses ICAO codes.
- LLM output: The delay assessment returns structured JSON with `delay_probability` (float 0–1), `primary_factors` (string), and `risk_level` (Low/Moderate/High/Critical).
- Heuristics: A departure candidate is a flight within the airport bbox, below 500ft altitude, with ground speed between 5–40 knots.
- Error handling: The Streamlit UI catches `ValueError` (airport data issues) and generic exceptions separately, with debug tracebacks available in expanders.

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER (Browser)                                     │
│                                                                             │
│   Enters airport code (e.g. "SFO" or "KSFO")                               │
│                         │                                                   │
└─────────────────────────┼───────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        app.py (Streamlit UI)                                │
│                                                                             │
│   1. normalize_airport("SFO") ──► "KSFO"                                    │
│   2. app.invoke({"airport": "KSFO"})                                        │
│                         │                                                   │
│   3. Receives FlightState with results ──► Renders risk table               │
│      ┌──────────┬──────────────────┬──────────────────────┐                 │
│      │ Callsign │ Departure Window │ Risk % + Factors     │                 │
│      ├──────────┼──────────────────┼──────────────────────┤                 │
│      │ DAL123   │ 0–15 min         │ 🚨 65% - Low vis... │                 │
│      └──────────┴──────────────────┴──────────────────────┘                 │
└─────────────────────────┼───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     graph.py (LangGraph Pipeline)                           │
│                                                                             │
│   FlightState = { airport, flights, weather, results }                      │
│                                                                             │
│   ┌──────────────────────┐                                                  │
│   │  ENTRY POINT         │                                                  │
│   └──────────┬───────────┘                                                  │
│              ▼                                                              │
│   ┌──────────────────────────────────────────────────────────┐              │
│   │  Node 1: detect_departures                               │              │
│   │                                                          │              │
│   │  airport_bbox.py                    opensky.py           │              │
│   │  ┌─────────────────────┐   ┌──────────────────────┐     │              │
│   │  │ compute_airport_bbox│   │ fetch_opensky_states  │     │              │
│   │  │ _from_opensky()     │   │ GET /api/states/all   │     │              │
│   │  │                     │   └──────────┬───────────┘     │              │
│   │  │ ┌─────────────────┐ │              │                  │              │
│   │  │ │ airportsdata DB │ │              │ raw states[]     │              │
│   │  │ │ (ICAO lookup)   │ │              │                  │              │
│   │  │ └─────────────────┘ │              │                  │              │
│   │  └──────────┬──────────┘              │                  │              │
│   │             │ bbox                    │                  │              │
│   │             ▼                         ▼                  │              │
│   │        heuristics.py                                     │              │
│   │        ┌──────────────────────────────────┐              │              │
│   │        │ is_departure_candidate(flight,   │              │              │
│   │        │   bbox)                          │              │              │
│   │        │ • within_bbox(lat, lon, bbox)    │              │              │
│   │        │ • alt < 500ft                    │              │              │
│   │        │ • 5 <= speed_kt <= 40            │              │              │
│   │        ├──────────────────────────────────┤              │              │
│   │        │ estimate_departure_window(       │              │              │
│   │        │   speed_kt)                      │              │              │
│   │        │ • >=25kt → "0–15 min"            │              │              │
│   │        │ • >=15kt → "15–30 min"           │              │              │
│   │        │ • >=5kt  → "30–60 min"           │              │              │
│   │        │ • else   → ">60 min"             │              │              │
│   │        └──────────────────────────────────┘              │              │
│   │                                                          │              │
│   │  Output: { flights: [...candidates] }                    │              │
│   └──────────────────────────┬───────────────────────────────┘              │
│                              │                                              │
│                              ▼                                              │
│   ┌──────────────────────────────────────────────────────────┐              │
│   │  Node 2: get_weather                                     │              │
│   │                                                          │              │
│   │  weather.py                                              │              │
│   │  ┌──────────────────────────────┐                        │              │
│   │  │ fetch_weather_via_mcp(icao)  │                        │              │
│   │  │ POST http://127.0.0.1:3333   │                        │              │
│   │  │      /mcp                    │                        │              │
│   │  │ JSON-RPC: tools/call         │                        │              │
│   │  │  → get_aviation_weather      │                        │              │
│   │  └──────────────┬───────────────┘                        │              │
│   │                 │                                        │              │
│   │                 ▼                                        │              │
│   │  ┌──────────────────────────────────────┐                │              │
│   │  │ MCP-Node/index.js (Node.js server)   │                │              │
│   │  │                                      │                │              │
│   │  │ aviationweather.gov/api/data/metar ──┤                │              │
│   │  │ aviationweather.gov/api/data/taf   ──┤                │              │
│   │  │                                      │                │              │
│   │  │ Returns: { metar: {...}, taf: {...} } │                │              │
│   │  └──────────────────────────────────────┘                │              │
│   │                                                          │              │
│   │  Output: { weather: { metar, taf } }                     │              │
│   └──────────────────────────┬───────────────────────────────┘              │
│                              │                                              │
│                              ▼                                              │
│   ┌──────────────────────────────────────────────────────────┐              │
│   │  Node 3: estimate_delays                                 │              │
│   │                                                          │              │
│   │  For each flight in state.flights:                       │              │
│   │                                                          │              │
│   │  llm.py                                                  │              │
│   │  ┌──────────────────────────────────────┐                │              │
│   │  │ assess_delay(flight, weather)        │                │              │
│   │  │                                      │                │              │
│   │  │ Hugging Face Inference API           │                │              │
│   │  │ Model: Qwen/Qwen2.5-7B-Instruct     │                │              │
│   │  │                                      │                │              │
│   │  │ System: "You are an AOC analyst..."  │                │              │
│   │  │ User: flight params + raw weather    │                │              │
│   │  │                                      │                │              │
│   │  │ Returns JSON:                        │                │              │
│   │  │ {                                    │                │              │
│   │  │   delay_probability: 0.0–1.0,        │                │              │
│   │  │   primary_factors: "...",             │                │              │
│   │  │   risk_level: "Low|Moderate|High|    │                │              │
│   │  │                 Critical"            │                │              │
│   │  │ }                                    │                │              │
│   │  └──────────────────────────────────────┘                │              │
│   │                                                          │              │
│   │  Output: { results: [{ callsign, departure_window,      │              │
│   │                        assessment }] }                   │              │
│   └──────────────────────────┬───────────────────────────────┘              │
│                              │                                              │
│   ┌──────────────────────┐   │                                              │
│   │  FINISH POINT        │◄──┘                                              │
│   └──────────────────────┘                                                  │
│                                                                             │
│   Returns complete FlightState to app.py                                    │
└─────────────────────────────────────────────────────────────────────────────┘

External Services:
  ┌────────────────────────┐  ┌────────────────────────┐  ┌──────────────────┐
  │ OpenSky Network API    │  │ aviationweather.gov    │  │ Hugging Face     │
  │ (live flight states)   │  │ (METAR + TAF)          │  │ Inference API    │
  └────────────────────────┘  └────────────────────────┘  └──────────────────┘
```

## Guidelines for Changes

- Keep `heuristics.py` free of external API calls — it should remain pure logic for testability.
- When adding new LLM providers, follow the pattern in `llm.py`: return a dict matching the `DelayAssessment` schema.
- The OpenSky API is unauthenticated and rate-limited. Avoid adding unnecessary calls.
- The bounding box cache in `airport_bbox.py` is in-memory only. It resets on restart.
- Any new dependencies must be added to `requirements.txt`.
