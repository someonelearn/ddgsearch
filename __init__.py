"""
ddgsearch — a Tavily-style web search tool for LLMs,
powered by DuckDuckGo (duckduckgo-search) and trafilatura.
"""

from .client import SearchClient
from .models import SearchResult, SearchResponse
from .tool import search, search_tool_definition

__all__ = [
    "SearchClient",
    "SearchResult",
    "SearchResponse",
    "search",
    "search_tool_definition",
]

__version__ = "0.1.0"
