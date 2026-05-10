"""Facade for the user-facing search_google tool implementation."""

import os
import re
import threading
from collections.abc import Callable

from tools.engines import bing, brave, duckduckgo, google, yahoo

_ENGINES = {
    "google": google.search,
    "bing": bing.search,
    "brave": brave.search,
    "duckduckgo": duckduckgo.search,
    "yahoo": yahoo.search,
}

_COUNT_TOKEN_RE = re.compile(r"^(.+)_([1-9][0-9]*)$")
_cursor = 0
_lock = threading.Lock()


def _parse(value: str) -> list[str]:
    """Expand SEARCH_ENGINE into a flat rotation schedule."""
    schedule = []
    for raw_token in value.split(","):
        token = raw_token.strip().lower()
        if not token:
            continue

        match = _COUNT_TOKEN_RE.fullmatch(token)
        if match is None:
            schedule.append(token)
            continue

        name, count = match.groups()
        schedule.extend([name] * int(count))

    return schedule or ["google"]


_SCHEDULE = _parse(os.environ.get("SEARCH_ENGINE", "google"))


def _pick_next() -> tuple[str, Callable[[], None]]:
    with _lock:
        name = _SCHEDULE[_cursor % len(_SCHEDULE)]

    def advance() -> None:
        global _cursor
        with _lock:
            _cursor += 1

    return name, advance


def search(driver, query: str) -> list[dict]:
    """Route a search query to the configured engine."""
    name, advance = _pick_next()
    fn = _ENGINES.get(name)
    try:
        if fn is None:
            return [{"error": f"Unknown SEARCH_ENGINE: {name!r}. Valid: {list(_ENGINES)}"}]
        return fn(driver, query)
    finally:
        advance()
