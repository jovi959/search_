"""Facade for the user-facing search_google tool implementation."""

import os

from tools.engines import bing, brave, google

_ENGINES = {
    "google": google.search,
    "bing": bing.search,
    "brave": brave.search,
}


def search(driver, query: str) -> list[dict]:
    """Route a search query to the configured engine."""
    name = os.environ.get("SEARCH_ENGINE", "google").strip().lower()
    fn = _ENGINES.get(name)
    if fn is None:
        return [{"error": f"Unknown SEARCH_ENGINE: {name!r}. Valid: {list(_ENGINES)}"}]
    return fn(driver, query)
