"""
Web search agent loop.

Takes an LLM client, tool definitions, and a dispatch function for executing
tool calls. Reusable in both testing (mock dispatch) and production
(real SeleniumBase dispatch).
"""

import json
import os
import re
import time

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
    successful_page_reads = []
    failed_page_reads = []
    delay = float(os.environ.get("TOOL_CALL_DELAY", "0"))

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
                if fn_name == "get_page_content" and isinstance(result, dict):
                    if result.get("error") or not result.get("page_text"):
                        failed_page_reads.append(result)
                    else:
                        successful_page_reads.append(result)
                if delay > 0:
                    time.sleep(delay)
                content = _wrap_tool_result(fn_name, result)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content,
                    }
                )
        else:
            raw = choice.message.content or ""
            raw = _final_answer_or_failure_notice(
                raw,
                successful_page_reads,
                failed_page_reads,
            )
            return _build_result(raw, all_steps)

    final = client.chat.completions.create(
        model=model,
        messages=messages + [
            {
                "role": "user",
                "content": (
                    "You have used your tool budget. Based on what you have "
                    "already gathered, write the final answer in your own words "
                    "now. Do NOT call any more tools, do NOT echo raw tool "
                    "output, and do NOT include <page_content> tags. If every "
                    "page read failed or returned empty content, say that you "
                    "could not retrieve enough source content to answer reliably."
                ),
            }
        ],
    )
    final_text = final.choices[0].message.content or ""
    final_text = _final_answer_or_failure_notice(
        final_text,
        successful_page_reads,
        failed_page_reads,
    )
    return _build_result(final_text, all_steps)


def _wrap_tool_result(tool_name: str, result) -> str:
    """Wrap get_page_content results in <page_content> tags to mark untrusted data."""
    if tool_name == "get_page_content" and isinstance(result, dict):
        page_text = result.get("page_text") or ""
        url = result.get("url", "")
        error = result.get("error")
        if error:
            return json.dumps({"url": url, "error": error})
        return f"<page_content url=\"{url}\">\n{page_text}\n</page_content>"
    return json.dumps(result)


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks that some models emit."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()


def _final_answer_or_failure_notice(
    raw: str,
    successful_page_reads: list,
    failed_page_reads: list,
) -> str:
    """Avoid presenting unsupported answers when every page read failed."""
    if failed_page_reads and not successful_page_reads:
        attempted_urls = [
            result.get("url")
            for result in failed_page_reads
            if isinstance(result, dict) and result.get("url")
        ]
        if attempted_urls:
            urls = ", ".join(dict.fromkeys(attempted_urls))
            return (
                "I found possible search results, but I could not retrieve "
                f"readable page content from the pages I tried: {urls}. I cannot "
                "answer reliably from the sources available in this run."
            )
        return (
            "I found possible search results, but every page read failed or "
            "returned empty content. I cannot answer reliably from the sources "
            "available in this run."
        )
    return raw


def _build_result(raw: str, steps: list) -> dict:
    """Wrap the model's plain-text answer with internally-tracked metadata."""
    answer = _strip_thinking(raw)
    sources = [
        {"url": s["input"].get("url", s["input"])}
        for s in steps
        if s["tool"] == "get_page_content"
    ]
    return {"answer": answer, "sources": sources, "steps": steps}
