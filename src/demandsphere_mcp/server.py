"""DemandSphere MCP Server."""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from .client import DSClient
from .config import settings
from .tools import brands_v51, chatgpt_compat, genai_v51, keywords_v50, sites

logger = logging.getLogger("demandsphere_mcp")


# ── Server instructions ───────────────────────────────────────────────
# Loaded ONCE per session. Educational context lives here instead of
# in per-tool docstrings (which multiply across 27 tools).

_INSTRUCTIONS = """\
DemandSphere search intelligence platform.

WORKFLOW:
1. list_sites or list_sites_flat → get site IDs
2. SERP tools → rankings, trends, search engine comparison (v5.0)
3. GenAI tools → AI mentions, citations, LLM traffic (v5.1)
4. Brand tools → manage tracked brands for GenAI visibility

PARAMETERS:
- global_key: site's global key string (used by get_keyword_performance, v5.1 brand tools)
- site_id: site's ID string (used by other v5.0 tools)
- site_global_key: same as global_key (used by v5.1 genai/LLM tools in URL path)
  All three come from list_sites results.
- search_engine: google_us, google_japan, bing_uk, yahoo_us, etc.
  AI platforms (v5.1 only): chatgpt_us, perplexity, gemini
  Mobile variants: google_us__iphone, google_japan__nexus5
- Dates: always YYYY-MM-DD
- granularity: daily (default), weekly, monthly
- order: asc (default) or desc
- grouped: set True to aggregate by keyword tag/group
- metric (LLM analytics): visits, page_views, new_visits, bounces, conversions, value
- llms_list/channels_list: comma-separated filters for LLM analytics

SORT OPTIONS:
- Keywords: keyword_name, rank, rank_change, search_volume, projected_mo_traffic, clicks, impressions, average_position, ctr
- Groups: tag_name, keywords_count, bucket0-bucket8, search_volume, projected_mo_traffic
- Landing matches: keyword_name, rank, rank_change, search_volume, landing_match

PAGINATION:
- v5.0: limit + page_num (default limit=25)
- v5.1: page_number + page_limit (default 10)
- Bulk citations: max 50 keywords per call

TOOL CATEGORIES:
- Sites: list_sites, list_sites_flat
- SERP: get_keyword_performance, get_keyword_groups, get_ranking_trends, get_search_engine_comparison, get_local_rankings, get_landing_matches, get_landings_history, get_search_engine_summary
- GenAI: get_mentions, get_keyword_citations, get_bulk_citations, get_site_citations, get_llm_stats, get_llm_performance_summary, get_channels_performance_summary, get_cross_channel_overview, get_cross_llms_overview, get_llm_filters, get_people_also_ask
- Brands: list_brands, create_brand, update_brand, delete_brands
- Search: search, fetch (ChatGPT Deep Research compatibility)
"""

# Lazy singleton — not created at import time (#7)
_server: FastMCP | None = None


def _check_config() -> None:
    if settings.transport == "stdio" and not settings.api_key:
        print(
            "ERROR: DEMANDSPHERE_API_KEY is not set.\n"
            "Set via env var, ~/.config/demandsphere/config.json, or .env file.\n",
            file=sys.stderr,
        )
        sys.exit(1)


def create_server() -> FastMCP:
    """Create and configure the MCP server with all tools registered.

    Safe to call from tests and external code — does not call sys.exit.
    """
    mcp = FastMCP("demandsphere", instructions=_INSTRUCTIONS)
    client = DSClient()

    sites.register(mcp, client)
    keywords_v50.register(mcp, client)
    genai_v51.register(mcp, client)
    brands_v51.register(mcp, client)
    chatgpt_compat.register(mcp, client)

    return mcp


def _get_server() -> FastMCP:
    """Lazy singleton accessor."""
    global _server
    if _server is None:
        _check_config()
        _server = create_server()
    return _server


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,  # Never stdout — would corrupt stdio transport
    )

    server = _get_server()

    if settings.transport == "streamable-http":
        logger.info("Starting DemandSphere MCP (HTTP) on %s:%d", settings.host, settings.port)
        server.run(transport="streamable-http", host=settings.host, port=settings.port)
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
