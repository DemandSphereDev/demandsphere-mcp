"""Keyword and ranking tools (v5.0 API).

Note on identifiers: The DS API uses two different site identifiers.
- ``global_key``: The site's global key string (used by keyword_performance)
- ``site_id``: The site's ID string (used by all other v5.0 endpoints)
Both are returned by list_sites. The parameter names here match the DS API.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import DSClient
from .utils import safe_tool, clamp_limit, validate_date_range


def register(mcp: FastMCP, client: DSClient) -> None:

    @mcp.tool()
    @safe_tool
    async def get_keyword_performance(
        global_key: str,
        search_engine: str,
        from_date: str,
        to_date: str,
        sort_by: str = "keyword_name",
        order: str = "asc",
        granularity: str = "daily",
        limit: int = 25,
        page_num: int = 1,
    ) -> dict:
        """Per-keyword rank, rank change, page URL, search volume, traffic, clicks, impressions, CTR, SERP features."""
        limit = clamp_limit(limit)
        validate_date_range(from_date, to_date)
        raw = await client.post(
            "/keywords/keywords_performance_detail/list",
            params={
                "global_key": global_key,
                "search_engines": search_engine,
                "from": from_date,
                "to": to_date,
                "sort_by": sort_by,
                "order": order,
                "granularity": granularity,
                "limit": limit,
                "page_num": page_num,
            },
        )
        return client.shape_tabular(raw)

    @mcp.tool()
    @safe_tool
    async def get_keyword_groups(
        site_id: str,
        search_engine: str,
        from_date: str,
        to_date: str,
        sort_by: str = "tag_name",
        order: str = "asc",
        granularity: str = "daily",
        limit: int = 25,
        page_num: int = 1,
    ) -> dict:
        """Keyword group/tag performance with ranking bucket distribution (bucket0-bucket8), volume, traffic, CTR."""
        limit = clamp_limit(limit)
        validate_date_range(from_date, to_date)
        raw = await client.post(
            "/keywords/keyword_groups_detail/list",
            params={
                "site_id": site_id,
                "search_engines": search_engine,
                "from": from_date,
                "to": to_date,
                "sort_by": sort_by,
                "order": order,
                "granularity": granularity,
                "limit": limit,
                "page_num": page_num,
            },
        )
        return client.shape_tabular(raw)

    @mcp.tool()
    @safe_tool
    async def get_ranking_trends(
        site_id: str,
        search_engine: str,
        from_date: str,
        to_date: str,
        sort_by: str = "keyword_name",
        order: str = "asc",
        granularity: str = "daily",
        grouped: bool = False,
        limit: int = 25,
        page_num: int = 1,
    ) -> dict:
        """Ranking position history over time. Set grouped=True to aggregate by keyword tag."""
        limit = clamp_limit(limit)
        validate_date_range(from_date, to_date)
        params: dict = {
            "site_id": site_id,
            "search_engines": search_engine,
            "from": from_date,
            "to": to_date,
            "sort_by": sort_by,
            "order": order,
            "granularity": granularity,
            "limit": limit,
            "page_num": page_num,
        }
        if grouped:
            params["grouped"] = "true"
        raw = await client.post("/keywords/ranking_trends/list", params=params)
        return client.shape_tabular(raw)

    @mcp.tool()
    @safe_tool
    async def get_search_engine_comparison(
        site_id: str,
        search_engine: str,
        from_date: str,
        to_date: str,
        sort_by: str = "keyword_name",
        order: str = "asc",
        granularity: str = "daily",
        grouped: bool = False,
        limit: int = 25,
        page_num: int = 1,
    ) -> dict:
        """Compare keyword rankings across search engines. Pass multiple engines comma-separated."""
        limit = clamp_limit(limit)
        validate_date_range(from_date, to_date)
        params: dict = {
            "site_id": site_id,
            "search_engines": search_engine,
            "from": from_date,
            "to": to_date,
            "sort_by": sort_by,
            "order": order,
            "granularity": granularity,
            "limit": limit,
            "page_num": page_num,
        }
        if grouped:
            params["grouped"] = "true"
        raw = await client.post("/keywords/search_engines/list", params=params)
        return client.shape_tabular(raw)

    @mcp.tool()
    @safe_tool
    async def get_local_rankings(
        site_id: str,
        search_engine: str,
        from_date: str,
        to_date: str,
        order: str = "asc",
        granularity: str = "daily",
        limit: int = 25,
        page_num: int = 1,
    ) -> dict:
        """Local search rankings with per-location rank history."""
        limit = clamp_limit(limit)
        validate_date_range(from_date, to_date)
        raw = await client.post(
            "/keywords/local_rankings/list",
            params={
                "site_id": site_id,
                "search_engines": search_engine,
                "from": from_date,
                "to": to_date,
                "sort_by": "keyword_name",
                "order": order,
                "granularity": granularity,
                "limit": limit,
                "page_num": page_num,
            },
        )
        return client.shape_tabular(raw)

    @mcp.tool()
    @safe_tool
    async def get_landing_matches(
        site_id: str,
        search_engine: str,
        from_date: str,
        to_date: str,
        sort_by: str = "keyword_name",
        order: str = "asc",
        granularity: str = "daily",
        limit: int = 25,
        page_num: int = 1,
    ) -> dict:
        """Check if ranking pages match preferred landing pages. Returns match/mismatch/none status."""
        limit = clamp_limit(limit)
        validate_date_range(from_date, to_date)
        raw = await client.post(
            "/keywords/landing_matches/list",
            params={
                "site_id": site_id,
                "search_engines": search_engine,
                "from": from_date,
                "to": to_date,
                "sort_by": sort_by,
                "order": order,
                "granularity": granularity,
                "limit": limit,
                "page_num": page_num,
            },
        )
        return client.shape_tabular(raw)

    @mcp.tool()
    @safe_tool
    async def get_landings_history(
        site_id: str,
        search_engine: str,
        keyword_id: str,
        from_date: str,
        to_date: str,
    ) -> dict:
        """Landing page history for a specific keyword. Shows which page ranked on each date."""
        validate_date_range(from_date, to_date)
        raw = await client.post(
            "/pages/landings_history/list",
            params={
                "site_id": site_id,
                "search_engines": search_engine,
                "keyword_id": keyword_id,
                "from": from_date,
                "to": to_date,
            },
        )
        return client.shape_tabular(raw)

    @mcp.tool()
    @safe_tool
    async def get_search_engine_summary(
        site_id: str,
        search_engine: str,
        from_date: str,
        to_date: str,
        granularity: str = "daily",
    ) -> dict:
        """High-level summary per search engine: aggregate rank, visits, conversions, revenue."""
        validate_date_range(from_date, to_date)
        raw = await client.post(
            "/search_engines/summary/list",
            params={
                "site_id": site_id,
                "search_engines": search_engine,
                "from": from_date,
                "to": to_date,
                "granularity": granularity,
            },
        )
        return client.shape_tabular(raw)
