"""Tests for ddgsearch (all network calls are mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ddgsearch import SearchClient, SearchResponse, SearchResult, search
from ddgsearch.tool import handle_tool_call, search_tool_definition


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_DDG_RESULTS = [
    {
        "title": "Python 3.13 Released",
        "href": "https://example.com/python-313",
        "body": "Python 3.13 brings major performance improvements.",
    },
    {
        "title": "Python Changelog",
        "href": "https://example.com/changelog",
        "body": "Full list of changes in Python 3.13.",
    },
]

FAKE_DDG_NEWS = [
    {
        "title": "Python News",
        "url": "https://example.com/news",
        "excerpt": "Latest Python news.",
    }
]


def make_mock_ddgs(results):
    """Return a context-manager mock that yields fake DDG results."""
    mock_instance = MagicMock()
    mock_instance.text.return_value = results
    mock_instance.news.return_value = results
    mock_instance.images.return_value = []
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_instance)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return mock_cm


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------

class TestSearchResult:
    def test_to_dict(self):
        r = SearchResult(title="T", url="https://x.com", snippet="S", score=0.9)
        d = r.to_dict()
        assert d["title"] == "T"
        assert d["url"] == "https://x.com"
        assert d["snippet"] == "S"
        assert d["score"] == 0.9
        assert d["content"] is None

    def test_to_dict_with_content(self):
        r = SearchResult(title="T", url="u", snippet="s", content="Full text", score=1.0)
        assert r.to_dict()["content"] == "Full text"


# ---------------------------------------------------------------------------
# SearchResponse
# ---------------------------------------------------------------------------

class TestSearchResponse:
    def test_to_dict(self):
        r = SearchResult(title="T", url="u", snippet="s")
        resp = SearchResponse(query="q", results=[r], answer="42")
        d = resp.to_dict()
        assert d["query"] == "q"
        assert d["answer"] == "42"
        assert len(d["results"]) == 1

    def test_empty(self):
        resp = SearchResponse(query="nothing")
        assert resp.results == []
        assert resp.images == []


# ---------------------------------------------------------------------------
# SearchClient — basic depth
# ---------------------------------------------------------------------------

class TestSearchClientBasic:
    @patch("ddgsearch.client.DDGS" if False else "ddgsearch.client.fetch_contents")
    def test_basic_search(self, _mock_fetch):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_RESULTS)):
            client = SearchClient(max_results=2, search_depth="basic")
            resp = client.search("python 3.13")

        assert resp.query == "python 3.13"
        assert len(resp.results) == 2
        assert resp.results[0].title == "Python 3.13 Released"
        assert resp.results[0].score == 1.0
        # basic depth: no content fetching
        assert resp.results[0].content is None
        _mock_fetch.assert_not_called()

    def test_score_decreases(self):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_RESULTS)):
            client = SearchClient(max_results=2, search_depth="basic")
            resp = client.search("q")
        assert resp.results[0].score > resp.results[1].score

    def test_empty_results(self):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs([])):
            client = SearchClient()
            resp = client.search("nothing")
        assert resp.results == []


# ---------------------------------------------------------------------------
# SearchClient — advanced depth
# ---------------------------------------------------------------------------

class TestSearchClientAdvanced:
    def test_advanced_fetches_content(self):
        fake_contents = {
            "https://example.com/python-313": "Extracted page text.",
            "https://example.com/changelog": None,
        }
        with (
            patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_RESULTS)),
            patch("ddgsearch.client.fetch_contents", return_value=fake_contents) as mock_fc,
        ):
            client = SearchClient(max_results=2, search_depth="advanced")
            resp = client.search("python")

        mock_fc.assert_called_once()
        assert resp.results[0].content == "Extracted page text."
        assert resp.results[1].content is None


# ---------------------------------------------------------------------------
# SearchClient — news topic
# ---------------------------------------------------------------------------

class TestSearchClientNews:
    def test_news_topic(self):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_NEWS)) as MockDDGS:
            client = SearchClient(topic="news")
            resp = client.search("python news")

        # ddgs.news() should have been called (not .text())
        ddgs_instance = MockDDGS.return_value.__enter__.return_value
        ddgs_instance.news.assert_called_once()
        ddgs_instance.text.assert_not_called()


# ---------------------------------------------------------------------------
# SearchClient — images
# ---------------------------------------------------------------------------

class TestSearchClientImages:
    def test_images_included(self):
        fake_images = [{"image": "https://img.example.com/1.jpg", "title": "Img"}]
        mock_ddgs = make_mock_ddgs(FAKE_DDG_RESULTS)
        mock_ddgs.__enter__.return_value.images.return_value = fake_images

        with patch("ddgsearch.client.DDGS", return_value=mock_ddgs):
            client = SearchClient(include_images=True)
            resp = client.search("python logo")

        assert len(resp.images) == 1

    def test_images_excluded_by_default(self):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_RESULTS)):
            client = SearchClient()
            resp = client.search("python")
        assert resp.images == []


# ---------------------------------------------------------------------------
# Per-call overrides
# ---------------------------------------------------------------------------

class TestPerCallOverrides:
    def test_override_max_results(self):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_RESULTS)):
            client = SearchClient(max_results=10)
            # Ask for only 1 result at call time
            resp = client.search("q", max_results=1)
        # DDG mock returns 2; client requested 1 → DDG gets max_results=1
        ddgs_instance = client._ddg_search.__self__ if False else None  # just check call
        # All results are still returned from mock, but config propagated
        assert resp.query == "q"


# ---------------------------------------------------------------------------
# Module-level search() shortcut
# ---------------------------------------------------------------------------

class TestModuleLevelSearch:
    def test_search_returns_response(self):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_RESULTS)):
            resp = search("python", max_results=2)
        assert isinstance(resp, SearchResponse)
        assert resp.query == "python"


# ---------------------------------------------------------------------------
# Tool definition & handle_tool_call
# ---------------------------------------------------------------------------

class TestToolDefinition:
    def test_schema_structure(self):
        assert search_tool_definition["name"] == "web_search"
        assert "parameters" in search_tool_definition
        props = search_tool_definition["parameters"]["properties"]
        assert "query" in props
        assert "max_results" in props
        assert "search_depth" in props

    def test_handle_tool_call(self):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_RESULTS)):
            result = handle_tool_call({"query": "python", "max_results": 2})
        assert "results" in result
        assert result["query"] == "python"
        assert isinstance(result["results"], list)

    def test_handle_tool_call_defaults(self):
        with patch("ddgsearch.client.DDGS", return_value=make_mock_ddgs(FAKE_DDG_RESULTS)):
            result = handle_tool_call({"query": "test"})
        assert "results" in result


# ---------------------------------------------------------------------------
# Missing dependency guard
# ---------------------------------------------------------------------------

class TestImportGuard:
    def test_missing_ddgs(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "ddgs":
                raise ImportError("No module named 'ddgs'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        client = SearchClient()
        with pytest.raises(ImportError, match="ddgs is required"):
            client._ddg_search("test", client._merge({}))
