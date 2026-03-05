#!/usr/bin/env python3
"""
CLI entry point for the web search agent.

Spins up a SeleniumBase UC browser, wires the real tool implementations
into a dispatch function, and runs the agent loop.
"""

import io
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from openai import OpenAI
from seleniumbase import Driver

from agent import run
from dispatch import build_dispatch

PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "websearch-agent.txt"


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

    driver = Driver(uc=True, headless=headless, page_load_strategy="eager")
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
