"""Yahoo Search engine implementation."""

import re
import time
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from tools._browser_utils import human_type, stealth_open

_RESULT_WAIT = 4
_POLL = 0.1
_INPUT_SELECTORS = (
    "#uh-sbq",
    "input[type='search'][placeholder='Search the web']",
    "input[type='search']",
)
_INPUT_WAIT = 3
_INTERNAL_HOSTS = (
    "search.yahoo.com",
    "r.search.yahoo.com",
    "login.yahoo.com",
    "help.yahoo.com",
)


def search(driver, query: str) -> list[dict]:
    """Search Yahoo and return up to 5 organic results."""
    try:
        stealth_open(driver, "https://search.yahoo.com/")
        _type_query(driver, query)
        _wait_for_results(driver)

        results = _parse_results(driver)
        if not results:
            results = _parse_results_fallback(driver)

        if not results:
            stealth_open(driver, f"https://search.yahoo.com/search?p={quote_plus(query)}")
            _wait_for_results(driver)
            results = _parse_results(driver)
            if not results:
                results = _parse_results_fallback(driver)

        return results if results else [{"error": "No results found"}]

    except Exception as exc:
        return [{"error": f"search_yahoo failed: {exc}"}]


def _type_query(driver, query: str):
    """Wait briefly for Yahoo's search box, then human-type into it."""
    for selector in _INPUT_SELECTORS:
        try:
            driver.wait_for_element_present(selector, timeout=_INPUT_WAIT)
            human_type(driver, selector, query)
            return
        except Exception:
            continue
    stealth_open(driver, f"https://search.yahoo.com/search?p={quote_plus(query)}")


def _wait_for_results(driver, timeout: float = _RESULT_WAIT):
    """Poll until Yahoo result elements appear in the DOM."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if (
                driver.find_elements("css selector", "#web li")
                or driver.find_elements("css selector", "main li h3 a[href]")
                or driver.find_elements("css selector", "ol li h3 a[href]")
                or driver.find_elements("css selector", "h3 a[href]")
            ):
                return
        except Exception:
            pass
        time.sleep(_POLL)


def _parse_results(driver) -> list[dict]:
    """Parse Yahoo SERP using result-list and heading anchors."""
    results = []
    seen = set()
    try:
        cards = driver.find_elements("css selector", "#web li, main li, ol li")
        for card in cards:
            try:
                a_tag = _find_first(card, ("h3 a[href]", "a[href]"))
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
    """Fallback: grab result-like title anchors directly."""
    results = []
    seen = set()
    try:
        anchors = driver.find_elements(
            "css selector",
            "#web h3 a[href], main h3 a[href], ol h3 a[href], h3 a[href]",
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
    """Return the visible title text for a Yahoo result card."""
    try:
        title = card.find_element("css selector", "h3")
        text = title.text.strip()
        if text:
            return text
    except Exception:
        pass
    return a_tag.text.strip()


def _get_snippet(card) -> str:
    """Return the Yahoo result snippet text when present."""
    for selector in ("p", "div p"):
        try:
            el = card.find_element("css selector", selector)
            text = el.text.strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def _clean_link(link: str) -> str:
    """Unwrap Yahoo redirect URLs when they contain a target URL."""
    if not link:
        return ""

    parsed = urlparse(link)
    params = parse_qs(parsed.query)
    for key in ("RU", "ru", "u"):
        if params.get(key):
            return unquote(params[key][0])

    match = re.search(r"/RU=([^/]+)", parsed.path)
    if match:
        return unquote(match.group(1))

    return link


def _is_internal_link(link: str) -> bool:
    """Return True for Yahoo search-owned links that should not be results."""
    parsed = urlparse(link)
    host = parsed.netloc.lower()
    return any(host == internal or host.endswith(f".{internal}") for internal in _INTERNAL_HOSTS)
