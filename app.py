"""
app.py — Streamlit frontend for the Airport Risk Monitor.

Accepts an airport code (IATA or ICAO), invokes the LangGraph pipeline,
and renders a risk assessment table for each departure candidate.
"""

import streamlit as st
import json
from graph import app  # The compiled LangGraph pipeline

def normalize_airport(code: str) -> str:
    """
    Convert a 3-letter IATA code to a 4-letter ICAO code for US airports.
    e.g. "SFO" -> "KSFO". If already ICAO length, return as-is.
    """
    code = code.strip().upper()
    if not code:
        return ""
    # US IATA codes are 3 chars; prepend "K" to get ICAO
    if len(code) == 3:
        return "K" + code
    return code

def get_risk_style(probability):
    """
    Map a delay probability (0–1) to a color and emoji for display.
    <= 0.2 = green/✅, <= 0.4 = orange/⚠️, > 0.4 = red/🚨
    """
    try:
        prob = float(probability)
        if prob <= 0.2:
            return "green", "✅"
        elif prob <= 0.4:
            return "orange", "⚠️"
        else:
            return "red", "🚨"
    except (ValueError, TypeError):
        return "gray", "❓"

# --- Page Config ---
st.set_page_config(page_title="Airline weather Risk Monitor", layout="wide", page_icon="✈️")

st.title("✈️ Airport Risk Monitor")
st.markdown("Real-time ground traffic analysis and weather-based delay probability.")

# --- Input Section ---
airport_input = st.text_input("Enter airport code (e.g., SFO, ATL, or EGLL)", placeholder="KSFO")

if st.button("Analyze Departures", type="primary"):
    if not airport_input:
        st.warning("Please enter an airport code.")
    else:
        airport = normalize_airport(airport_input)
        
        with st.spinner(f"Requesting telemetry for {airport}..."):
            try:
                # 1. Fetch data from LangGraph
                result = app.invoke({"airport": airport})
                
                # 2. Extract flight list
                flight_results = result.get("results", [])

                if not flight_results:
                    st.info(f"No active departure candidates found at {airport} right now.")
                else:
                    st.subheader(f"Current Departure Assessment: {airport}")
                    
                    # Manual Table Header
                    h1, h2, h3 = st.columns([1, 1.2, 3])
                    h1.write("**Callsign**")
                    h2.write("**Departure Window**")
                    h3.write("**Risk Analysis & Factors**")
                    st.divider()

                    # 3. Loop through flights with Data Safety
                    for flight in flight_results:
                        col1, col2, col3 = st.columns([1, 1.2, 3])
                        
                        # --- Column 1 & 2 ---
                        col1.markdown(f"### `{flight.get('callsign', 'N/A')}`")
                        col2.write(f"**{flight.get('departure_window', 'N/A')}**")

                        # --- Column 3: Safe Assessment Parsing ---
                        with col3:
                            raw_assessment = flight.get("assessment", {})
                            
                            # Handle cases where assessment might be a JSON string
                            if isinstance(raw_assessment, str):
                                try:
                                    assessment_data = json.loads(raw_assessment)
                                except:
                                    assessment_data = {"delay_probability": 0, "primary_factors": [raw_assessment]}
                            else:
                                assessment_data = raw_assessment

                            # Extract probability and factors safely
                            prob = assessment_data.get("delay_probability", 0)
                            factors = assessment_data.get("primary_factors", [])
                            
                            color, icon = get_risk_style(prob)

                            # Display Visual Probability
                            st.markdown(f"{icon} **Risk Level: :{color}[{prob*100:.0f}%]**")
                            
                            # Display Factors as a list
                            if factors and isinstance(factors, list):
                                for factor in factors:
                                    st.markdown(f"- {factor}")
                            elif factors: # if it's a single string
                                st.markdown(f"- {factors}")
                            else:
                                st.caption("No specific delay factors identified.")
                        
                        st.divider()

                    # 4. Raw Data Expander
                    with st.expander("🌐 View Raw METAR / Weather Data"):
                        st.json(result.get("weather", {}))

            # --- Specific Error Handling ---
            except ValueError as ve:
                st.error("📡 **Airport Data Issue**")
                st.warning(f"{ve}")
                st.info("Check if the airport is currently active or if OpenSky has coverage there.")
            
            except Exception as e:
                st.error("🚨 **UI Rendering Error**")
                st.write("An unexpected format was received from the backend.")
                with st.expander("Debug Traceback"):
                    st.exception(e) # This shows exactly where the data parsing failed

