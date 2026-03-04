# Web Search Agent

A local web research agent powered by an LLM (via LM Studio) and SeleniumBase for real browser automation. Ask a question from the CLI and the agent searches Google, reads pages, and writes a summarised answer.

The project also includes a full [Promptfoo](https://www.promptfoo.dev/) test suite that validates agent behaviour using mock fixtures — no browser needed for tests.

## Project Structure

```
web_search_mcp/
├── main.py                       # CLI entry point (real browser dispatch)
├── agent.py                      # Core agentic loop (prompt → tool calls → answer)
├── .env                          # Config: model, API URL, HEADLESS flag
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
│   ├── factual-lookup.yaml
│   ├── browse-and-summarize.yaml
│   ├── multi-page-synthesis.yaml
│   ├── specific-fact-extraction.yaml
│   ├── jamaica-news.yaml
│   ├── noisy-page-content.yaml
│   ├── contradictory-sources.yaml
│   ├── single-search-result.yaml
│   ├── no-results.yaml
│   ├── retry-irrelevant.yaml
│   ├── all-pages-fail.yaml
│   ├── page-error-fallback.yaml
│   ├── page-injection.yaml
│   └── page-injection-tool-abuse.yaml
├── run-tests.js                  # Test runner wrapper (clean pass/fail output)
├── promptfooconfig.yaml          # Main Promptfoo eval config
├── promptfooconfig-debug.yaml    # Single-test config for iterating
├── setup.bat                     # One-click Windows setup
├── requirements.txt              # Python deps (openai, seleniumbase, bs4)
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
```

| Variable             | Purpose                                      |
|----------------------|----------------------------------------------|
| `LM_STUDIO_BASE_URL`| OpenAI-compatible API endpoint                |
| `LM_STUDIO_API_KEY`  | API key (LM Studio default: `lm-studio`)     |
| `AGENT_MODEL`        | Model the agent uses for reasoning/tool calls |
| `GRADER_MODEL`       | Model Promptfoo uses to grade LLM rubrics     |
| `HEADLESS`           | `true` = no browser window, `false` = visible |

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

### Agent Loop (`agent.py`)

1. Sends the rendered prompt to the LLM with tool definitions
2. If the LLM requests a tool call, dispatches it and feeds the result back
3. Repeats up to 5 rounds until the LLM produces a final text answer
4. Returns the answer with tracked steps and sources

The agent takes a generic `dispatch` callable — it doesn't know whether tools are real or mocked.

### Real Tools (CLI via `main.py`)

`main.py` creates a SeleniumBase UC browser and wires real tool implementations into the dispatch:

- **`tools/search_google.py`** — Navigates to Google, types the query, parses organic results (title, link, snippet)
- **`tools/get_page_content.py`** — Navigates to a URL, strips HTML noise, returns clean text

### Mock Tools (Tests via Promptfoo)

`providers/websearch_agent.py` serves fixture data from test YAMLs. Each test defines `vars.fixtures` with pre-recorded tool responses, so tests are deterministic and fast.

### Tool Definitions (`tools/*.json`)

Each tool has its own JSON file in OpenAI function-calling format. `tools/registry.py` loads all `*.json` files at import time and exposes them to the agent.
