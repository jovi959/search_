"""
Web search agent loop.

Takes an LLM client, tool definitions, and a dispatch function for executing
tool calls. Reusable in both testing (mock dispatch) and production
(real SeleniumBase dispatch).
"""

import json
import re

from openai import OpenAI
from tools.registry import get_openai_tools

MAX_TOOL_ROUNDS = 5

SYNTHESIS_NUDGE = (
    'Now write your final answer as a JSON object: '
    '{"answer": "your summary", "sources": [{"title": "...", "link": "..."}], '
    '"steps": [{"tool": "...", "input": "..."}]}. '
    'Summarize in your own words. Do NOT repeat the raw tool output.'
)


def run(prompt: str, client: OpenAI, model: str, dispatch) -> dict:
    """
    Run the agentic loop.

    Args:
        prompt:   The rendered prompt to send to the LLM.
        client:   OpenAI-compatible client.
        model:    Model identifier.
        dispatch: Callable(tool_name: str, args: dict) -> result.
                  Called whenever the LLM requests a tool execution.
    """
    tools = get_openai_tools()
    messages = [{"role": "user", "content": prompt}]
    all_steps = []

    for round_idx in range(MAX_TOOL_ROUNDS):
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

                result = dispatch(fn_name, fn_args)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

            messages.append({"role": "user", "content": SYNTHESIS_NUDGE})
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
    cleaned = _strip_thinking(raw)
    json_str = _extract_json(cleaned)
    try:
        obj = json.loads(json_str)
        if isinstance(obj, dict) and "answer" in obj:
            if "steps" not in obj:
                obj["steps"] = steps
            if "sources" not in obj:
                obj["sources"] = []
            return obj
    except (json.JSONDecodeError, TypeError):
        pass
    return {
        "answer": cleaned,
        "sources": [],
        "steps": steps,
    }
