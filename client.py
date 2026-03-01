"""SearchClient: orchestrates DuckDuckGo search + trafilatura extraction."""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from .fetcher import fetch_contents
from .models import SearchResponse, SearchResult

logger = logging.getLogger(__name__)

SearchDepth = Literal["basic", "advanced"]
Topic = Literal["general", "news"]


class SearchClient:
    """
    A Tavily-style search client backed by DuckDuckGo and trafilatura.

    Parameters
    ----------
    max_results:
        Number of search results to return (default: 5).
    search_depth:
        ``"basic"`` returns only snippets; ``"advanced"`` fetches and
        extracts full page content via trafilatura.
    topic:
        ``"general"`` for web search, ``"news"`` for news results.
    include_images:
        Whether to include image results in the response.
    max_content_chars:
        Maximum characters of extracted content per result (advanced only).
    fetch_workers:
        Thread-pool size used for concurrent page fetching.
    region:
        DuckDuckGo region code, e.g. ``"us-en"``, ``"uk-en"``, ``"de-de"``.
    safesearch:
        ``"on"``, ``"moderate"``, or ``"off"``.
    """

    def __init__(
        self,
        max_results: int = 5,
        search_depth: SearchDepth = "basic",
        topic: Topic = "general",
        include_images: bool = False,
        max_content_chars: int = 4000,
        fetch_workers: int = 5,
        region: str = "wt-wt",
        safesearch: str = "moderate",
    ) -> None:
        self.max_results = max_results
        self.search_depth = search_depth
        self.topic = topic
        self.include_images = include_images
        self.max_content_chars = max_content_chars
        self.fetch_workers = fetch_workers
        self.region = region
        self.safesearch = safesearch

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, **overrides) -> SearchResponse:
        """
        Run a search for *query* and return a :class:`SearchResponse`.

        Keyword overrides mirror the constructor parameters and apply only
        to this call.
        """
        cfg = self._merge(overrides)
        raw_results = self._ddg_search(query, cfg)
        results = self._build_results(raw_results, cfg)

        images: list[dict] = []
        if cfg["include_images"]:
            images = self._ddg_images(query, cfg)

        return SearchResponse(query=query, results=results, images=images)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _merge(self, overrides: dict) -> dict:
        """Return a config dict with per-call overrides applied."""
        return {
            "max_results": overrides.get("max_results", self.max_results),
            "search_depth": overrides.get("search_depth", self.search_depth),
            "topic": overrides.get("topic", self.topic),
            "include_images": overrides.get("include_images", self.include_images),
            "max_content_chars": overrides.get("max_content_chars", self.max_content_chars),
            "fetch_workers": overrides.get("fetch_workers", self.fetch_workers),
            "region": overrides.get("region", self.region),
            "safesearch": overrides.get("safesearch", self.safesearch),
        }

    def _ddg_search(self, query: str, cfg: dict) -> list[dict]:
        """Return raw DuckDuckGo text results."""
        try:
            from ddgs import DDGS
        except ImportError as exc:
            raise ImportError(
                "ddgs is required: pip install ddgs"
            ) from exc

        with DDGS() as ddgs:
            if cfg["topic"] == "news":
                raw = list(
                    ddgs.news(
                        query,
                        region=cfg["region"],
                        safesearch=cfg["safesearch"],
                        max_results=cfg["max_results"],
                    )
                )
            else:
                raw = list(
                    ddgs.text(
                        query,
                        region=cfg["region"],
                        safesearch=cfg["safesearch"],
                        max_results=cfg["max_results"],
                    )
                )
        return raw

    def _ddg_images(self, query: str, cfg: dict) -> list[dict]:
        """Return raw DuckDuckGo image results."""
        try:
            from ddgs import DDGS
        except ImportError:
            return []

        try:
            with DDGS() as ddgs:
                return list(
                    ddgs.images(
                        query,
                        region=cfg["region"],
                        safesearch=cfg["safesearch"],
                        max_results=cfg["max_results"],
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Image search failed: %s", exc)
            return []

    def _build_results(self, raw: list[dict], cfg: dict) -> list[SearchResult]:
        """Convert raw DDG hits → SearchResult objects, optionally fetching content."""
        if not raw:
            return []

        # Positional relevance score: first result = 1.0, last ≈ 0.0
        total = len(raw)

        results: list[SearchResult] = []
        for i, item in enumerate(raw):
            score = round(1.0 - (i / max(total, 1)) * 0.9, 4)
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("href") or item.get("url", ""),
                    snippet=item.get("body") or item.get("excerpt", ""),
                    score=score,
                )
            )

        if cfg["search_depth"] == "advanced":
            urls = [r.url for r in results if r.url]
            contents = fetch_contents(
                urls,
                max_chars=cfg["max_content_chars"],
                max_workers=cfg["fetch_workers"],
            )
            for result in results:
                result.content = contents.get(result.url)

        return results
