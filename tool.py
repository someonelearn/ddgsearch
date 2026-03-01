"""
Top-level convenience API and JSON tool definition for LLM tool-use protocols
(OpenAI function-calling, Anthropic tool-use, etc.).
"""

from __future__ import annotations

from typing import Any, Optional

from .client import SearchClient, SearchDepth, Topic
from .models import SearchResponse

# ---------------------------------------------------------------------------
# Module-level default client (lazy-initialised)
# ---------------------------------------------------------------------------

_default_client: Optional[SearchClient] = None


def _get_client() -> SearchClient:
    global _default_client
    if _default_client is None:
        _default_client = SearchClient()
    return _default_client


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def search(
    query: str,
    max_results: int = 5,
    search_depth: SearchDepth = "basic",
    topic: Topic = "general",
    include_images: bool = False,
    max_content_chars: int = 4000,
    region: str = "wt-wt",
    safesearch: str = "moderate",
) -> SearchResponse:
    """
    Search the web and return structured results suitable for LLM consumption.

    Parameters
    ----------
    query:
        Natural-language search query.
    max_results:
        Number of results to return (1–20).
    search_depth:
        ``"basic"`` → snippets only (fast).
        ``"advanced"`` → full page content extracted via trafilatura (slower).
    topic:
        ``"general"`` for normal web search or ``"news"`` for recent news.
    include_images:
        Include image results in the response.
    max_content_chars:
        Max characters of extracted content per result (``search_depth="advanced"``).
    region:
        DuckDuckGo region, e.g. ``"us-en"``, ``"uk-en"``.
    safesearch:
        ``"on"``, ``"moderate"``, or ``"off"``.

    Returns
    -------
    :class:`~ddgsearch.SearchResponse`
    """
    client = _get_client()
    return client.search(
        query,
        max_results=max_results,
        search_depth=search_depth,
        topic=topic,
        include_images=include_images,
        max_content_chars=max_content_chars,
        region=region,
        safesearch=safesearch,
    )


# ---------------------------------------------------------------------------
# LLM tool definitions
# ---------------------------------------------------------------------------

#: OpenAI / Anthropic-compatible JSON schema for the search function.
search_tool_definition: dict[str, Any] = {
    "name": "web_search",
    "description": (
        "Search the web for up-to-date information. "
        "Use this tool whenever you need current facts, recent events, "
        "product details, or any information that may have changed after "
        "your training cutoff."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string.",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (default 5, max 20).",
                "default": 5,
                "minimum": 1,
                "maximum": 20,
            },
            "search_depth": {
                "type": "string",
                "enum": ["basic", "advanced"],
                "description": (
                    "'basic' returns titles, URLs, and short snippets. "
                    "'advanced' also fetches and extracts full page content."
                ),
                "default": "basic",
            },
            "topic": {
                "type": "string",
                "enum": ["general", "news"],
                "description": "Search category. Use 'news' for recent news articles.",
                "default": "general",
            },
            "include_images": {
                "type": "boolean",
                "description": "Whether to include image results.",
                "default": False,
            },
        },
        "required": ["query"],
    },
}

#: Anthropic tool-use format (input_schema style).
search_tool_definition_anthropic: dict[str, Any] = {
    "name": "web_search",
    "description": search_tool_definition["description"],
    "input_schema": search_tool_definition["parameters"],
}


def handle_tool_call(tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a search from an LLM tool-call payload and return a serialisable dict.

    Parameters
    ----------
    tool_input:
        The ``input`` / ``arguments`` object parsed from the LLM's tool-call.

    Returns
    -------
    A plain dict suitable for serialising as the tool result.

    Example
    -------
    >>> result = handle_tool_call({"query": "latest Python release"})
    >>> print(result["results"][0]["title"])
    """
    response = search(
        query=tool_input["query"],
        max_results=tool_input.get("max_results", 5),
        search_depth=tool_input.get("search_depth", "basic"),
        topic=tool_input.get("topic", "general"),
        include_images=tool_input.get("include_images", False),
    )
    return response.to_dict()
