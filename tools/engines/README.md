# Search Engine Contributors Guide

Search engines are intentionally simple modules. Each engine owns only its
homepage/search URL, selectors, result parsing, and error message.

## Engine Contract

Create a Python module in this directory with one public function:

```python
def search(driver, query: str) -> list[dict]:
    ...
```

Return up to 5 organic results:

```python
{"title": "Result title", "link": "https://example.com", "snippet": "Summary text"}
```

On failure, return a single error object:

```python
[{"error": "search_engine_name failed: details"}]
```

The user-facing tool is still named `search_google` for compatibility. The
configured engine is selected by `SEARCH_ENGINE` in `.env`; it can be a single
engine name or a rotation list/pattern such as `bing_2,google_2`.

## Add an Engine

1. Create `tools/engines/<name>.py`.
2. Inspect the engine homepage and find a stable search box selector. Prefer a
   stable id, then `textarea[name='q']`, then `input[name='q']`.
3. Inspect one results page and find a stable result card selector.
4. Find title, link, and snippet selectors inside that card.
5. Use `wait_for_element_present` before typing. Only fall back to a search URL
   if the search box cannot be found.
6. Register the engine in [tools/search.py](../search.py) by importing the
   module and adding `"<name>": <name>.search` to `_ENGINES`.
7. Document the engine in [docs/README.md](../../docs/README.md), especially the
   `SEARCH_ENGINE` row.
8. Set `SEARCH_ENGINE=<name>` and `HEADLESS=false` in `.env`, then run a manual
   query with `python main.py "your query"`.

## Template

```python
"""Example search engine implementation."""

import time
from urllib.parse import quote_plus

from tools._browser_utils import human_type, stealth_open

_RESULT_WAIT = 4
_POLL = 0.1
_INPUT_SELECTORS = ("#searchbox", "textarea[name='q']", "input[name='q']")
_INPUT_WAIT = 3


def search(driver, query: str) -> list[dict]:
    try:
        stealth_open(driver, "https://example.com/")
        _type_query(driver, query)
        _wait_for_results(driver)
        results = _parse_results(driver)
        return results if results else [{"error": "No results found"}]
    except Exception as exc:
        return [{"error": f"search_example failed: {exc}"}]


def _type_query(driver, query: str):
    for selector in _INPUT_SELECTORS:
        try:
            driver.wait_for_element_present(selector, timeout=_INPUT_WAIT)
            human_type(driver, selector, query)
            return
        except Exception:
            continue
    stealth_open(driver, f"https://example.com/search?q={quote_plus(query)}")


def _wait_for_results(driver, timeout: float = _RESULT_WAIT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if driver.find_elements("css selector", ".result-card"):
                return
        except Exception:
            pass
        time.sleep(_POLL)


def _parse_results(driver) -> list[dict]:
    results = []
    for card in driver.find_elements("css selector", ".result-card")[:5]:
        try:
            a_tag = card.find_element("css selector", "a[href]")
            title = a_tag.text.strip()
            link = a_tag.get_attribute("href") or ""
            snippet = card.find_element("css selector", ".snippet").text.strip()
            if title and link and "example.com" not in link:
                results.append({"title": title, "link": link, "snippet": snippet})
        except Exception:
            continue
    return results
```

## Helpers You Get For Free

- `stealth_open` respects `STEALTH_RECONNECT_TIME` and can use SeleniumBase UC
  reconnect navigation.
- `human_type` respects `TYPING_WPM`, including textarea support, short pauses,
  and occasional typo correction.
- Promptfoo tests stay mocked below the dispatch boundary, so adding an engine
  should not require fixture changes.

## Common Pitfalls

- Do not assume every search box is an `input`. Bing uses a `textarea`.
- Prefer stable selectors such as ids, names, ARIA labels, and `data-*`
  attributes. Avoid generated class names like DuckDuckGo's or Yahoo's search
  box classes.
- Do not check for the search box immediately after navigation without waiting.
- Filter engine-owned links such as `google.com`, `bing.com`,
  `search.brave.com`, `duckduckgo.com`, or `search.yahoo.com`.
- Return structured result dictionaries, not raw Selenium elements or page text.

## Reference Implementations

- [google.py](google.py): fullest implementation, including consent handling and
  fallback parsing.
- [bing.py](bing.py): small implementation with wait-then-type behavior.
- [brave.py](brave.py): small implementation with card and anchor fallbacks.
- [duckduckgo.py](duckduckgo.py): stable search box selectors and data-attribute
  result parsing.
- [yahoo.py](yahoo.py): stable `#yschsp` / `#uh-sbq` search box selectors and
  Yahoo redirect URL unwrapping.
