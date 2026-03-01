"""Fetch and extract clean text from URLs using trafilatura."""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10  # seconds per URL
_TRAFILATURA_CONFIG = {
    "include_comments": False,
    "include_tables": True,
    "no_fallback": False,
    "favor_precision": False,
}


def _fetch_one(url: str, max_chars: int) -> Optional[str]:
    """Download *url* and return extracted plain text, or None on failure."""
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded,
            include_comments=_TRAFILATURA_CONFIG["include_comments"],
            include_tables=_TRAFILATURA_CONFIG["include_tables"],
            no_fallback=_TRAFILATURA_CONFIG["no_fallback"],
            favor_precision=_TRAFILATURA_CONFIG["favor_precision"],
        )
        if text and max_chars > 0:
            text = text[:max_chars]
        return text
    except Exception as exc:  # noqa: BLE001
        logger.debug("trafilatura failed for %s: %s", url, exc)
        return None


def fetch_contents(
    urls: list[str],
    max_chars: int = 4000,
    max_workers: int = 5,
) -> dict[str, Optional[str]]:
    """
    Concurrently fetch and extract text for a list of URLs.

    Parameters
    ----------
    urls:
        Target URLs to fetch.
    max_chars:
        Maximum characters to keep per page (0 = unlimited).
    max_workers:
        Thread-pool concurrency limit.

    Returns
    -------
    dict mapping each URL → extracted text (or None if extraction failed).
    """
    results: dict[str, Optional[str]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(_fetch_one, url, max_chars): url for url in urls
        }
        for future in concurrent.futures.as_completed(
            future_to_url, timeout=_FETCH_TIMEOUT * len(urls)
        ):
            url = future_to_url[future]
            try:
                results[url] = future.result(timeout=_FETCH_TIMEOUT)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Fetch timed out or errored for %s: %s", url, exc)
                results[url] = None

    return results
