from io import BytesIO

from skills import registry, web_search_skill


def test_open_web_page_returns_readable_text(monkeypatch):
    html = b"""
    <html><head><title>Ignored</title><script>alert(1)</script></head>
    <body><h1>Example</h1><p>Hello <b>world</b>.</p></body></html>
    """
    monkeypatch.setattr(web_search_skill, "_validate_url", lambda url: url)
    monkeypatch.setattr(
        web_search_skill,
        "urlopen",
        lambda *_args, **_kwargs: BytesIO(html),
    )
    monkeypatch.setattr(
        web_search_skill,
        "_llm_tldr",
        lambda _text: "Example Hello world.",
    )

    result = web_search_skill.open_web_page("https://example.com")

    assert result == (
        "## Web page\n\n"
        "**Source:** https://example.com\n\n"
        "**TL;DR:** Example Hello world.\n\n"
        "**Page content:**\n"
        "- Example\n"
        "- Hello world."
    )


def test_open_web_page_limits_tldr_length(monkeypatch):
    text = "This is the first sentence. " + ("Long detail " * 100)

    def fail(_text):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(web_search_skill, "_llm_tldr", fail)
    summary = web_search_skill._tldr(text)

    assert len(summary) <= web_search_skill._MAX_TLDR_LENGTH
    assert summary.startswith("This is the first sentence.")


def test_tldr_uses_configured_llm(monkeypatch):
    monkeypatch.setattr(
        web_search_skill,
        "_llm_tldr",
        lambda text: "LLM summary.",
    )

    assert web_search_skill._tldr("Long webpage text.") == "LLM summary."


def test_tldr_falls_back_when_llm_fails(monkeypatch):
    def fail(_text):
        raise RuntimeError("Ollama is unavailable")

    monkeypatch.setattr(web_search_skill, "_llm_tldr", fail)

    assert web_search_skill._tldr("First sentence. Second sentence.") == (
        "First sentence. Second sentence."
    )


def test_open_web_page_rejects_non_http_urls():
    result = web_search_skill.open_web_page("file:///etc/passwd")

    assert result == "Error: could not open web page: url must be an absolute HTTP(S) URL"


def test_search_web_supports_multiple_types(monkeypatch):
    calls = []

    class FakeDDGS:
        def text(self, query, max_results):
            calls.append(("text", query, max_results))
            return [{"title": "Text result", "body": "A text result.", "href": "https://example.com"}]

        def news(self, query, max_results):
            calls.append(("news", query, max_results))
            return [{"title": "News result", "date": "today", "url": "https://news.example.com"}]

        def images(self, query, max_results):
            calls.append(("images", query, max_results))
            return [{"title": "Image result", "image": "https://img.example.com/a.jpg"}]

        def videos(self, query, max_results):
            calls.append(("videos", query, max_results))
            return [{"title": "Video result", "description": "A video.", "content": "https://video.example.com"}]

    monkeypatch.setattr(web_search_skill, "DDGS", FakeDDGS)

    result = web_search_skill.search_web("rose assistant")

    assert "## Text search results" in result
    assert "**Query:** `rose assistant`" in result
    assert "**Results:** 1" in result
    assert "1. **Text result**" in result
    assert "- A text result." in result
    assert "- Link: https://example.com" in result

    assert "## News search results" in web_search_skill.search_web("rose assistant", "news")
    assert "## Image search results" in web_search_skill.search_web("rose assistant", "images")
    assert "## Video search results" in web_search_skill.search_web("rose assistant", "videos")
    assert [call[0] for call in calls] == ["text", "news", "images", "videos"]


def test_search_web_validates_type_and_query(monkeypatch):
    assert web_search_skill.search_web("") == "Error: search query must not be empty."
    assert "search_type must be one of:" in web_search_skill.search_web("hello", "maps")
    monkeypatch.setattr(web_search_skill, "DDGS", lambda: (_ for _ in ()).throw(AssertionError))


def test_search_tools_are_registered_as_read_only():
    assert registry.get("open_web_page").dangerous is False
    assert registry.get("search_web").dangerous is False
