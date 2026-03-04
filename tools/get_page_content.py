"""
Real page content fetcher using SeleniumBase.

Uses regular navigation for content pages (UC stealth is only needed for Google).
Falls back gracefully on connection or timeout errors.
"""

from bs4 import BeautifulSoup


def get_page_content(driver, url: str) -> dict:
    """
    Fetch *url* and return its readable text.

    Returns {"url": ..., "page_text": ...} on success,
    or {"url": ..., "error": ...} on failure.
    """
    try:
        driver.default_get_open(url)
        driver.sleep(2)
    except Exception:
        try:
            driver.execute_script(f"window.location.href = '{_escape_js(url)}';")
            driver.sleep(3)
        except Exception as nav_exc:
            return {"url": url, "error": f"Navigation failed: {nav_exc}"}

    try:
        page_source = driver.get_page_source()
    except Exception:
        try:
            page_source = driver.execute_script("return document.documentElement.outerHTML;")
        except Exception as src_exc:
            return {"url": url, "error": f"Could not read page source: {src_exc}"}

    text = _extract_text(page_source)

    if not text.strip():
        return {"url": url, "error": "Page loaded but no readable text found"}

    trimmed = _trim(text, max_chars=12000)
    return {"url": url, "page_text": trimmed}


def _escape_js(s: str) -> str:
    """Escape a string for safe embedding in a JS single-quoted literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _extract_text(html: str) -> str:
    """Strip HTML to readable text, removing nav/script/style noise."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "noscript", "iframe", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _trim(text: str, max_chars: int = 12000) -> str:
    """Truncate to *max_chars* on a line boundary."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit("\n", 1)[0]
    return cut + "\n[... content truncated ...]"
