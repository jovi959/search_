# Web Search Agent

A local web research agent powered by an LLM (via LM Studio) and SeleniumBase for real browser automation. Ask a question from the CLI or connect via the MCP server -- the agent searches the configured web engine, reads pages, and writes a summarised answer.

The project also includes a full [Promptfoo](https://www.promptfoo.dev/) test suite that validates agent behaviour using mock fixtures — no browser needed for tests.

Optional **browser and agent tuning** (`USER_AGENT`, `STEALTH_RECONNECT_TIME`, `TYPING_WPM`, `TOOL_CALL_DELAY`) is documented under [Configuration](#configuration)—see [Browser and agent tuning](#browser-and-agent-tuning).

## Changelog

Maintained by hand: commit messages and diffs are the source of truth here; **newest first** within each day.

### 2026-05-10

Summaries below are from `git show` on local `main`. Within this day, commits are listed **newest first** (see timestamps in `git log` if you need order).

#### `5acb12f` — add bing

| Area | What changed |
|------|----------------|
| **Bing (`tools/engines/bing.py`)** | Search box handling: `wait_for_element_present` on `#sb_form_q`, `textarea[name='q']`, `input[name='q']` (short timeout), then `human_type`; falls back to `https://www.bing.com/search?q=…` only if no box appears. |
| **Agent ([`agent.py`](../agent.py))** | Tracks successful vs failed `get_page_content` results. If **every** page read failed or returned empty text, the user-facing answer is replaced with a short notice that sources could not be read reliably (includes URLs when known). |
| **Round cap** | When the loop hits `MAX_TOOL_ROUNDS`, the code runs **one more** `chat.completions` call with a user message that forces a final answer from prior context—no further tool calls. |
| **Prompt ([`prompts/websearch-agent.txt`](../prompts/websearch-agent.txt))** | Instructs the model to read **at least two** result pages when multiple sources could disagree. |
| **Tests** | New [`tests/round-cap-summary.yaml`](../tests/round-cap-summary.yaml) (search + four page reads uses the full round budget; asserts no raw `<page_content>` and a real summary). Listed in [`promptfooconfig.yaml`](../promptfooconfig.yaml). |

#### `0041274` — refactor to support multiple engines

| Area | What changed |
|------|----------------|
| **Split search** | Removed monolithic `tools/search_google.py` (no longer in tree). Shared stealth/typing → [`tools/_browser_utils.py`](../tools/_browser_utils.py). Google → [`tools/engines/google.py`](../tools/engines/google.py). Bing → [`tools/engines/bing.py`](../tools/engines/bing.py). |
| **Facade** | New [`tools/search.py`](../tools/search.py): reads `SEARCH_ENGINE`, dispatches to `google.search` or `bing.search`. Tool **name** stays `search_google` everywhere. |
| **Dispatch** | [`dispatch.py`](../dispatch.py) imports `from tools.search import search` and wires `"search_google": … search(driver, query)`. |
| **Config** | `SEARCH_ENGINE=google` \| `bing` in [`.env`](../.env). Comments for `STEALTH_RECONNECT_TIME` and `TYPING_WPM` refer to the generic “search box,” not Google only. |
| **Docs** | [`docs/README.md`](README.md) and [`docs/TOOL_GUIDE.md`](TOOL_GUIDE.md) updated for `SEARCH_ENGINE`. |

#### `ca558c6` — user agent + human typing (search box)

| Area | What changed |
|------|----------------|
| **`USER_AGENT`** | Optional Chrome user agent: [`main.py`](../main.py) and [`mcp_server.py`](../mcp_server.py) pass `agent=` into SeleniumBase `Driver` when set; empty = browser default (see the [Configuration](#configuration) table). |
| **`TYPING_WPM`** | Lived in search code first; now implemented as [`human_type()`](../tools/_browser_utils.py) in [`tools/_browser_utils.py`](../tools/_browser_utils.py). **`0`** = instant `type()` + submit. **`> 0`** = target typing speed (words/min, ~5 chars/word): character-by-character delays, **speed clusters** (bursts of 3–7 chars with per-cluster speed jitter up to 50% faster than base), **longer pauses between clusters**, and ~**5%** adjacent-key **typos** on letters + backspace correction (QWERTY neighbors). All engines that call `human_type` share this behaviour. |
| **Docs** | `USER_AGENT` / `TYPING_WPM` documented in this README’s `.env` example and table. |

#### `4e2ca91` — stealth reconnect

| Area | What changed |
|------|----------------|
| **`STEALTH_RECONNECT_TIME`** | Seconds to keep CDP “reconnect” mode during navigations when using UC stealth open. **`0`** = plain `driver.get()`. **`> 0`** = `uc_open_with_reconnect(..., reconnect_time=…)` when available (see [`stealth_open()`](../tools/_browser_utils.py)). Used for search **and** other code paths that call `stealth_open`. |

#### `e9d9579` — pause between tool calls

| Area | What changed |
|------|----------------|
| **`TOOL_CALL_DELAY`** | Seconds to sleep in [`agent.py`](../agent.py) after each tool dispatch before wrapping the result for the model (`0` = no pause). |

#### This doc + follow-ups (working tree)

| Item | Status |
|------|--------|
| **Changelog** | This section (edits in `docs/README.md` may be uncommitted). |
| **Brave engine** | [`tools/engines/brave.py`](../tools/engines/brave.py) + [`tools/engines/README.md`](../tools/engines/README.md) added locally, and [`tools/search.py`](../tools/search.py) registers `"brave": brave.search`. Use `SEARCH_ENGINE=brave` to select it. |

### 2026-03-30

| Commit | What changed |
|--------|----------------|
| **`fc17c1a` — blocklist** | [`blocklist.json`](../blocklist.json) + [`tools/blocklist.py`](../tools/blocklist.py): hostname / URL patterns; [`get_page_content`](../tools/get_page_content.py) returns an error without visiting blocked URLs. Details in [`BLOCKLIST.md`](BLOCKLIST.md). |
| **`f639994` — eager loads** | SeleniumBase `Driver` uses `page_load_strategy: "eager"` ([`mcp_server.py`](../mcp_server.py), [`main.py`](../main.py)) so navigation returns before every subresource finishes. This commit added it on the MCP server path. |

### 2026-03-05

| Commit | What changed |
|--------|----------------|
| **`5f7befe` — MCP + dispatch** | Streamable HTTP MCP server and shared [`dispatch.py`](../dispatch.py) wiring for CLI and server (baseline for the architecture described in this doc). |

### Earlier

| Area | What |
|------|------|
| Tests | Promptfoo (`npm test`), mock fixtures, no live browser |
| CLI | [`main.py`](../main.py) — one-shot questions |

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
│   ├── search.py                 # Configurable search facade
│   ├── _browser_utils.py         # Shared browser/typing helpers
│   ├── engines/                  # Per-engine search implementations (google, bing, brave)
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
USER_AGENT=
SEARCH_ENGINE=google
MCP_HOST=0.0.0.0
MCP_PORT=8000
TOOL_CALL_DELAY=0
STEALTH_RECONNECT_TIME=0
TYPING_WPM=0
```

| Variable                 | Purpose                                                                                                                            |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `LM_STUDIO_BASE_URL`     | OpenAI-compatible API endpoint                                                                                                     |
| `LM_STUDIO_API_KEY`      | API key (LM Studio default: `lm-studio`)                                                                                           |
| `AGENT_MODEL`            | Model the agent uses for reasoning/tool calls                                                                                      |
| `GRADER_MODEL`           | Model Promptfoo uses to grade LLM rubrics                                                                                          |
| `HEADLESS`               | `true` = no browser window, `false` = visible                                                                                      |
| `USER_AGENT`             | Custom Chrome user agent passed to SeleniumBase (`Driver(agent=…)`). Empty = browser default. See [below](#browser-and-agent-tuning). |
| `SEARCH_ENGINE`          | Which engine the `search_google` tool actually uses under the hood. `google` (default), `bing`, or `brave`. See [tools/engines/README.md](../tools/engines/README.md) to add more. |
| `MCP_HOST`               | MCP server bind address (default `0.0.0.0`)                                                                                        |
| `MCP_PORT`               | MCP server port (default `8000`)                                                                                                   |
| `TOOL_CALL_DELAY`        | Seconds to sleep **after each tool runs** (search or page read), before the result is sent back to the LLM. `0` = no pause. See [below](#browser-and-agent-tuning). |
| `STEALTH_RECONNECT_TIME` | UC-mode navigation: `0` = normal `driver.get()`. `> 0` = `uc_open_with_reconnect` with that many seconds of reconnect-style behaviour for URLs opened via [`stealth_open()`](../tools/_browser_utils.py) (search navigation and any other caller). See [below](#browser-and-agent-tuning). |
| `TYPING_WPM`             | How the **search box query** is typed: `0` = instant submit. `> 0` = simulated human typing at that WPM (clusters, pauses, occasional typo+correct). Implemented in [`human_type()`](../tools/_browser_utils.py). See [below](#browser-and-agent-tuning). |

### Browser and agent tuning

These settings matter for **CLI and MCP** runs (not Promptfoo mocks). They are read from `.env` via [`main.py`](../main.py), [`mcp_server.py`](../mcp_server.py), [`agent.py`](../agent.py), and [`tools/_browser_utils.py`](../tools/_browser_utils.py).

| Variable | Layer | What it does |
|----------|--------|----------------|
| `TOOL_CALL_DELAY` | **Agent** ([`agent.py`](../agent.py)) | After each tool call completes, sleep this many seconds before adding the tool result to the conversation. Use `0` for fastest iteration; raise it if the LM or site rate-limits when many tools run in a row. |
| `STEALTH_RECONNECT_TIME` | **Browser / UC** ([`stealth_open()`](../tools/_browser_utils.py)) | **`0`:** load URLs with a normal `get()`. **`> 0`:** use SeleniumBase’s `uc_open_with_reconnect` with that reconnect duration when available. Affects navigations that go through `stealth_open` (including opening the search engine before typing the query). |
| `TYPING_WPM` | **Search UI** ([`human_type()`](../tools/_browser_utils.py)) | **`0`:** type the whole query at once and submit. **`> 0`:** type at the given words-per-minute (~5 characters per word), with variable burst lengths, pauses between bursts, and rare QWERTY-adjacent mistypes plus backspace. Applied when an engine types into the search field (Google, Bing, etc.). |
| `USER_AGENT` | **Browser** ([`main.py`](../main.py), [`mcp_server.py`](../mcp_server.py)) | If non-empty, SeleniumBase starts Chrome with that user-agent string. Leave empty to use the default Chrome UA. |

## Usage

```bash
# Ask a question
python main.py "What is the latest news in Jamaica?"

# Watch the browser (set HEADLESS=false in .env)
python main.py "Who is the current PM of Jamaica?"
```

The agent will:
1. Search using the configured engine (Google by default)
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
| `web_research`  | `question` (string)  | Searches the web, reads pages, returns a researched answer     |

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

**Agent Loop** -- `agent.py` sends the prompt + tool definitions to the LLM. When the LLM makes a tool call, the agent dispatches it and feeds the result back. After each tool returns, an optional **`TOOL_CALL_DELAY`** sleep runs before the result is wrapped for the model. This repeats up to 5 rounds until the LLM produces a final text answer. The agent takes a generic `dispatch` callable -- it doesn't know whether tools are real or mocked.

**MCP Server** -- `mcp_server.py` runs a FastMCP server that exposes a single `web_research` tool over Streamable HTTP. On startup it launches a Chrome browser via SeleniumBase UC mode. Each tool call runs the full agent loop internally and returns the researched answer.

**CLI** -- `main.py` does the same thing as the MCP server but as a one-shot command-line tool.

**Mock Tools (Tests)** -- `providers/websearch_agent.py` serves fixture data from test YAMLs. No browser, no network -- tests are deterministic and fast.

**Shared Dispatch** -- `dispatch.py` wires the real SeleniumBase tool implementations into the agent loop. Both `main.py` and `mcp_server.py` import from it.
