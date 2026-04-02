> ⚠️ **DISCLAIMER: This project is for educational and demonstration purposes only. It is not production-grade software. Do not use it for real aviation operations, decision-making, or any safety-critical purpose.**

# ✈️ Airport Risk Monitor

Real-time airport departure delay risk monitor that combines live flight telemetry from the OpenSky Network, aviation weather data (METAR/TAF) via an MCP server, and LLM-based risk assessment to estimate departure delay probabilities.

Enter an airport code (IATA like `SFO` or ICAO like `KSFO`), and the system will identify ground-level departure candidates, pull current weather conditions, and use an LLM to produce a structured delay risk assessment for each flight.

## High-Level Overview

The app runs a 3-node LangGraph pipeline:

1. **Detect Departures** — Fetches global flight states from OpenSky, computes a bounding box around the target airport, and filters for ground-level departure candidates using speed/altitude heuristics.
2. **Get Weather** — Calls a local MCP weather server to retrieve METAR and TAF data for the airport.
3. **Estimate Delays** — Sends each candidate flight + weather data to an LLM for structured delay risk assessment (probability, factors, risk level).

The frontend is a Streamlit app. For the full architecture, flow diagrams, and conventions, see [`.kiro/steering/project.md`](.kiro/steering/project.md).

## Tech Stack

- Python 3.14 / Streamlit (frontend)
- LangGraph / LangChain (pipeline orchestration)
- OpenSky Network API (live flight data)
- Node.js MCP server (aviation weather via METAR/TAF)
- Hugging Face Inference API — Qwen 2.5 7B (LLM risk assessment)
- `airportsdata` (ICAO airport lookups)

---

## Installation

### 1. Clone the repository

```bash
git clone <[your-repo-url](https://github.com/manisrivastav/Flight-delay-estimator-AI-Agent.git)>
cd <Flight-delay-estimator-AI-Agent>
```

### 2. Python environment setup

**macOS (using venv with Python 3.14):**

```bash
python3.14 -m venv venv_3.14
source venv_3.14/bin/activate
python --version  # should show 3.14.x
```

**Windows:**

```powershell
python -m venv venv_3.14
.\venv_3.14\Scripts\Activate.ps1
python --version
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

After installing new packages, always re-activate the environment:

```bash
source ./venv_3.14/bin/activate   # macOS/Linux
.\venv_3.14\Scripts\Activate.ps1  # Windows
```

### 4. Node.js MCP server setup

In a separate terminal, navigate to the MCP-Node directory and install dependencies:

```bash
cd MCP-Node
npm install
```

Requires Node.js (v18+) installed on your system.

### 5. Create your `.env` file

Create a `.env` file in the project root with your API key:

```env
HUGGINGFACEHUB_API_TOKEN=your_huggingface_api_token_here
```

You can get a free token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

---

## LLM Provider Configuration

The project ships with three LLM provider options in `llm.py`. Only one should be active at a time.

### Hugging Face (default — enabled)

Uses `Qwen/Qwen2.5-7B-Instruct` via the Hugging Face Inference API. Requires `HUGGINGFACEHUB_API_TOKEN` in your `.env` file. This is the currently active provider.

### Groq (cloud — commented out)

Uses `llama-3.3-70b-versatile` via the Groq API. To enable:

1. Comment out the entire Hugging Face section at the bottom of `llm.py`.
2. Uncomment the Groq section (look for `# Use this with groq API key`).
3. Add your Groq key to `.env`:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

### Ollama (local — commented out)

Uses a local Ollama instance with the `mistral` model. To enable:

1. Comment out the active provider section in `llm.py`.
2. Uncomment the Ollama section at the top (look for `#ENABLED to use with Ollama in LOCAL`).
3. Make sure Ollama is running locally with the Mistral model pulled:
   ```bash
   ollama pull mistral
   ollama serve
   ```
   No API key needed for this option.

---

## Running the App

The app requires two processes running in separate terminals.

### Terminal 1 — Start the MCP Weather Server

```bash
cd MCP-Node
node index.js
```

This starts the aviation weather MCP server on `http://127.0.0.1:3333/mcp`. Keep this terminal open.

### Terminal 2 — Start the Streamlit App

```bash
source venv_3.14/bin/activate   # macOS/Linux
# or: .\venv_3.14\Scripts\Activate.ps1  # Windows

streamlit run app.py
```

The app will open in your browser. Enter an airport code (e.g. `SFO`, `ATL`, `EGLL`) and click "Analyze Departures".

---

## Note on Flight Data (OpenSky Network)

This project uses the [OpenSky Network](https://opensky-network.org/) API for live flight telemetry. OpenSky is a community-driven, crowdsourced platform — its coverage depends on volunteer-operated ADS-B receivers in each region. This means:

- Flight data may be incomplete for some airports, especially those in areas with limited receiver coverage.
- Not all flights will appear in the results. If no departure candidates are found, it may simply be a coverage gap rather than an absence of traffic.
- The API is unauthenticated and rate-limited, so excessive requests may be throttled.

For the most reliable results, try major airports in well-covered regions (e.g. `KSFO`, `KATL`, `EGLL`).

---

## Future Considerations

- **Flight delay history** — Incorporate historical delay data to give the LLM richer context and improve inference accuracy over time.
- **Real flight and weather data integration** — Replace or supplement crowdsourced sources with certified aviation data feeds for more complete and reliable coverage.
- **Pilot weather reports (PIREPs)** — Generate route-aware pilot reports based on weather conditions along the planned flight path, not just at the departure airport.
- **Gate and runway assignment optimization** — Use real-time delay predictions to suggest optimal gate reassignments and runway sequencing, reducing taxi time and ground congestion.
- **Passenger rebooking recommendations** — Proactively flag high-risk flights and suggest alternative connections or rebooking options before delays cascade across the network.

---

## Architecture Reference

For the full architecture, file descriptions, flow diagrams, heuristics, and development conventions, see:

📄 [`.kiro/steering/project.md`](.kiro/steering/project.md)
