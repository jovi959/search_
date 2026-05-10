"""
Real Google search using SeleniumBase UC mode.

Navigates to Google, types the query, and parses organic results.
Waits only for result DOM elements — never for full page readyState.
"""

import os
import random
import time
from urllib.parse import quote_plus

from selenium.webdriver.common.keys import Keys

_RESULT_WAIT = 4
_POLL = 0.1
_CHARS_PER_WORD = 5  # standard WPM convention (avg English word length)
_TYPING_SPEED_BUFF = 0.50      # up to 50% faster than base delay on normal keystrokes
_TYPO_RATE = 0.05              # ~5% chance per char to mistype + backspace
_CLUSTER_SIZE_MIN = 3          # min chars typed in one speed burst
_CLUSTER_SIZE_MAX = 7          # max chars typed in one speed burst
_CLUSTER_PAUSE_MULT_MIN = 1.5  # inter-cluster thinking pause (x base delay)
_CLUSTER_PAUSE_MULT_MAX = 3.5

# Approximate QWERTY adjacency for plausible typos.
_QWERTY_NEIGHBORS = {
    "q": "wa", "w": "qeas", "e": "wrds", "r": "etfd", "t": "ryfg",
    "y": "tugh", "u": "yihj", "i": "uojk", "o": "ipkl", "p": "ol",
    "a": "qwsz", "s": "awedxz", "d": "serfcx", "f": "drtgvc",
    "g": "ftyhbv", "h": "gyujnb", "j": "huiknm", "k": "jiolm", "l": "kop",
    "z": "asx", "x": "zsdc", "c": "xdfv", "v": "cfgb", "b": "vghn",
    "n": "bhjm", "m": "njk",
}


def _stealth_open(driver, url: str):
    """uc_open_with_reconnect when STEALTH_RECONNECT_TIME > 0, else plain get()."""
    try:
        reconnect_time = float(os.environ.get("STEALTH_RECONNECT_TIME", "0"))
    except ValueError:
        reconnect_time = 0.0
    if reconnect_time > 0:
        try:
            driver.uc_open_with_reconnect(url, reconnect_time=reconnect_time)
            return
        except AttributeError:
            pass
    driver.get(url)


def _typo_char(ch: str) -> str:
    """Return a plausible adjacent-key typo for *ch*, preserving case."""
    neighbors = _QWERTY_NEIGHBORS.get(ch.lower())
    if not neighbors:
        return ch
    typo = random.choice(neighbors)
    return typo.upper() if ch.isupper() else typo


def _new_cluster_speed() -> float:
    """Pick a per-cluster speed multiplier in [1 - _TYPING_SPEED_BUFF, 1.0]."""
    return random.uniform(1.0 - _TYPING_SPEED_BUFF, 1.0)


def _new_cluster_size() -> int:
    """Pick how many real characters this burst will type."""
    return random.randint(_CLUSTER_SIZE_MIN, _CLUSTER_SIZE_MAX)


def _human_type(driver, selector: str, text: str):
    """Type *text* into *selector* and submit.

    When TYPING_WPM > 0, types char-by-char in bursts ("clusters") at the
    target WPM. Each burst picks its own speed (up to 50% faster than base);
    a longer thinking-pause separates bursts so rhythm doesn't feel uniform.
    Adjacent-key typos fire ~5% of the time and use the full base delay
    (no buff) so corrections feel deliberate. Otherwise falls back to
    SeleniumBase's instant `driver.type()`.
    """
    try:
        wpm = float(os.environ.get("TYPING_WPM", "0"))
    except ValueError:
        wpm = 0.0

    if wpm <= 0:
        driver.type(selector, text + "\n")
        return

    base_delay = 60.0 / (wpm * _CHARS_PER_WORD)
    element = driver.find_element("css selector", selector)
    element.click()

    cluster_speed = _new_cluster_speed()
    cluster_remaining = _new_cluster_size()

    for ch in text:
        if ch.isalpha() and random.random() < _TYPO_RATE:
            typo = _typo_char(ch)
            if typo != ch:
                element.send_keys(typo)
                time.sleep(base_delay)
                element.send_keys(Keys.BACKSPACE)
                time.sleep(base_delay)

        element.send_keys(ch)
        time.sleep(base_delay * cluster_speed)
        cluster_remaining -= 1

        if cluster_remaining <= 0:
            time.sleep(base_delay * random.uniform(
                _CLUSTER_PAUSE_MULT_MIN, _CLUSTER_PAUSE_MULT_MAX
            ))
            cluster_speed = _new_cluster_speed()
            cluster_remaining = _new_cluster_size()

    element.send_keys(Keys.RETURN)


def search_google(driver, query: str) -> list[dict]:
    """
    Search Google for *query* and return up to 5 organic results.

    Returns a list of dicts: [{"title": ..., "link": ..., "snippet": ...}, ...]
    On failure, returns [{"error": "<message>"}].
    """
    try:
        _stealth_open(driver, "https://www.google.com/")

        _dismiss_consent(driver)

        _type_query(driver, query)
        _wait_for_results(driver)

        results = _parse_results(driver)
        if not results:
            results = _parse_results_fallback(driver)

        if not results:
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            _stealth_open(driver, url)
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
                _human_type(driver, selector, query)
                return
        except Exception:
            continue
    _stealth_open(driver, f"https://www.google.com/search?q={quote_plus(query)}")


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
