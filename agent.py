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


def run(prompt: str, client: OpenAI, model: str, dispatch) -> dict:
    """
    Run the agentic loop.

    Args:
        prompt:   The rendered prompt to send to the LLM.
        client:   OpenAI-compatible client.
        model:    Model identifier.
        dispatch: Callable(tool_name: str, args: dict) -> result.
    """
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

                result = dispatch(fn_name, fn_args)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )
        else:
            raw = choice.message.content or ""
            return _build_result(raw, all_steps)

    last_content = messages[-1].get("content", "") if isinstance(messages[-1], dict) else ""
    return _build_result(last_content, all_steps)


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks that some models emit."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()


def _build_result(raw: str, steps: list) -> dict:
    """Wrap the model's plain-text answer with internally-tracked metadata."""
    answer = _strip_thinking(raw)
    sources = [
        {"url": s["input"].get("url", s["input"])}
        for s in steps
        if s["tool"] == "get_page_content"
    ]
    return {"answer": answer, "sources": sources, "steps": steps}
