"""Brave Search engine implementation."""

import time
from urllib.parse import quote_plus

from tools._browser_utils import human_type, stealth_open

_RESULT_WAIT = 4
_POLL = 0.1
_INPUT_SELECTORS = ("#searchbox", "textarea[name='q']", "input[name='q']")
_INPUT_WAIT = 3
_INTERNAL_HOSTS = ("search.brave.com", "brave.com/search")


def search(driver, query: str) -> list[dict]:
    """Search Brave and return up to 5 organic results."""
    try:
        stealth_open(driver, "https://search.brave.com/")
        _type_query(driver, query)
        _wait_for_results(driver)

        results = _parse_results(driver)
        if not results:
            results = _parse_results_fallback(driver)

        if not results:
            stealth_open(driver, f"https://search.brave.com/search?q={quote_plus(query)}")
            _wait_for_results(driver)
            results = _parse_results(driver)
            if not results:
                results = _parse_results_fallback(driver)

        return results if results else [{"error": "No results found"}]

    except Exception as exc:
        return [{"error": f"search_brave failed: {exc}"}]


def _type_query(driver, query: str):
    """Wait briefly for Brave's search box, then human-type into it."""
    for selector in _INPUT_SELECTORS:
        try:
            driver.wait_for_element_present(selector, timeout=_INPUT_WAIT)
            human_type(driver, selector, query)
            return
        except Exception:
            continue
    stealth_open(driver, f"https://search.brave.com/search?q={quote_plus(query)}")


def _wait_for_results(driver, timeout: float = _RESULT_WAIT):
    """Poll until Brave result elements appear in the DOM."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if (
                driver.find_elements("css selector", "div.snippet[data-type='web']")
                or driver.find_elements("css selector", "div.snippet")
                or driver.find_elements("css selector", "a.heading-serpresult")
            ):
                return
        except Exception:
            pass
        time.sleep(_POLL)


def _parse_results(driver) -> list[dict]:
    """Parse Brave SERP via standard result containers."""
    results = []
    try:
        cards = driver.find_elements(
            "css selector",
            "div.snippet[data-type='web'], div.snippet",
        )
        for card in cards[:5]:
            try:
                a_tag = card.find_element("css selector", "a[href]")
                link = a_tag.get_attribute("href") or ""
                title = _get_title(card, a_tag)
                snippet = _get_snippet(card)

                if title and link and not _is_internal_link(link):
                    results.append({"title": title, "link": link, "snippet": snippet})
            except Exception:
                continue
    except Exception:
        pass
    return results


def _parse_results_fallback(driver) -> list[dict]:
    """Fallback: grab title anchors directly when result cards change."""
    results = []
    try:
        anchors = driver.find_elements("css selector", "a.heading-serpresult, a.h")
        for anchor in anchors[:5]:
            try:
                link = anchor.get_attribute("href") or ""
                title = anchor.text.strip()
                if title and link and not _is_internal_link(link):
                    results.append({"title": title, "link": link, "snippet": ""})
            except Exception:
                continue
    except Exception:
        pass
    return results


def _get_title(card, a_tag) -> str:
    """Return the visible title text for a Brave result card."""
    for selector in (".title", ".heading-serpresult", "h3", "h4"):
        try:
            el = card.find_element("css selector", selector)
            text = el.text.strip()
            if text:
                return text
        except Exception:
            continue
    return a_tag.text.strip()


def _get_snippet(card) -> str:
    """Return the Brave result snippet text when present."""
    for selector in (".snippet-description", ".snippet-content p", ".description", "p"):
        try:
            el = card.find_element("css selector", selector)
            text = el.text.strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def _is_internal_link(link: str) -> bool:
    """Return True for Brave-owned links that should not be returned as results."""
    lower = link.lower()
    return any(host in lower for host in _INTERNAL_HOSTS)
