import json
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
ALL_TOOLS = json.loads((TOOLS_DIR / "definitions.json").read_text(encoding="utf-8"))
TOOL_DEFS_BY_NAME = {t["function"]["name"]: t for t in ALL_TOOLS}


def get_openai_tools() -> list[dict]:
    """Return all tool definitions in OpenAI function-calling format."""
    return list(ALL_TOOLS)
