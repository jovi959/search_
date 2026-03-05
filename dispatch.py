"""
Shared dispatch builder for the web search agent.

Used by both main.py (CLI) and mcp.py (MCP server) to wire
real SeleniumBase tools into the agent loop.
"""

from tools.search_google import search_google
from tools.get_page_content import get_page_content


def build_dispatch(driver):
    """Return a dispatch(tool_name, args) closure backed by real browser tools."""
    tool_map = {
        "search_google": lambda args: search_google(driver, args["query"]),
        "get_page_content": lambda args: get_page_content(driver, args["url"]),
    }

    def dispatch(tool_name: str, args: dict):
        fn = tool_map.get(tool_name)
        if fn is None:
            return {"error": f"Unknown tool: {tool_name}"}
        return fn(args)

    return dispatch
