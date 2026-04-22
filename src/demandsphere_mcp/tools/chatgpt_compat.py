"""ChatGPT Deep Research compatibility (search/fetch tools)."""

from __future__ import annotations

import hashlib
from collections import OrderedDict

from mcp.server.fastmcp import FastMCP

from .utils import safe_tool

# LRU-bounded cache. Prevents memory leak in long-running HTTP deployments.
_CACHE_MAX_SIZE = 1000


class _LRUCache:
    """Simple LRU cache with max size eviction."""

    def __init__(self, max_size: int = _CACHE_MAX_SIZE) -> None:
        self._data: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> dict | None:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key: str, value: dict) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self._max_size:
            self._data.popitem(last=False)


_record_cache = _LRUCache()


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @safe_tool
    async def search(query: str) -> dict:
        """Search DemandSphere data. Returns record IDs for use with fetch(). Covers keywords, AI mentions, citations, LLM traffic, PAA."""
        query_lower = query.lower()
        ids: list[str] = []

        _ROUTES = [
            (
                [
                    "ranking",
                    "keyword",
                    "serp",
                    "position",
                    "rank",
                    "performance",
                    "traffic",
                    "search volume",
                ],
                "keyword_performance",
                "Keyword ranking data. Use serp_analytics(view='performance') for full results.",
            ),
            (
                [
                    "mention",
                    "cited",
                    "citation",
                    "ai",
                    "chatgpt",
                    "gemini",
                    "perplexity",
                    "genai",
                    "brand",
                ],
                "mentions",
                "AI mention/citation data. Use get_mentions or get_site_citations for full results.",
            ),
            (
                ["traffic", "visits", "llm", "analytics", "channel", "conversion", "bounce"],
                "llm_traffic",
                "LLM traffic analytics. Use llm_analytics(view='stats') or llm_analytics(view='cross_llms') for full results.",
            ),
            (
                ["people also ask", "paa", "question", "faq"],
                "paa",
                "People Also Ask data. Use get_people_also_ask for full results.",
            ),
            (
                ["landing", "page", "match", "mismatch", "cannibalization"],
                "landing_matches",
                "Landing page match analysis. Use get_landing_matches for full results.",
            ),
        ]

        for keywords, record_type, description in _ROUTES:
            if any(kw in query_lower for kw in keywords):
                rid = _make_id(record_type, query)
                _record_cache.put(
                    rid, {"type": record_type, "query": query, "description": description}
                )
                ids.append(rid)

        if not ids:
            rid = _make_id("general", query)
            _record_cache.put(
                rid,
                {
                    "type": "general",
                    "query": query,
                    "description": "No specific match. Try queries about rankings, AI mentions, LLM traffic, or PAA questions.",
                },
            )
            ids.append(rid)

        return {
            "ids": ids,
            "hints": [
                "Use fetch(record_id) to get details for each returned ID.",
                "For direct data access, use the specific tool mentioned in each record's description.",
            ],
        }

    @mcp.tool()
    @safe_tool
    async def fetch(record_id: str) -> dict:
        """Fetch a record by ID from a previous search() call."""
        record = _record_cache.get(record_id)
        if record:
            return {
                "id": record_id,
                **record,
                "hints": [
                    "Use the specific tool mentioned in the description for full results.",
                ],
            }
        return {"id": record_id, "error": "Not found. Try searching again."}


def _make_id(record_type: str, query: str) -> str:
    h = hashlib.sha256(query.encode()).hexdigest()[:12]
    return f"ds:{record_type}:{h}"
