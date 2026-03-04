# Tool Building Guide

How to add and configure tools for the web search agent.

## Overview

Tools are defined once in `tools/definitions.json` using the OpenAI function-calling format. Both Python (via `tools/registry.py`) and Promptfoo tests read from this single file — no duplication across languages.

The agent loop in `agent.py` automatically picks up any tool in `definitions.json`. You just need to provide a dispatch implementation (mock for testing, real for production).

## Step-by-Step: Adding a New Tool

### 1. Define the tool in `definitions.json`

Add a new entry to the JSON array:

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

### 2. Add mock fixtures in your test YAML

Under `vars.fixtures`, add an entry matching your tool name. Each entry is a list of responses the mock dispatch will return sequentially:

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
          field_b: 42
        - field_a: "second call response"
          field_b: 99
```

If the agent calls `your_tool_name` twice, it gets the first fixture on call 1 and the second on call 2. If it calls more times than there are fixtures, the last one repeats.

### 3. Add assertions in the test YAML

```yaml
  assert:
    - type: javascript
      metric: used_your_tool
      value: |
        const obj = JSON.parse(output);
        return obj.steps.some(s => s.tool === 'your_tool_name');
```

### 4. Wire up the real implementation (production)

When building the real dispatch (not mock), implement the actual tool logic and register it. The dispatch function signature is:

```python
def dispatch(tool_name: str, args: dict) -> dict:
    ...
```

It receives the tool name and arguments the LLM passed, and returns a dict that gets serialized back to the LLM as a tool result.

## Writing Good Tool Descriptions

The tool `description` field is the primary way you instruct the LLM on how and when to use a tool. A good description can be the difference between a working agent and a broken one.

### Structure

Follow this template for rich, structured descriptions:

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

- **When to Use / When NOT to Use** prevents the LLM from calling the wrong tool or calling it at the wrong time
- **Examples with reasoning** teach by showing concrete good and bad patterns
- **Reasoning tags** always start with `Good:` or `BAD:` for scannability
- **Usage section** tells the LLM what to do with the tool's output
- **Parameter descriptions** should include concrete examples of good inputs

### Trade-off: Description Length vs Model Size

Verbose descriptions with examples work well for larger models (9B+) that can process long contexts. For smaller models (4B and under), keep descriptions short and direct — long descriptions eat context and can confuse the model.

Current `definitions.json` uses short descriptions optimized for the 4B tester model. The full structured versions are documented in the plan file for reference and can be swapped in when using a larger model.

## How the Tool System Works

### `tools/definitions.json`

The single source of truth. An array of OpenAI function-calling tool definitions. Both Python and Node.js (Promptfoo) read from this file.

### `tools/registry.py`

Loads `definitions.json` at import time and exposes:

- `ALL_TOOLS` — the raw list of tool defs
- `TOOL_DEFS_BY_NAME` — dict keyed by tool name for quick lookup
- `get_openai_tools()` — returns the list for passing to `client.chat.completions.create(tools=...)`

### Mock dispatch (testing)

In `providers/websearch_agent.py`, the mock dispatch reads from `context.vars.fixtures`:

```python
def dispatch(tool_name: str, args: dict):
    entries = fixtures.get(tool_name, [])
    idx = counters.get(tool_name, 0)
    counters[tool_name] = idx + 1
    return entries[min(idx, len(entries) - 1)]
```

It serves fixture responses sequentially per tool. No file I/O — all mock data is inline in the test YAML and passed through by Promptfoo.

### Agent loop (`agent.py`)

The agent doesn't know or care whether tools are mocked. It receives a `dispatch` callable and uses it whenever the LLM makes a tool call. This makes the same agent code work for both testing and production.
