"""
Real page content fetcher using SeleniumBase UC mode.

Accepts a live SeleniumBase Driver instance, navigates to the URL,
and returns cleaned text content matching the agent's expected schema.
"""

from bs4 import BeautifulSoup


def get_page_content(driver, url: str) -> dict:
    """
    Fetch *url* and return its readable text.

    Returns {"url": ..., "page_text": ...} on success,
    or {"url": ..., "error": ...} on failure.
    """
    try:
        driver.uc_open_with_reconnect(url, reconnect_time=4)
        driver.sleep(2)

        page_source = driver.get_page_source()
        text = _extract_text(page_source)

        if not text.strip():
            return {"url": url, "error": "Page loaded but no readable text found"}

        trimmed = _trim(text, max_chars=12000)
        return {"url": url, "page_text": trimmed}

    except Exception as exc:
        return {"url": url, "error": f"get_page_content failed: {exc}"}


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
