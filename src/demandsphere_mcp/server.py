"""DemandSphere MCP Server."""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette

from .client import DSClient, set_default_client
from .config import settings
from .tools import brands_v51, chatgpt_compat, genai_v51, keywords_v50, prompts, resources, sites

logger = logging.getLogger("demandsphere_mcp")


# ── Server instructions ───────────────────────────────────────────────
# Loaded ONCE per session. Educational context lives here instead of
# in per-tool docstrings (which multiply across 20 tools).

_INSTRUCTIONS = """\
DemandSphere search intelligence platform.

WORKFLOW:
1. list_sites or list_sites_flat → get site IDs
2. SERP tools → rankings, trends, search engine comparison (v5.0)
3. GenAI tools → AI mentions, citations, LLM traffic (v5.1)
4. Brand tools → manage tracked brands for GenAI visibility

PARAMETERS:
- global_key: site's global key string (used by serp_analytics view='performance', v5.1 brand tools)
- site_id: site's ID string (used by other v5.0 tools)
- site_global_key: same as global_key (used by v5.1 genai/LLM tools in URL path)
  All three come from list_sites results.
- search_engine: google_us, google_japan, bing_uk, yahoo_us, etc.
  AI platforms (v5.1 only): chatgpt_us, perplexity, gemini
  Mobile variants: google_us__iphone, google_japan__nexus5
- Dates: always YYYY-MM-DD
- granularity: daily (default), weekly, monthly
- order: asc (default) or desc
- grouped: set True to aggregate by keyword tag/group (serp_analytics views: trends, engine_comparison)
- metric (llm_analytics): visits, page_views, new_visits, bounces, conversions, value
- llms_list/channels_list: comma-separated filters for llm_analytics views: stats, performance

SORT OPTIONS:
- serp_analytics: keyword_name, rank, rank_change, search_volume, projected_mo_traffic, clicks, impressions, average_position, ctr
- Groups: tag_name, keywords_count, bucket0-bucket8, search_volume, projected_mo_traffic
- Landing matches: keyword_name, rank, rank_change, search_volume, landing_match

PAGINATION:
- v5.0: limit + page_num (default limit=25)
- v5.1: page_number + page_limit (default 10)
- Bulk citations: max 50 keywords per call

TOOL CATEGORIES:
- Sites: list_sites, list_sites_flat
- SERP: serp_analytics (views: performance, trends, engine_comparison, engine_summary), get_keyword_groups, get_local_rankings, get_landing_matches, get_landings_history
- GenAI: get_mentions, get_keyword_citations, get_bulk_citations, get_site_citations, llm_analytics (views: stats, performance, channels, cross_channel, cross_llms), get_llm_filters, get_people_also_ask
- Brands: list_brands, create_brand, update_brand, delete_brands
- Search: search, fetch (ChatGPT Deep Research compatibility)
"""


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
    Callers are responsible for installing a default DSClient via
    ``set_default_client()`` (stdio / single-tenant) or arranging per-request
    ContextVar population (hosted mode) before tools are invoked.
    """
    mcp = FastMCP("demandsphere", instructions=_INSTRUCTIONS)

    sites.register(mcp)
    keywords_v50.register(mcp)
    genai_v51.register(mcp)
    brands_v51.register(mcp)
    chatgpt_compat.register(mcp)
    prompts.register(mcp)
    resources.register(mcp)

    return mcp


def create_asgi_app() -> Starlette:
    """Return the Starlette ASGI app for streamable HTTP transport.

    Use this when embedding the MCP inside a larger ASGI stack (e.g. the
    hosted gateway). The consuming app is responsible for installing auth
    middleware that populates the ``_current_client`` ContextVar per request.

    Intentionally does NOT call ``set_default_client()`` — relying on a
    default in hosted mode would mask a missing middleware wiring.
    """
    return create_server().streamable_http_app()


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,  # Never stdout — would corrupt stdio transport
    )

    _check_config()
    set_default_client(DSClient())
    server = create_server()

    if settings.transport == "streamable-http":
        logger.info(
            "Starting DemandSphere MCP (HTTP) on %s:%d",
            settings.host,
            settings.port,
        )
        server.run(
            transport="streamable-http",
            host=settings.host,
            port=settings.port,
        )
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
