#!/usr/bin/env python3
"""
Promptfoo exec provider for the web search agent.

Called by Promptfoo as:
  python providers/websearch_agent.py <prompt> <provider_config> <test_context>

Uses the tester LLM to reason over tools, intercepts tool calls with mock
fixture data from the test context, and returns structured JSON to stdout.
"""

import sys
import json
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from tools.registry import get_openai_tools

MAX_TOOL_ROUNDS = 5
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")


class MockQueue:
    """
    FIFO queue of mock responses per tool.  Each entry is either:
      - a string  -> load from fixtures/{subdir}/{name}.json
      - anything else (dict / list) -> use directly as inline data
    Last entry repeats when the queue is exhausted.
    """

    def __init__(self, entries, fixtures_subdir: str):
        if isinstance(entries, str):
            entries = [entries]
        elif not isinstance(entries, list):
            entries = [entries]
        self._queue = entries
        self._subdir = fixtures_subdir
        self._index = 0

    def next(self):
        entry = self._queue[min(self._index, len(self._queue) - 1)]
        self._index += 1
        if isinstance(entry, str):
            path = os.path.join(FIXTURES_DIR, self._subdir, f"{entry}.json")
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return entry


TOOL_FIXTURE_SUBDIRS = {
    "search_google": "search",
    "navigate_and_summarize": "navigate",
}


def build_mock_dispatch(fixtures_map: dict):
    """Build a dict of tool_name -> callable that returns mock data."""
    queues = {}
    for tool_name, subdir in TOOL_FIXTURE_SUBDIRS.items():
        entries = fixtures_map.get(tool_name, [])
        if entries:
            queues[tool_name] = MockQueue(entries, subdir)

    def dispatch(tool_name: str, args: dict):
        if tool_name in queues:
            data = queues[tool_name].next()
            if isinstance(data, dict) and tool_name == "navigate_and_summarize" and "link" not in data:
                data["link"] = args.get("link", "")
            return data
        return {"error": f"No fixture configured for tool: {tool_name}"}

    return dispatch


def run_agent(prompt: str, config: dict, context: dict) -> dict:
    tester_cfg = config.get("tester", {})
    client = OpenAI(
        base_url=tester_cfg.get("base_url", "http://192.168.2.11:1234/v1"),
        api_key=tester_cfg.get("api_key", "lm-studio"),
    )
    model = tester_cfg.get("model", "qwen/qwen3.5-9b")

    vars_ = context.get("vars", {})
    fixtures_map = vars_.get("fixtures", {})

    mock = build_mock_dispatch(fixtures_map)
    tools = get_openai_tools()

    messages = [{"role": "user", "content": prompt}]
    all_steps = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools if tools else None,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or (
            choice.message.tool_calls and len(choice.message.tool_calls) > 0
        ):
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                all_steps.append({"tool": fn_name, "input": fn_args})

                result = mock(fn_name, fn_args)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )
        else:
            raw = choice.message.content or ""
            return _parse_final_response(raw, all_steps)

    last_content = messages[-1].get("content", "") if isinstance(messages[-1], dict) else ""
    return _parse_final_response(last_content, all_steps)


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks that some models emit."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()


def _extract_json(text: str) -> str:
    """Pull the first JSON object or array out of text that may have markdown fences."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if m:
        return m.group(1).strip()
    return text


def _parse_final_response(raw: str, steps: list) -> dict:
    """Try to parse the LLM's final output as JSON, or wrap it."""
    cleaned = _strip_thinking(raw)
    json_str = _extract_json(cleaned)
    try:
        obj = json.loads(json_str)
        if isinstance(obj, dict):
            if "steps" not in obj:
                obj["steps"] = steps
            return obj
    except (json.JSONDecodeError, TypeError):
        pass
    return {
        "answer": cleaned,
        "sources": [],
        "steps": steps,
    }


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    config = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    context = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

    result = run_agent(prompt, config, context)
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
