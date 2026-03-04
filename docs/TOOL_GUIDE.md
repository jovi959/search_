# Tool Building Guide

How to add and configure tools for the web search agent.

## Overview

Each tool is defined by a JSON file in `tools/` using the OpenAI function-calling format (e.g. `tools/search_google.json`). The `tools/registry.py` module loads all `*.json` files at import time and exposes them to the agent.

For real execution, each tool also has a Python implementation file (e.g. `tools/search_google.py`) that accepts a SeleniumBase driver and returns structured results.

The agent loop in `agent.py` doesn't know or care whether tools are real or mocked — it receives a `dispatch` callable and uses it for every tool call.

## Current Tools

| Tool               | Definition                    | Implementation                | Purpose                     |
|--------------------|-------------------------------|-------------------------------|-----------------------------|
| `search_google`    | `tools/search_google.json`    | `tools/search_google.py`      | Google search via UC mode   |
| `get_page_content` | `tools/get_page_content.json` | `tools/get_page_content.py`   | Fetch and clean page text   |

## Step-by-Step: Adding a New Tool

### 1. Create the tool definition JSON

Add a new file in `tools/`, e.g. `tools/your_tool.json`:

```json
{
  "type": "function",
  "function": {
    "name": "your_tool_name",
    "description": "What this tool does and what it returns.",
    "parameters": {
      "type": "object",
      "properties": {
        "param_name": {
          "type": "string",
          "description": "What this parameter is for."
        }
      },
      "required": ["param_name"]
    }
  }
}
```

The registry picks it up automatically — no code changes needed.

### 2. Create the real implementation

Add `tools/your_tool.py`:

```python
def your_tool_name(driver, param_name: str) -> dict:
    """Use the SeleniumBase driver to do something and return results."""
    # ... browser automation logic ...
    return {"result_field": "value"}
```

Then register it in `main.py`'s `build_dispatch`:

```python
tool_map = {
    "search_google": lambda args: search_google(driver, args["query"]),
    "get_page_content": lambda args: get_page_content(driver, args["url"]),
    "your_tool_name": lambda args: your_tool_name(driver, args["param_name"]),
}
```

### 3. Add mock fixtures in your test YAML

Under `vars.fixtures`, add an entry matching your tool name. Each entry is a list of responses the mock dispatch returns sequentially:

```yaml
- description: test for new tool
  vars:
    input: "user question"
    fixtures:
      search_google:
        - - title: "Result 1"
            link: "https://example.com"
      your_tool_name:
        - field_a: "first call response"
        - field_a: "second call response"
```

If the agent calls `your_tool_name` twice, it gets the first fixture on call 1 and the second on call 2. Extra calls repeat the last fixture.

### 4. Add assertions in the test YAML

```yaml
  assert:
    - type: javascript
      metric: used_your_tool
      value: |
        const obj = JSON.parse(output);
        return obj.steps.some(s => s.tool === 'your_tool_name');
```

## Writing Good Tool Descriptions

The tool `description` field is the primary way you instruct the LLM on how and when to use a tool.

### Structure

```
One-line summary of what the tool does and returns.

### When to Use This Tool

Use `tool_name` when you need to:
- Scenario A
- Scenario B

### When NOT to Use

Skip `tool_name` when:
1. Alternative situation (use X instead)
2. Another situation to avoid

### Examples

<example>
  Input: "good input example"
<reasoning>
  Good: Explanation of why this is a good use.
</reasoning>
</example>

<example>
  Input: "bad input example"
<reasoning>
  BAD: Explanation of what's wrong and what to do instead.
</reasoning>
</example>

### Usage
- Behavioral instruction about processing results.
- Constraints or rules about using this tool.
```

### Key Principles

- **When to Use / When NOT to Use** prevents the LLM from calling the wrong tool
- **Examples with reasoning** teach by showing concrete good and bad patterns
- **Parameter descriptions** should include concrete examples of good inputs

### Trade-off: Description Length vs Model Size

Verbose descriptions with examples work well for larger models (9B+). For smaller models (4B and under), keep descriptions short — long descriptions eat context and can confuse the model.

## How the Tool System Works

### `tools/*.json`

Each JSON file defines one tool in OpenAI function-calling format. This is the single source of truth for that tool's schema.

### `tools/registry.py`

Loads all `*.json` files at import time and exposes:

- `ALL_TOOLS` — the raw list of tool defs
- `TOOL_DEFS_BY_NAME` — dict keyed by tool name for quick lookup
- `get_openai_tools()` — returns the list for `client.chat.completions.create(tools=...)`

### `tools/*.py` (real implementations)

Each tool's Python file exports a function that takes a SeleniumBase driver as the first argument. `main.py` wires these into the dispatch closure.

### Mock dispatch (testing)

In `providers/websearch_agent.py`, the mock dispatch reads from `context.vars.fixtures`:

```python
def dispatch(tool_name: str, args: dict):
    entries = fixtures.get(tool_name, [])
    idx = counters.get(tool_name, 0)
    counters[tool_name] = idx + 1
    return entries[min(idx, len(entries) - 1)]
```

No browser, no network — all mock data is inline in the test YAML.

### Agent loop (`agent.py`)

The agent receives a `dispatch` callable and uses it whenever the LLM makes a tool call. Same code for real and mock execution.
