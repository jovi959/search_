# Web Search Agent

A local web research agent powered by an LLM (via LM Studio) and SeleniumBase for real browser automation. Ask a question from the CLI or connect via the MCP server — the agent searches Google, reads pages, and writes a summarised answer.

The project also includes a full [Promptfoo](https://www.promptfoo.dev/) test suite that validates agent behaviour using mock fixtures — no browser needed for tests.

## Project Structure

```
web_search_mcp/
├── main.py                       # CLI entry point
├── mcp_server.py                 # MCP server (Streamable HTTP)
├── agent.py                      # Core agentic loop (prompt → tool calls → answer)
├── dispatch.py                   # Shared dispatch builder (used by CLI + MCP)
├── .env                          # Config: model, API URL, HEADLESS, MCP port
├── prompts/
│   ├── websearch-agent.txt       # Agent system prompt (uses {{input}})
│   └── loader.py                 # Loads and renders prompt templates
├── tools/
│   ├── search_google.json        # Tool definition (OpenAI function-calling format)
│   ├── search_google.py          # Real Google search via SeleniumBase UC mode
│   ├── get_page_content.json     # Tool definition
│   ├── get_page_content.py       # Real page fetcher via SeleniumBase
│   └── registry.py               # Loads all *.json tool defs for Python
├── providers/
│   └── websearch_agent.py        # Promptfoo exec provider (mock dispatch for tests)
├── tests/                        # Promptfoo test cases (YAML with fixtures)
├── run-tests.js                  # Test runner wrapper (clean pass/fail output)
├── promptfooconfig.yaml          # Main Promptfoo eval config
├── promptfooconfig-debug.yaml    # Single-test config for iterating
├── setup.bat                     # One-click Windows setup
├── requirements.txt              # Python deps (openai, seleniumbase, fastmcp)
└── package.json                  # Node deps (promptfoo)
```

## Prerequisites

- **Python 3.10+**
- **Node.js** (for Promptfoo tests)
- **Google Chrome** (SeleniumBase drives it via UC mode)
- **LM Studio** running with an OpenAI-compatible API

## Setup

Run `setup.bat` for a guided install, or do it manually:

```bash
# Node dependencies (for tests)
npm install

# Python virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux
python -m pip install -r requirements.txt
```

## Configuration

All settings live in `.env`:

```
LM_STUDIO_BASE_URL=http://192.168.2.11:1234/v1
LM_STUDIO_API_KEY=lm-studio
AGENT_MODEL=locooperator-4b@q8_0
GRADER_MODEL=gemma-3-4b-it
HEADLESS=true
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

| Variable             | Purpose                                      |
|----------------------|----------------------------------------------|
| `LM_STUDIO_BASE_URL`| OpenAI-compatible API endpoint                |
| `LM_STUDIO_API_KEY`  | API key (LM Studio default: `lm-studio`)     |
| `AGENT_MODEL`        | Model the agent uses for reasoning/tool calls |
| `GRADER_MODEL`       | Model Promptfoo uses to grade LLM rubrics     |
| `HEADLESS`           | `true` = no browser window, `false` = visible |
| `MCP_HOST`           | MCP server bind address (default `0.0.0.0`)  |
| `MCP_PORT`           | MCP server port (default `8000`)              |

## Usage

```bash
# Ask a question
python main.py "What is the latest news in Jamaica?"

# Watch the browser (set HEADLESS=false in .env)
python main.py "Who is the current PM of Jamaica?"
```

The agent will:
1. Search Google using SeleniumBase UC mode (stealth)
2. Read the best result pages
3. Summarise the findings into a clear answer
4. Print the answer, sources, and tool call steps

## MCP Server

The agent is also available as an MCP server, exposing a single `web_research` tool over [Streamable HTTP](https://spec.modelcontextprotocol.io/specification/basic/transports/#streamable-http). Any MCP-compatible client can connect and use it.

### Starting the Server

```bash
python mcp_server.py
```

The server starts on `http://0.0.0.0:8000/mcp/` by default (configurable via `MCP_HOST` and `MCP_PORT` in `.env`). A Chrome browser launches in the background (or visible if `HEADLESS=false`) and stays alive for all requests.

### Exposed Tool

| Tool            | Parameters           | Description                                                    |
|-----------------|----------------------|----------------------------------------------------------------|
| `web_research`  | `question` (string)  | Searches Google, reads pages, returns a researched answer      |

### Adding to Claude Desktop

Edit your Claude Desktop config file:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the server under `mcpServers`:

```json
{
  "mcpServers": {
    "web-search": {
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

Restart Claude Desktop. The `web_research` tool will appear in Claude's tool list.

### Adding to Cursor

Open Cursor Settings > MCP and add a new server:

- **Type:** `http`
- **URL:** `http://localhost:8000/mcp/`

The `web_research` tool will be available to Cursor's agent.

### Adding to Any MCP Client (Python)

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8000/mcp/") as client:
        result = await client.call_tool(
            "web_research",
            {"question": "What is the latest news in Jamaica?"}
        )
        print(result.content[0].text)

asyncio.run(main())
```

### Network Access

The server binds to `0.0.0.0` by default, so other machines on your network can connect at `http://<your-ip>:8000/mcp/`. To restrict to localhost only, set `MCP_HOST=127.0.0.1` in `.env`.

## Running Tests

Tests use Promptfoo with mock fixtures — no browser, no real web requests.

```bash
# Run all tests (clean pass/fail summary)
npm test

# Run one specific test
npm test -- tests/factual-lookup.yaml

# Run multiple specific tests
npm test -- tests/factual-lookup.yaml tests/no-results.yaml

# View results in browser
npm run view
```

## How It Works

**Agent Loop** -- `agent.py` sends the prompt + tool definitions to the LLM. When the LLM makes a tool call, the agent dispatches it and feeds the result back. This repeats up to 5 rounds until the LLM produces a final text answer. The agent takes a generic `dispatch` callable -- it doesn't know whether tools are real or mocked.

**MCP Server** -- `mcp_server.py` runs a FastMCP server that exposes a single `web_research` tool over Streamable HTTP. On startup it launches a Chrome browser via SeleniumBase UC mode. Each tool call runs the full agent loop internally and returns the researched answer.

**CLI** -- `main.py` does the same thing as the MCP server but as a one-shot command-line tool.

**Mock Tools (Tests)** -- `providers/websearch_agent.py` serves fixture data from test YAMLs. No browser, no network -- tests are deterministic and fast.

**Shared Dispatch** -- `dispatch.py` wires the real SeleniumBase tool implementations into the agent loop. Both `main.py` and `mcp_server.py` import from it.
