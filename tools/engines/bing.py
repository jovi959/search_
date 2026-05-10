"""Bing search engine implementation."""

import base64
import binascii
import time
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from tools._browser_utils import human_type, stealth_open

_RESULT_WAIT = 4
_POLL = 0.1
_INPUT_SELECTORS = ("#sb_form_q", "textarea[name='q']", "input[name='q']")
_INPUT_WAIT = 3


def search(driver, query: str) -> list[dict]:
    """Search Bing and return up to 5 organic results."""
    try:
        stealth_open(driver, "https://www.bing.com/")
        _type_query(driver, query)
        _wait_for_results(driver)
        results = _parse_results(driver)
        return results if results else [{"error": "No results found"}]

    except Exception as exc:
        return [{"error": f"search_bing failed: {exc}"}]


def _type_query(driver, query: str):
    """Wait briefly for Bing's search box, then human-type into it.

    Falls back to URL-based search only if no selector matches in time.
    """
    for selector in _INPUT_SELECTORS:
        try:
            driver.wait_for_element_present(selector, timeout=_INPUT_WAIT)
            human_type(driver, selector, query)
            return
        except Exception:
            continue
    stealth_open(driver, f"https://www.bing.com/search?q={quote_plus(query)}")


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
                link = _clean_link(a_tag.get_attribute("href") or "")
                title = a_tag.text.strip()
                snippet = _get_snippet(card)

                if title and link and "bing.com" not in urlparse(link).netloc.lower():
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


def _clean_link(link: str) -> str:
    """Unwrap Bing's bing.com/ck/a?...&u=a1<base64url> redirector to the real URL."""
    if not link:
        return ""
    parsed = urlparse(link)
    host = parsed.netloc.lower()
    if not host.endswith("bing.com") or not parsed.path.startswith("/ck/"):
        return link
    raw = parse_qs(parsed.query).get("u", [""])[0]
    if not raw:
        return link
    payload = raw[2:] if len(raw) > 2 and raw[0].lower() == "a" and raw[1].isdigit() else raw
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload).decode("utf-8", "replace")
    except (binascii.Error, ValueError):
        return link
    decoded = decoded.strip()
    if decoded.lower().startswith(("http://", "https://")):
        return decoded
    try:
        return unquote(decoded) or link
    except Exception:
        return link
