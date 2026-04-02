"""
weather.py — HTTP client for the local MCP weather server.

Sends JSON-RPC requests to the Node.js MCP server running at
http://127.0.0.1:3333/mcp to retrieve METAR and TAF aviation weather data.
The MCP server must be running before this module is used.
"""

import httpx
import json

def fetch_weather_via_mcp(icao: str) -> dict:
    """
    Call the MCP weather server to get METAR + TAF for an airport.

    Args:
        icao: 4-letter ICAO airport code (e.g. "KSFO").

    Returns:
        dict with weather data from the MCP server's response.

    Raises:
        Exception on HTTP errors or MCP-level errors.
    """
    # Build a JSON-RPC 2.0 request to invoke the get_aviation_weather tool
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_aviation_weather",
            "arguments": {"icao": str(icao).strip().upper()}
        }
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "http://127.0.0.1:3333/mcp",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            data = response.json()

            if "error" in data:
                raise Exception(f"MCP Error: {data['error']}")

            return data.get("result", {})

    except Exception as e:
        print(f"Python Client Error: {e}")
        raise

if __name__ == "__main__":
    # Quick manual test — run this file directly to verify MCP connectivity
    print("KATL:", fetch_weather_via_mcp("KATL"))
    print("KJFK:", fetch_weather_via_mcp("KJFK"))