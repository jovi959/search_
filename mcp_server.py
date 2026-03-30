#!/usr/bin/env python3
"""
MCP server for the web search agent.

Exposes a single `web_research` tool over Streamable HTTP.
Any MCP client (Claude Desktop, Cursor, etc.) can connect and
ask questions that get researched via real Google search.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
from openai import OpenAI
from seleniumbase import Driver

from agent import run
from dispatch import build_dispatch

_executor = ThreadPoolExecutor(max_workers=1)

PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "websearch-agent.txt"


@lifespan
async def browser_lifespan(server):
    """Create a UC browser on startup, tear it down on shutdown."""
    headless = os.environ.get("HEADLESS", "true").lower() == "true"
    driver = Driver(uc=True, headless=headless, page_load_strategy="eager")
    try:
        yield {"driver": driver}
    finally:
        driver.quit()


mcp = FastMCP(
    "Web Search Agent",
    lifespan=browser_lifespan,
    instructions=(
        "This server provides a web_research tool that searches Google "
        "and reads pages to answer questions. Pass a clear question and "
        "get back a researched answer with sources."
    ),
)


@mcp.tool()
async def web_research(question: str, ctx: Context) -> str:
    """
    Search the web and return a researched answer to the question.

    Uses a local LLM agent that searches Google, reads the best pages,
    and synthesises the findings into a concise answer with sources.
    This may take 30-90 seconds depending on the query.
    """
    driver = ctx.lifespan_context["driver"]

    client = OpenAI(
        base_url=os.environ.get("LM_STUDIO_BASE_URL", "http://192.168.2.11:1234/v1"),
        api_key=os.environ.get("LM_STUDIO_API_KEY", "lm-studio"),
    )
    model = os.environ.get("AGENT_MODEL", "locooperator-4b@q8_0")

    prompt_template = PROMPT_FILE.read_text(encoding="utf-8")
    prompt = prompt_template.replace("{{input}}", question)

    dispatch = build_dispatch(driver)

    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(
        _executor, lambda: run(prompt, client, model, dispatch)
    )

    step = 0
    while not future.done():
        await asyncio.sleep(1)
        step += 1
        try:
            await ctx.report_progress(progress=step, total=step + 5)
        except Exception:
            pass

    result = future.result()

    answer = result.get("answer", "No answer produced.")
    sources = result.get("sources", [])

    if sources:
        source_lines = "\n".join(
            f"  - {s.get('url', s)}" for s in sources
        )
        return f"{answer}\n\nSources:\n{source_lines}"

    return answer


if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    print(f"[*] Starting MCP server on {host}:{port}")
    print(f"[*] Endpoint: http://{host}:{port}/mcp/")
    mcp.run(transport="streamable-http", host=host, port=port)
