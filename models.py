"""Pydantic models for search results."""

from __future__ import annotations

from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """A single search result with extracted page content."""

    title: str
    url: str
    snippet: str  # DuckDuckGo summary
    content: Optional[str] = None  # Full text extracted by trafilatura
    score: float = 0.0  # Relevance score (0–1), positional heuristic

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content,
            "score": self.score,
        }


@dataclass
class SearchResponse:
    """The full response returned by :func:`search`."""

    query: str
    results: List[SearchResult] = field(default_factory=list)
    answer: Optional[str] = None  # Optional AI-style extracted answer
    images: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "answer": self.answer,
            "results": [r.to_dict() for r in self.results],
            "images": self.images,
        }
