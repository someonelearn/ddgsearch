# ddgsearch

A **Tavily-style web search tool for LLMs**, built on:

- 🦆 **[duckduckgo-search](https://github.com/deedy5/duckduckgo_search)** — privacy-friendly, no API key needed
- 📄 **[trafilatura](https://trafilatura.readthedocs.io/)** — fast, high-quality web content extraction

---

## Features

| Feature | Description |
|---|---|
| **Zero API key** | Uses DuckDuckGo — no account needed |
| **Two search depths** | `basic` (snippets) or `advanced` (full page text via trafilatura) |
| **News search** | Switch topic to `"news"` for recent articles |
| **Image results** | Optional image search |
| **LLM tool schemas** | Ready-to-use JSON schemas for OpenAI & Anthropic tool-use |
| **Concurrent fetching** | Thread-pool page extraction for speed |

---

## Installation

```bash
pip install ddgsearch
```

Or from source:

```bash
git clone https://github.com/yourname/ddgsearch
cd ddgsearch
pip install -e ".[dev]"
```

---

## Quick Start

```python
from ddgsearch import search

# Basic search — returns titles, URLs, snippets
response = search("latest Python release")

for result in response.results:
    print(f"[{result.score:.2f}] {result.title}")
    print(f"  {result.url}")
    print(f"  {result.snippet}\n")
```

```
[1.00] Python 3.13 Released
  https://www.python.org/downloads/release/python-3130/
  Python 3.13 features major performance improvements and a new REPL.

[0.78] What's New in Python 3.13
  https://docs.python.org/3/whatsnew/3.13.html
  A summary of all new features and changes in Python 3.13.
```

---

## Advanced — Full Page Extraction

```python
from ddgsearch import SearchClient

client = SearchClient(
    max_results=5,
    search_depth="advanced",   # fetches + extracts full page content
    max_content_chars=3000,    # truncate to first 3000 chars per page
)

response = client.search("how does RLHF work?")

for result in response.results:
    print(result.title)
    print(result.content[:500] if result.content else "(no content extracted)")
```

---

## LLM Tool Use

### OpenAI / function-calling

```python
import json
import openai
from ddgsearch import search_tool_definition
from ddgsearch.tool import handle_tool_call

client = openai.OpenAI()

messages = [{"role": "user", "content": "What happened in AI this week?"}]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=[{"type": "function", "function": search_tool_definition}],
)

tool_call = response.choices[0].message.tool_calls[0]
tool_input = json.loads(tool_call.function.arguments)

# Execute the search
result = handle_tool_call(tool_input)

# Feed result back to the model
messages.append(response.choices[0].message)
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": json.dumps(result),
})
```

### Anthropic / tool-use

```python
import anthropic
from ddgsearch.tool import search_tool_definition_anthropic, handle_tool_call

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    tools=[search_tool_definition_anthropic],
    messages=[{"role": "user", "content": "What is the latest news about fusion energy?"}],
)

# Handle tool-use block
for block in response.content:
    if block.type == "tool_use":
        result = handle_tool_call(block.input)
        print(result)
```

---

## API Reference

### `search(query, **kwargs) → SearchResponse`

Module-level convenience function using a shared default client.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | — | Search query |
| `max_results` | `int` | `5` | Number of results (1–20) |
| `search_depth` | `str` | `"basic"` | `"basic"` or `"advanced"` |
| `topic` | `str` | `"general"` | `"general"` or `"news"` |
| `include_images` | `bool` | `False` | Include image results |
| `max_content_chars` | `int` | `4000` | Max chars per page (advanced) |
| `region` | `str` | `"wt-wt"` | DuckDuckGo region code |
| `safesearch` | `str` | `"moderate"` | `"on"`, `"moderate"`, `"off"` |

### `SearchResponse`

```python
@dataclass
class SearchResponse:
    query: str
    results: list[SearchResult]
    answer: str | None          # reserved for future extractive QA
    images: list[dict]
```

### `SearchResult`

```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str                # DuckDuckGo summary blurb
    content: str | None         # Full extracted text (advanced only)
    score: float                # Positional relevance 0.0–1.0
```

---

## Running Tests

```bash
pytest tests/ -v
```

All tests mock network calls — no real HTTP requests are made.

---

## Architecture

```
ddgsearch/
├── __init__.py        # Public API surface
├── client.py          # SearchClient — orchestrates DDG + trafilatura
├── fetcher.py         # Concurrent URL fetching via trafilatura
├── models.py          # SearchResult, SearchResponse dataclasses
└── tool.py            # LLM tool schemas + handle_tool_call()
```

---

## License

MIT
