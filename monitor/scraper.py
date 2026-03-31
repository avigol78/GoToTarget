"""
Extract call-centre statistics from the top of the ERAN portal page.

The header row looks roughly like:
  שלוחה: none | בשיחה: 1 | בהמתנה: 2 | בהפסקה: 0 | מחוברים/ות: 6 | פונים/ות: 2 | שיחות: 1

We scrape the four values the user cares about:
  calls      – שיחות (active calls)
  waiting    – פונים ממתינים / בהמתנה (waiting callers)
  connected  – מחוברים (connected volunteers)
  on_break   – בהפסקה (volunteers on break)
"""
import re
import logging

log = logging.getLogger(__name__)

# Map of our field names → possible Hebrew label substrings (right-to-left friendly)
_FIELD_PATTERNS = {
    "calls":     [r"שיחות[^\d]*(\d+)", r"(\d+)[^\d]*שיחות"],
    "waiting":   [r"בהמתנה[^\d]*(\d+)", r"ממתינ[^\d]*(\d+)", r"(\d+)[^\d]*בהמתנה"],
    "connected": [r"מחוברים[^\d]*(\d+)", r"מחוברות[^\d]*(\d+)", r"(\d+)[^\d]*מחובר"],
    "on_break":  [r"בהפסקה[^\d]*(\d+)", r"הפסקה[^\d]*(\d+)", r"(\d+)[^\d]*בהפסקה"],
}


def _extract_int(text: str, patterns: list) -> int | None:
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    return None


def scrape_stats(page) -> dict:
    """
    Given a Playwright page already at the call-centre URL,
    return a dict with keys: calls, waiting, connected, on_break.
    Missing values are None.
    """
    # Try to get the header/status-bar text
    raw_text = ""

    # Strategy 1: grab the whole visible header area
    for selector in [
        ".status-bar", ".header-stats", ".call-center-header",
        "[class*='status']", "[class*='header']", "[class*='stats']",
        "header", "#header", ".navbar", ".top-bar",
    ]:
        try:
            el = page.query_selector(selector)
            if el:
                t = el.inner_text()
                if any(kw in t for kw in ["שיחות", "מחובר", "בהפסקה", "ממתינ"]):
                    raw_text = t
                    log.debug("Found stats via selector '%s'", selector)
                    break
        except Exception:
            pass

    # Strategy 2: fall back to full page text
    if not raw_text:
        try:
            raw_text = page.inner_text("body")
        except Exception as exc:
            log.error("Could not read page body: %s", exc)
            return {}

    data = {}
    for field, patterns in _FIELD_PATTERNS.items():
        data[field] = _extract_int(raw_text, patterns)

    log.info("Scraped: %s", data)
    return data
