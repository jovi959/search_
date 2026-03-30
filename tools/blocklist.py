"""
URL blocklist — blocks tool calls to sites the user doesn't want visited.

Reads patterns from ``blocklist.json`` at the project root.
Patterns are matched against the URL's hostname using fnmatch-style
wildcards (``*`` and ``?``).  A pattern containing ``://`` is matched
against the full URL instead.

The file is re-read on every check so edits take effect immediately
without restarting the server.
"""

import fnmatch
import json
from pathlib import Path
from urllib.parse import urlparse

_BLOCKLIST_PATH = Path(__file__).resolve().parent.parent / "blocklist.json"


def _load_patterns() -> list[str]:
    if not _BLOCKLIST_PATH.exists():
        return []
    try:
        data = json.loads(_BLOCKLIST_PATH.read_text(encoding="utf-8"))
        return data.get("blocked", [])
    except (json.JSONDecodeError, KeyError, OSError):
        return []


def is_blocked(url: str) -> bool:
    """Return True if *url* matches any pattern in blocklist.json."""
    patterns = _load_patterns()
    if not patterns:
        return False

    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return False

    hostname = hostname.lower()
    full_url = url.lower()

    for pattern in patterns:
        p = pattern.strip().lower()
        if not p:
            continue
        if "://" in p:
            if fnmatch.fnmatch(full_url, p):
                return True
        else:
            if fnmatch.fnmatch(hostname, p):
                return True

    return False
