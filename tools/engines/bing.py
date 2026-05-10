"""Bing search engine implementation."""

import time
from urllib.parse import quote_plus

from tools._browser_utils import human_type, stealth_open

_RESULT_WAIT = 4
_POLL = 0.1


def search(driver, query: str) -> list[dict]:
    """Search Bing and return up to 5 organic results."""
    try:
        stealth_open(driver, "https://www.bing.com/")
        if driver.is_element_present("input[name='q']"):
            human_type(driver, "input[name='q']", query)
        else:
            stealth_open(driver, f"https://www.bing.com/search?q={quote_plus(query)}")

        _wait_for_results(driver)
        results = _parse_results(driver)
        return results if results else [{"error": "No results found"}]

    except Exception as exc:
        return [{"error": f"search_bing failed: {exc}"}]


def _wait_for_results(driver, timeout: float = _RESULT_WAIT):
    """Poll until Bing result elements appear in the DOM."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if driver.find_elements("css selector", "li.b_algo"):
                return
        except Exception:
            pass
        time.sleep(_POLL)


def _parse_results(driver) -> list[dict]:
    """Parse Bing SERP via standard li.b_algo result containers."""
    results = []
    try:
        cards = driver.find_elements("css selector", "li.b_algo")
        for card in cards[:5]:
            try:
                a_tag = card.find_element("css selector", "h2 > a")
                link = a_tag.get_attribute("href") or ""
                title = a_tag.text.strip()
                snippet = _get_snippet(card)

                if title and link:
                    results.append({"title": title, "link": link, "snippet": snippet})
            except Exception:
                continue
    except Exception:
        pass
    return results


def _get_snippet(card) -> str:
    """Return the Bing result snippet text when present."""
    try:
        el = card.find_element("css selector", ".b_caption p")
        return el.text.strip()
    except Exception:
        return ""
