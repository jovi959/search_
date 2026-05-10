"""
Shared browser helpers for search engines.

These helpers are intentionally small and SeleniumBase-oriented so each search
engine module can focus on its own page selectors.
"""

import os
import random
import time

from selenium.webdriver.common.keys import Keys

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


def stealth_open(driver, url: str):
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


def typo_char(ch: str) -> str:
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


def human_type(driver, selector: str, text: str):
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
            typo = typo_char(ch)
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
