"""
Real Google search using SeleniumBase UC mode.

Navigates to Google, types the query, and parses organic results.
Waits only for result DOM elements — never for full page readyState.
"""

import time
from urllib.parse import quote_plus

_RESULT_WAIT = 4
_POLL = 0.1


def search_google(driver, query: str) -> list[dict]:
    """
    Search Google for *query* and return up to 5 organic results.

    Returns a list of dicts: [{"title": ..., "link": ..., "snippet": ...}, ...]
    On failure, returns [{"error": "<message>"}].
    """
    try:
        driver.get("https://www.google.com/")

        _dismiss_consent(driver)

        _type_query(driver, query)
        _wait_for_results(driver)

        results = _parse_results(driver)
        if not results:
            results = _parse_results_fallback(driver)

        if not results:
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            driver.get(url)
            _wait_for_results(driver)
            results = _parse_results(driver)
            if not results:
                results = _parse_results_fallback(driver)

        return results if results else [{"error": "No results found"}]

    except Exception as exc:
        return [{"error": f"search_google failed: {exc}"}]


def _wait_for_results(driver, timeout: float = _RESULT_WAIT):
    """Poll until Google result elements appear in the DOM."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if driver.find_elements("css selector", "div.g") or \
               driver.find_elements("css selector", "a h3"):
                return
        except Exception:
            pass
        time.sleep(_POLL)


def _type_query(driver, query: str):
    """Type query into the Google search box and submit."""
    for selector in ["textarea[name='q']", "input[name='q']"]:
        try:
            if driver.is_element_present(selector):
                driver.type(selector, query + "\n")
                return
        except Exception:
            continue
    driver.get(f"https://www.google.com/search?q={quote_plus(query)}")


def _dismiss_consent(driver):
    """Click through Google consent / cookie banners if present."""
    try:
        for selector in [
            "button#L2AGLb",
            "button[aria-label='Accept all']",
            "form[action*='consent'] button",
        ]:
            if driver.is_element_visible(selector):
                driver.click(selector)
                time.sleep(0.5)
                break
    except Exception:
        pass


def _parse_results(driver) -> list[dict]:
    """Parse Google SERP via standard div.g containers."""
    results = []
    try:
        cards = driver.find_elements("css selector", "div.g")
        for card in cards[:5]:
            try:
                a_tag = card.find_element("css selector", "a[href]")
                link = a_tag.get_attribute("href") or ""

                title_el = card.find_element("css selector", "h3")
                title = title_el.text.strip() if title_el else ""

                snippet = _get_snippet(card)

                if title and link and "google.com" not in link:
                    results.append({"title": title, "link": link, "snippet": snippet})
            except Exception:
                continue
    except Exception:
        pass
    return results


def _parse_results_fallback(driver) -> list[dict]:
    """Fallback: grab any <a> that wraps an <h3>."""
    results = []
    try:
        h3_list = driver.find_elements("css selector", "a h3")
        for h3 in h3_list[:5]:
            try:
                a_tag = h3.find_element("xpath", "..")
                link = a_tag.get_attribute("href") or ""
                title = h3.text.strip()
                if title and link and "google.com" not in link:
                    results.append({"title": title, "link": link, "snippet": ""})
            except Exception:
                continue
    except Exception:
        pass
    return results


def _get_snippet(card) -> str:
    """Try multiple selectors for the snippet text under a result card."""
    for sel in [
        "div.VwiC3b", "span.st", "div[data-sncf]",
        "div[style*='line-clamp']", "div.IsZvec",
    ]:
        try:
            el = card.find_element("css selector", sel)
            text = el.text.strip()
            if text:
                return text
        except Exception:
            continue
    return ""
