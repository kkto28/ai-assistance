"""
Browser skill: read-only actions against a webpage, using your real,
already-running Chrome over CDP (core/browser.py's shared connector).

All four tools are registered as non-dangerous: they do not submit
forms, click buttons, or otherwise change the page. The screenshot tool
does write a local file. Interactive actions such as click or fill_form
should be separate tools marked dangerous=True.

Requires: pip install playwright
"""
from __future__ import annotations
import re
import time

from core.browser import open_page
from skills import tool
from skills.file_skill import WORKSPACE


def _safe_filename(url: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:60].strip("_")
    return f"screenshot_{stem}_{int(time.time())}.png"


def _missing_playwright() -> str:
    return "Error: playwright not installed. Run: pip install playwright"


@tool(
    name="navigate",
    description=(
        "Open a URL in a new tab in your real Chrome, leaving it open "
        "for you to see. Use when the user wants a page actually shown, "
        "not just its content read back."
    ),
)
def navigate(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401 (import check)
    except ImportError:
        return _missing_playwright()
    try:
        pw, page = open_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        title = page.title()
        pw.stop()  # disconnects our driver only -- the tab stays open in Chrome
        return f"Opened {url} ({title})"
    except Exception as e:
        return f"Error navigating: {e}"


@tool(
    name="get_page_text",
    description=(
        "Fetch a URL and return its visible text content, for reading "
        "or summarizing an article/page without opening it yourself."
    ),
)
def get_page_text(url: str, max_chars: str = "3000") -> str:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return _missing_playwright()
    try:
        pw, page = open_page()
        page.goto(url, wait_until="networkidle", timeout=30_000)
        text = page.inner_text("body").strip()
        page.close()
        pw.stop()

        limit = int(max_chars)
        if len(text) > limit:
            text = text[:limit] + f"\n... [truncated, {len(text)} total chars]"
        return text or "(page has no visible text)"
    except Exception as e:
        return f"Error fetching page text: {e}"


@tool(
    name="get_links",
    description="Fetch a URL and list the links found on the page (text and href).",
)
def get_links(url: str, max_links: str = "30") -> str:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return _missing_playwright()
    try:
        pw, page = open_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))",
        )
        page.close()
        pw.stop()

        if not links:
            return "(no links found)"
        limit = int(max_links)
        lines = [
            f"{(l['text'][:60] or '(no text)')} -> {l['href']}"
            for l in links[:limit]
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching links: {e}"


@tool(
    name="screenshot",
    description=(
        "Navigate to a URL and save a screenshot of it as a PNG file "
        "in the workspace."
    )
)
def screenshot(url: str, full_page: str = "true") -> str:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return _missing_playwright()
    try:
        pw, page = open_page()
        page.goto(url, wait_until="networkidle", timeout=30_000)

        filename = _safe_filename(url)
        output_path = WORKSPACE / filename
        page.screenshot(
            path=str(output_path), full_page=(full_page.lower() == "true")
        )
        page.close()
        pw.stop()

        return f"Saved screenshot to workspace/{filename}"
    except Exception as e:
        return f"Error capturing screenshot: {e}"
