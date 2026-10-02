import builtins
import sys
from types import ModuleType

import pytest

from skills import browser_skill, registry


@pytest.fixture
def playwright_available(monkeypatch):
    package = ModuleType("playwright")
    package.__path__ = []
    api = ModuleType("playwright.sync_api")
    api.sync_playwright = lambda: None
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", api)


def test_safe_filename_sanitizes_url_and_uses_timestamp(monkeypatch):
    monkeypatch.setattr(browser_skill.time, "time", lambda: 123)

    assert browser_skill._safe_filename("https://example.com/a?x=1") == (
        "screenshot_https_example_com_a_x_1_123.png"
    )


def test_navigate_opens_page_and_leaves_tab_open(monkeypatch, playwright_available):
    calls = []

    class Page:
        def goto(self, url, **kwargs):
            calls.append(("goto", url, kwargs))

        def title(self):
            return "Example"

        def close(self):
            calls.append(("close_page",))

    class Playwright:
        def stop(self):
            calls.append(("stop",))

    monkeypatch.setattr(browser_skill, "open_page", lambda: (Playwright(), Page()))

    assert browser_skill.navigate("https://example.com") == (
        "Opened https://example.com (Example)"
    )
    assert calls == [
        (
            "goto",
            "https://example.com",
            {"wait_until": "domcontentloaded", "timeout": 30_000},
        ),
        ("stop",),
    ]


def test_get_page_text_strips_and_truncates_content(
    monkeypatch, playwright_available
):
    calls = []

    class Page:
        def goto(self, _url, **_kwargs):
            pass

        def inner_text(self, selector):
            assert selector == "body"
            return "  Readable page content  "

        def close(self):
            calls.append("close_page")

    class Playwright:
        def stop(self):
            calls.append("stop")

    monkeypatch.setattr(browser_skill, "open_page", lambda: (Playwright(), Page()))

    assert browser_skill.get_page_text("https://example.com", "8") == (
        "Readable\n... [truncated, 21 total chars]"
    )
    assert calls == ["close_page", "stop"]


def test_get_page_text_reports_empty_pages(monkeypatch, playwright_available):
    class Page:
        def goto(self, _url, **_kwargs):
            pass

        def inner_text(self, _selector):
            return " \n "

        def close(self):
            pass

    class Playwright:
        def stop(self):
            pass

    monkeypatch.setattr(browser_skill, "open_page", lambda: (Playwright(), Page()))

    assert browser_skill.get_page_text("https://example.com") == (
        "(page has no visible text)"
    )


def test_get_links_formats_text_and_limits_results(monkeypatch, playwright_available):
    class Page:
        def goto(self, _url, **_kwargs):
            pass

        def eval_on_selector_all(self, selector, _script):
            assert selector == "a[href]"
            return [
                {"text": "First link", "href": "https://example.com/1"},
                {"text": "", "href": "https://example.com/2"},
            ]

        def close(self):
            pass

    class Playwright:
        def stop(self):
            pass

    monkeypatch.setattr(browser_skill, "open_page", lambda: (Playwright(), Page()))

    assert browser_skill.get_links("https://example.com", "1") == (
        "First link -> https://example.com/1"
    )


def test_get_links_reports_when_page_has_no_links(monkeypatch, playwright_available):
    class Page:
        def goto(self, _url, **_kwargs):
            pass

        def eval_on_selector_all(self, _selector, _script):
            return []

        def close(self):
            pass

    class Playwright:
        def stop(self):
            pass

    monkeypatch.setattr(browser_skill, "open_page", lambda: (Playwright(), Page()))

    assert browser_skill.get_links("https://example.com") == "(no links found)"


def test_screenshot_saves_to_workspace_with_requested_page_size(
    monkeypatch, tmp_path, playwright_available
):
    calls = []

    class Page:
        def goto(self, _url, **_kwargs):
            pass

        def screenshot(self, **kwargs):
            calls.append(("screenshot", kwargs))

        def close(self):
            calls.append(("close_page",))

    class Playwright:
        def stop(self):
            calls.append(("stop",))

    monkeypatch.setattr(browser_skill, "open_page", lambda: (Playwright(), Page()))
    monkeypatch.setattr(browser_skill, "WORKSPACE", tmp_path)
    monkeypatch.setattr(browser_skill, "_safe_filename", lambda _url: "shot.png")

    assert browser_skill.screenshot("https://example.com", "false") == (
        "Saved screenshot to workspace/shot.png"
    )
    assert calls == [
        ("screenshot", {"path": str(tmp_path / "shot.png"), "full_page": False}),
        ("close_page",),
        ("stop",),
    ]


def test_browser_tools_report_missing_playwright(monkeypatch):
    original_import = builtins.__import__

    def import_without_playwright(name, *args, **kwargs):
        if name == "playwright.sync_api":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_playwright)

    assert browser_skill.navigate("https://example.com") == (
        browser_skill._missing_playwright()
    )
    assert browser_skill.get_page_text("https://example.com") == (
        browser_skill._missing_playwright()
    )
    assert browser_skill.get_links("https://example.com") == (
        browser_skill._missing_playwright()
    )
    assert browser_skill.screenshot("https://example.com") == (
        browser_skill._missing_playwright()
    )


@pytest.mark.parametrize(
    "name, function",
    [
        ("navigate", browser_skill.navigate),
        ("get_page_text", browser_skill.get_page_text),
        ("get_links", browser_skill.get_links),
        ("screenshot", browser_skill.screenshot),
    ],
)
def test_browser_tools_are_registered_as_non_dangerous(name, function):
    tool = registry.get(name)

    assert tool.func is function
    assert tool.dangerous is False
