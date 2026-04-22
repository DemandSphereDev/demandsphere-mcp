"""MCP Resources for parameter discovery and site enumeration."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ..client import DSClient


def register(mcp: FastMCP, client: DSClient) -> None:
    # ── Static parameter enumerations ──────────────────────────────────

    @mcp.resource(
        "data://search-engines",
        name="search-engines",
        description="Available search engine codes for the search_engine parameter.",
    )
    def search_engines() -> str:
        return json.dumps(
            {
                "standard": [
                    "google_us",
                    "google_uk",
                    "google_au",
                    "google_ca",
                    "google_de",
                    "google_fr",
                    "google_es",
                    "google_it",
                    "google_japan",
                    "bing_us",
                    "bing_uk",
                    "yahoo_us",
                    "yahoo_japan",
                ],
                "ai_platforms": [
                    "chatgpt_us",
                    "gemini_us",
                    "perplexity_us",
                ],
                "mobile_variants": [
                    "google_us__iphone",
                    "google_us__nexus5",
                    "google_uk__iphone",
                    "google_japan__iphone",
                    "google_japan__nexus5",
                ],
                "note": (
                    "Use with search_engine parameter in SERP and GenAI tools. "
                    "AI platforms are only valid for v5.1 GenAI tools (get_mentions, citations, etc.)."
                ),
            }
        )

    @mcp.resource(
        "data://sort-options",
        name="sort-options",
        description="Valid sort_by values per tool category.",
    )
    def sort_options() -> str:
        return json.dumps(
            {
                "keyword_performance": [
                    "keyword_name",
                    "rank",
                    "rank_change",
                    "search_volume",
                    "projected_mo_traffic",
                    "clicks",
                    "impressions",
                    "average_position",
                    "ctr",
                ],
                "keyword_groups": [
                    "tag_name",
                    "keywords_count",
                    "bucket0",
                    "bucket1",
                    "bucket2",
                    "bucket3",
                    "bucket4",
                    "bucket5",
                    "bucket6",
                    "bucket7",
                    "bucket8",
                    "search_volume",
                    "projected_mo_traffic",
                ],
                "landing_matches": [
                    "keyword_name",
                    "rank",
                    "rank_change",
                    "search_volume",
                    "landing_match",
                ],
                "note": "Use with sort_by parameter. Defaults: keyword_name (keywords), tag_name (groups).",
            }
        )

    @mcp.resource(
        "data://granularity",
        name="granularity",
        description="Valid granularity values for time-series data.",
    )
    def granularity() -> str:
        return json.dumps(
            {
                "values": ["daily", "weekly", "monthly"],
                "default": "daily",
                "note": "Use with granularity parameter in SERP and ranking tools.",
            }
        )

    @mcp.resource(
        "data://metrics",
        name="metrics",
        description="Valid metric values for LLM analytics tools.",
    )
    def metrics() -> str:
        return json.dumps(
            {
                "values": [
                    "visits",
                    "page_views",
                    "new_visits",
                    "bounces",
                    "conversions",
                    "value",
                ],
                "default": "visits",
                "note": (
                    "Use with metric parameter in llm_analytics "
                    "(views: performance, channels, cross_channel, cross_llms)."
                ),
            }
        )

    # ── Dynamic site discovery ─────────────────────────────────────────

    @mcp.resource(
        "data://sites",
        name="sites",
        description="Available sites with IDs, global keys, names, and URLs.",
    )
    async def sites() -> str:
        raw = await client.post("/sites/hierarchy/list")
        site_list = raw.get("hierarchyList", raw)
        return json.dumps(
            {
                "sites": site_list,
                "note": (
                    "Use 'id' as site_id for v5.0 SERP tools. "
                    "Use 'global_key' as site_global_key for v5.1 GenAI and brand tools, "
                    "and as global_key for serp_analytics(view='performance')."
                ),
            }
        )
