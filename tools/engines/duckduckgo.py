"""DuckDuckGo search engine implementation."""

import time
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from tools._browser_utils import human_type, stealth_open

_RESULT_WAIT = 4
_POLL = 0.1
_INPUT_SELECTORS = (
    "#searchbox_input",
    "input[name='q'][aria-label='Search with DuckDuckGo']",
    "input[name='q']",
)
_INPUT_WAIT = 3
_INTERNAL_HOSTS = ("duckduckgo.com", "duck.com")


def search(driver, query: str) -> list[dict]:
    """Search DuckDuckGo and return up to 5 organic results."""
    try:
        stealth_open(driver, "https://duckduckgo.com/")
        _type_query(driver, query)
        _wait_for_results(driver)

        results = _parse_results(driver)
        if not results:
            results = _parse_results_fallback(driver)

        if not results:
            stealth_open(driver, f"https://duckduckgo.com/?q={quote_plus(query)}")
            _wait_for_results(driver)
            results = _parse_results(driver)
            if not results:
                results = _parse_results_fallback(driver)

        return results if results else [{"error": "No results found"}]

    except Exception as exc:
        return [{"error": f"search_duckduckgo failed: {exc}"}]


def _type_query(driver, query: str):
    """Wait briefly for DuckDuckGo's search box, then human-type into it."""
    for selector in _INPUT_SELECTORS:
        try:
            driver.wait_for_element_present(selector, timeout=_INPUT_WAIT)
            human_type(driver, selector, query)
            return
        except Exception:
            continue
    stealth_open(driver, f"https://duckduckgo.com/?q={quote_plus(query)}")


def _wait_for_results(driver, timeout: float = _RESULT_WAIT):
    """Poll until DuckDuckGo result elements appear in the DOM."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if (
                driver.find_elements("css selector", "[data-testid='result']")
                or driver.find_elements("css selector", "article")
                or driver.find_elements("css selector", "a[data-testid='result-title-a']")
                or driver.find_elements("css selector", "main a[href]")
            ):
                return
        except Exception:
            pass
        time.sleep(_POLL)


def _parse_results(driver) -> list[dict]:
    """Parse DuckDuckGo SERP via stable data attributes and semantic tags."""
    results = []
    seen = set()
    try:
        cards = driver.find_elements("css selector", "[data-testid='result'], article")
        for card in cards:
            try:
                a_tag = _find_first(
                    card,
                    (
                        "a[data-testid='result-title-a']",
                        "h2 a[href]",
                        "a[href]",
                    ),
                )
                if a_tag is None:
                    continue

                link = _clean_link(a_tag.get_attribute("href") or "")
                title = _get_title(card, a_tag)
                snippet = _get_snippet(card)

                if title and link and link not in seen and not _is_internal_link(link):
                    seen.add(link)
                    results.append({"title": title, "link": link, "snippet": snippet})
                    if len(results) >= 5:
                        break
            except Exception:
                continue
    except Exception:
        pass
    return results


def _parse_results_fallback(driver) -> list[dict]:
    """Fallback: grab result-like anchors directly when card markup changes."""
    results = []
    seen = set()
    try:
        anchors = driver.find_elements(
            "css selector",
            "a[data-testid='result-title-a'], main h2 a[href], article h2 a[href], main a[href]",
        )
        for anchor in anchors:
            try:
                link = _clean_link(anchor.get_attribute("href") or "")
                title = anchor.text.strip()
                if title and link and link not in seen and not _is_internal_link(link):
                    seen.add(link)
                    results.append({"title": title, "link": link, "snippet": ""})
                    if len(results) >= 5:
                        break
            except Exception:
                continue
    except Exception:
        pass
    return results


def _find_first(parent, selectors: tuple[str, ...]):
    """Return the first descendant matching one of the static selectors."""
    for selector in selectors:
        try:
            return parent.find_element("css selector", selector)
        except Exception:
            continue
    return None


def _get_title(card, a_tag) -> str:
    """Return the visible title text for a DuckDuckGo result card."""
    for selector in ("a[data-testid='result-title-a']", "h2"):
        try:
            el = card.find_element("css selector", selector)
            text = el.text.strip()
            if text:
                return text
        except Exception:
            continue
    return a_tag.text.strip()


def _get_snippet(card) -> str:
    """Return the DuckDuckGo result snippet text when present."""
    for selector in (
        "[data-result='snippet']",
        "[data-testid='result-snippet']",
        "[data-testid='result-extras-snippet']",
        "p",
    ):
        try:
            el = card.find_element("css selector", selector)
            text = el.text.strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def _clean_link(link: str) -> str:
    """Unwrap DuckDuckGo redirect URLs when they contain an uddg target."""
    if not link:
        return ""
    parsed = urlparse(link)
    host = parsed.netloc.lower()
    if host.endswith("duckduckgo.com"):
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return unquote(target[0])
    return link


def _is_internal_link(link: str) -> bool:
    """Return True for DuckDuckGo-owned links that should not be results."""
    parsed = urlparse(link)
    host = parsed.netloc.lower()
    return any(host == internal or host.endswith(f".{internal}") for internal in _INTERNAL_HOSTS)
