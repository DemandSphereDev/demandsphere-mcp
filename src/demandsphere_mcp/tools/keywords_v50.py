"""Keyword and ranking tools (v5.0 API).

Note on identifiers: The DS API uses two different site identifiers.
- ``global_key``: The site's global key string (used by keyword_performance)
- ``site_id``: The site's ID string (used by all other v5.0 endpoints)
Both are returned by list_sites. The parameter names here match the DS API.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import DSClient
from .utils import safe_tool, clamp_limit, validate_date_range, build_hints, attach_hints


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
        result = client.shape_tabular(raw)
        hints = build_hints(
            total_count=result.get("total_count"),
            returned_count=result.get("returned_count"),
            truncated=result.get("truncated", False),
            page_num=page_num,
            limit=limit,
            extra=[
                "Use get_ranking_trends with site_id to see position history over time.",
                "Use get_landing_matches to check if the right pages are ranking.",
            ],
        )
        return attach_hints(result, hints)

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
        result = client.shape_tabular(raw)
        hints = build_hints(
            total_count=result.get("total_count"),
            returned_count=result.get("returned_count"),
            truncated=result.get("truncated", False),
            page_num=page_num,
            limit=limit,
            extra=[
                "Use get_ranking_trends with grouped=True to see rank trends by group.",
                "Use get_keyword_performance with global_key for per-keyword detail.",
            ],
        )
        return attach_hints(result, hints)

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
        result = client.shape_tabular(raw)
        extra = []
        if grouped:
            extra.append("Set grouped=False to see individual keyword trends.")
        else:
            extra.append("Set grouped=True to aggregate trends by keyword tag.")
        hints = build_hints(
            total_count=result.get("total_count"),
            returned_count=result.get("returned_count"),
            truncated=result.get("truncated", False),
            page_num=page_num,
            limit=limit,
            extra=extra,
        )
        return attach_hints(result, hints)

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
        result = client.shape_tabular(raw)
        hints = build_hints(
            total_count=result.get("total_count"),
            returned_count=result.get("returned_count"),
            truncated=result.get("truncated", False),
            page_num=page_num,
            limit=limit,
            extra=[
                "Pass multiple search engines comma-separated (e.g. 'google_us,bing_us') to compare.",
                "Use get_keyword_performance for detailed per-keyword metrics on a single engine.",
            ],
        )
        return attach_hints(result, hints)

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
        result = client.shape_tabular(raw)
        hints = build_hints(
            total_count=result.get("total_count"),
            returned_count=result.get("returned_count"),
            truncated=result.get("truncated", False),
            page_num=page_num,
            limit=limit,
            extra=[
                "Results are per-location. Use get_ranking_trends for non-local rank history.",
            ],
        )
        return attach_hints(result, hints)

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
        result = client.shape_tabular(raw)
        hints = build_hints(
            total_count=result.get("total_count"),
            returned_count=result.get("returned_count"),
            truncated=result.get("truncated", False),
            page_num=page_num,
            limit=limit,
            extra=[
                "Use get_landings_history with a specific keyword_id to see which pages ranked over time.",
            ],
        )
        return attach_hints(result, hints)

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
        result = client.shape_tabular(raw)
        hints = build_hints(
            total_count=result.get("total_count"),
            returned_count=result.get("returned_count"),
            truncated=result.get("truncated", False),
            extra=[
                "Use get_landing_matches to see match/mismatch status across all keywords.",
            ],
        )
        return attach_hints(result, hints)

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
        result = client.shape_tabular(raw)
        hints = build_hints(
            total_count=result.get("total_count"),
            returned_count=result.get("returned_count"),
            truncated=result.get("truncated", False),
            extra=[
                "Use get_keyword_performance for per-keyword breakdown.",
                "Use get_ranking_trends for position history over time.",
            ],
        )
        return attach_hints(result, hints)
