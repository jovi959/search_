"""
Page content fetcher using SeleniumBase.

Uses regular navigation for content pages (UC stealth is only needed for Google).
Falls back gracefully on connection, timeout, and SSL errors.
"""

import re

from bs4 import BeautifulSoup

_CHROME_ERROR_PATTERNS = [
    (r"NET::ERR_CERT_", "SSL certificate error"),
    (r"net::ERR_CERT_", "SSL certificate error"),
    (r"ERR_NAME_NOT_RESOLVED", "DNS resolution failed"),
    (r"ERR_CONNECTION_REFUSED", "Connection refused"),
    (r"ERR_CONNECTION_TIMED_OUT", "Connection timed out"),
    (r"ERR_CONNECTION_RESET", "Connection reset"),
    (r"ERR_TIMED_OUT", "Request timed out"),
    (r"ERR_SSL_PROTOCOL_ERROR", "SSL protocol error"),
    (r"ERR_INTERNET_DISCONNECTED", "No internet connection"),
]


def get_page_content(driver, url: str) -> dict:
    """
    Fetch *url* and return its readable text.

    Returns {"url": ..., "page_text": ...} on success,
    or {"url": ..., "error": ...} on failure.
    """
    try:
        driver.get(url)
    except Exception:
        try:
            driver.execute_script(f"window.location.href = '{_escape_js(url)}';")
        except Exception as nav_exc:
            return {"url": url, "error": f"Navigation failed: {nav_exc}"}

    try:
        page_source = driver.execute_script(
            "return document.documentElement.outerHTML;"
        )
    except Exception:
        try:
            page_source = driver.get_page_source()
        except Exception as src_exc:
            return {"url": url, "error": f"Could not read page source: {src_exc}"}

    error = _detect_error_page(page_source)
    if error:
        return {"url": url, "error": error}

    text = _extract_text(page_source)
    if not text.strip():
        return {"url": url, "error": "Page loaded but no readable text found"}

    return {"url": url, "page_text": _trim(text)}


def _detect_error_page(html: str) -> str | None:
    """Return an error message if Chrome is showing an error/interstitial page."""
    if not html:
        return None

    for pattern, label in _CHROME_ERROR_PATTERNS:
        if re.search(pattern, html):
            return f"Page blocked by browser: {label}"

    if 'id="main-frame-error"' in html:
        return "Page blocked by browser: Chrome error page"
    if 'class="interstitial-wrapper"' in html:
        return "Page blocked by browser: security interstitial"
    if "Your connection is not private" in html and "PEM encoded chain" in html:
        return "Page blocked by browser: SSL certificate error"

    return None


def _escape_js(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "noscript", "iframe", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _trim(text: str, max_chars: int = 12000) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit("\n", 1)[0]
    return cut + "\n[... content truncated ...]"
