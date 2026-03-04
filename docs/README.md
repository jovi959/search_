# Web Search Agent

A local web research agent tested with [Promptfoo](https://www.promptfoo.dev/). The agent uses an LLM (via LM Studio) to search the web and summarize pages, with plans to integrate SeleniumBase for real browser automation.

## Project Structure

```
web_search_mcp/
├── agent.py                  # Core agentic loop (prompt in, answer out)
├── prompts/
│   ├── websearch-agent.txt   # Agent prompt template (uses {{input}})
│   └── loader.py             # Loads and renders prompt templates
├── tools/
│   ├── definitions.json      # Tool definitions (OpenAI function-calling format)
│   └── registry.py           # Loads definitions for Python consumption
├── providers/
│   └── websearch_agent.py    # Promptfoo exec provider (wires mock dispatch into agent)
├── tests/
│   ├── factual-lookup.yaml   # Can the agent answer a factual question?
│   ├── browse-and-summarize.yaml  # Does it read pages and summarize?
│   ├── injection-resistance.yaml  # Does it resist prompt injection?
│   └── no-results.yaml       # Does it handle empty results gracefully?
├── promptfooconfig.yaml      # Main Promptfoo eval config
├── promptfooconfig-debug.yaml # Single-test config for iterating
├── requirements.txt          # Python deps (openai)
└── package.json              # Node deps (promptfoo)
```

## Prerequisites

- **Node.js** (for Promptfoo)
- **Python 3.10+**
- **LM Studio** running locally with an OpenAI-compatible API

## Setup

```bash
# Node dependencies
npm install

# Python virtual environment
python -m venv .venv
.venv/Scripts/activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

## Configuration

Edit `promptfooconfig.yaml` to point at your LM Studio instance:

- **tester** model: the LLM that powers the agent (makes tool calls, writes answers)
- **defaultTest provider**: the LLM that grades `llm-rubric` assertions (judger)

Both default to `http://192.168.2.11:1234/v1`.

## Running Tests

```bash
# Run all tests
npm run eval

# Run with no cache
npx promptfoo eval --no-cache

# Run a single test for debugging
npx promptfoo eval --no-cache -c promptfooconfig-debug.yaml

# View results in browser
npm run view
```

## How It Works

### Agent Loop (`agent.py`)

1. Sends the rendered prompt to the LLM with tool definitions
2. If the LLM requests a tool call, dispatches it and feeds the result back
3. Repeats up to 5 rounds until the LLM produces a final text answer
4. Wraps the answer with internally-tracked steps and sources

### Testing with Promptfoo

Promptfoo calls `providers/websearch_agent.py` as an exec provider. Test YAMLs provide mock tool responses inline via `vars.fixtures`, so no real web requests are made during testing.

Each test case defines:
- **vars.input** — the user's question
- **vars.fixtures** — mock responses for each tool (sequential per tool)
- **assert** — JavaScript checks and LLM rubric grading

### Tool Definitions (`tools/definitions.json`)

A single JSON file defines all tools in OpenAI function-calling format. Both Python (`tools/registry.py`) and Promptfoo tests read from this file — no duplication.

### Prompts (`prompts/`)

Prompt templates live in `.txt` files with `{{variable}}` placeholders. The Python `prompts/loader.py` module renders them, making prompts reusable from any Python code.

## Adding a New Tool

1. Add the tool definition to `tools/definitions.json`
2. Add mock fixture data in your test YAML under `vars.fixtures.<tool_name>`
3. The agent loop will automatically pick it up via `get_openai_tools()`

## Adding a New Test

1. Create a new YAML file in `tests/`
2. Add it to the `tests:` list in `promptfooconfig.yaml`
3. Define `vars`, `fixtures`, and `assert` blocks
