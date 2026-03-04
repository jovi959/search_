#!/usr/bin/env python3
"""
Promptfoo exec provider entry point.

Test YAML provides mock data inline via vars.fixtures.
This script just hands it back when the LLM requests a tool call.
"""

import sys
import json
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from openai import OpenAI
from agent import run


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    config = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    context = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

    tester_cfg = config.get("tester", {})
    client = OpenAI(
        base_url=tester_cfg.get("base_url", os.environ.get("LM_STUDIO_BASE_URL", "http://192.168.2.11:1234/v1")),
        api_key=tester_cfg.get("api_key", os.environ.get("LM_STUDIO_API_KEY", "lm-studio")),
    )
    model = tester_cfg.get("model", os.environ.get("AGENT_MODEL", "locooperator-4b"))

    fixtures = context.get("vars", {}).get("fixtures", {})
    counters = {}

    def dispatch(tool_name: str, args: dict):
        entries = fixtures.get(tool_name, [])
        if not entries:
            return {"error": f"No fixture data for tool: {tool_name}"}
        idx = counters.get(tool_name, 0)
        counters[tool_name] = idx + 1
        return entries[min(idx, len(entries) - 1)]

    result = run(prompt, client, model, dispatch)
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
