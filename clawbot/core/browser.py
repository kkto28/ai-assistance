"""
Shared Chrome-over-CDP connector, used by any skill that controls your
real, already-running Chrome (browser_skill.py).

Chrome must already be running with remote debugging enabled.

Two entry points, for two different lifecycles:
  - connect_browser(): raw (pw, browser, context) for a skill that
    manages its own page(s) over a longer session.
  - open_page(): convenience (pw, page) for a skill that does one
    quick read-only task per call -- navigate, extract, disconnect.
"""
from __future__ import annotations
from config import config


def connect_browser():
    """Returns (playwright_instance, browser, context). Caller is
    responsible for opening/closing pages and eventually calling
    playwright_instance.stop() -- this only disconnects our driver,
    it does NOT close your actual Chrome."""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    endpoint = f"http://localhost:{config.chrome_cdp_port}"
    browser = pw.chromium.connect_over_cdp(endpoint)
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    return pw, browser, context


def open_page():
    """Convenience for a single quick task: connect, open one new tab,
    return (playwright_instance, page). Caller should page.close() (if
    it doesn't want the tab left open) then playwright_instance.stop()
    when done."""
    pw, browser, context = connect_browser()
    page = context.new_page()
    return pw, page
