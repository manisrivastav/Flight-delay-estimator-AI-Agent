import http from "http";
import fetch from "node-fetch";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";

/**
 * Initialize the base MCP Server instance.
 * We use the low-level Server class (not McpServer) for full control
 * over request handling without the higher-level abstractions.
 */
const server = new Server(
  {
    name: "aviation-weather",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Fetch METAR and TAF weather data from aviationweather.gov.
 *
 * @param {string} icao - ICAO airport code (e.g. "KATL", "KJFK")
 * @returns {object} MCP-formatted content response with weather JSON
 */
const getAviationWeather = async (icao) => {
  const code = icao.toUpperCase();
  console.log(`[MCP] Fetching for: ${code}`);

  // Fetch METAR (current conditions) and TAF (forecast) in parallel
  const [metarRes, tafRes] = await Promise.all([
    fetch(`https://aviationweather.gov/api/data/metar?ids=${code}&format=json`),
    fetch(`https://aviationweather.gov/api/data/taf?ids=${code}&format=json`)
  ]);
  const metar = await metarRes.json();
  const taf = await tafRes.json();

  // Return in MCP content format (array of content blocks)
  return {
    content: [{
      type: "text",
      text: JSON.stringify({ icao: code, metar: metar[0] || "N/A", taf: taf[0] || "N/A" }, null, 2),
    }],
  };
};

/**
 * Stateless HTTP server — handles JSON-RPC POST requests at /mcp.
 *
 * Supports two MCP methods:
 *   - tools/list: Returns the list of available tools and their schemas.
 *   - tools/call: Executes a tool by name with the provided arguments.
 *
 * No session state, no Express — just a plain Node.js http server.
 */
const httpServer = http.createServer((req, res) => {
  // Only accept POST requests to /mcp
  if (req.method === 'POST' && req.url === '/mcp') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const request = JSON.parse(body);

        // --- tools/list: Advertise available tools to the client ---
        if (request.method === "tools/list") {
          const response = {
            jsonrpc: "2.0",
            id: request.id,
            result: {
              tools: [
                {
                  name: "get_aviation_weather",
                  description: "Get METAR and TAF weather for an ICAO airport code",
                  inputSchema: {
                    type: "object",
                    properties: { icao: { type: "string" } },
                    required: ["icao"],
                  },
                },
              ],
            },
          };
          res.writeHead(200, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify(response));
        }

        // --- tools/call: Execute the requested tool ---
        if (request.method === "tools/call") {
          const { name, arguments: args } = request.params;

          if (name === "get_aviation_weather") {
            const result = await getAviationWeather(args.icao);
            const response = {
              jsonrpc: "2.0",
              id: request.id,
              result: result,
            };
            res.writeHead(200, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify(response));
          }
        }

        // Unknown method — return 404
        res.writeHead(404).end();
      } catch (err) {
        // Internal server error — return JSON-RPC error response
        console.error("[Server Error]", err.message);
        res.writeHead(500).end(JSON.stringify({
          jsonrpc: "2.0",
          error: { code: -32603, message: err.message },
          id: null
        }));
      }
    });
  } else {
    // Non-POST or wrong path — 404
    res.writeHead(404).end();
  }
});

// Start listening on port 3333 (localhost only)
httpServer.listen(3333, "127.0.0.1", () => {
  console.log("🚀 Manual MCP Server live at http://127.0.0.1:3333/mcp");
});
