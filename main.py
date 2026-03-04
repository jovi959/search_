#!/usr/bin/env python3
"""
CLI entry point for the web search agent.

Spins up a SeleniumBase UC browser, wires the real tool implementations
into a dispatch function, and runs the agent loop.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from openai import OpenAI
from seleniumbase import Driver

from agent import run
from tools.search_google import search_google
from tools.get_page_content import get_page_content

PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "websearch-agent.txt"


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


def main():
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print("Usage: python main.py <your question>")
        print('  e.g. python main.py "What is SeleniumBase?"')
        sys.exit(1)

    headless = os.environ.get("HEADLESS", "true").lower() == "true"
    client = OpenAI(
        base_url=os.environ.get("LM_STUDIO_BASE_URL", "http://192.168.2.11:1234/v1"),
        api_key=os.environ.get("LM_STUDIO_API_KEY", "lm-studio"),
    )
    model = os.environ.get("AGENT_MODEL", "locooperator-4b@q8_0")

    prompt_template = PROMPT_FILE.read_text(encoding="utf-8")
    prompt = prompt_template.replace("{{input}}", question)

    print(f"[*] Question: {question}")
    print(f"[*] Model:    {model}")
    print(f"[*] Headless: {headless}")
    print()

    driver = Driver(uc=True, headless=headless)
    try:
        dispatch = build_dispatch(driver)
        result = run(prompt, client, model, dispatch)

        print("=" * 60)
        print("ANSWER:")
        print("=" * 60)
        print(result["answer"])
        print()

        if result.get("sources"):
            print("SOURCES:")
            for src in result["sources"]:
                url = src.get("url", src)
                print(f"  - {url}")
            print()

        if result.get("steps"):
            print(f"STEPS ({len(result['steps'])} tool calls):")
            for i, step in enumerate(result["steps"], 1):
                print(f"  {i}. {step['tool']}({step['input']})")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
