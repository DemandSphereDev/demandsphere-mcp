"""Keyword and ranking tools (v5.0 API).

Note on identifiers: The DS API uses two different site identifiers.
- ``global_key``: The site's global key string (used by serp_analytics view='performance')
- ``site_id``: The site's ID string (used by all other v5.0 endpoints)
Both are returned by list_sites. The parameter names here match the DS API.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import DSClient
from .utils import attach_hints, build_hints, clamp_limit, safe_tool, validate_date_range

_SERP_VIEWS = {"performance", "trends", "engine_comparison", "engine_summary"}


def register(mcp: FastMCP, client: DSClient) -> None:
    @mcp.tool()
    @safe_tool
    async def serp_analytics(
        view: str,
        search_engine: str,
        from_date: str,
        to_date: str,
        global_key: str | None = None,
        site_id: str | None = None,
        sort_by: str = "keyword_name",
        order: str = "asc",
        granularity: str = "daily",
        grouped: bool = False,
        limit: int = 25,
        page_num: int = 1,
    ) -> dict:
        """SERP analytics with multiple views. view='performance': per-keyword rank, traffic, CTR (requires global_key). view='trends': rank history over time (requires site_id). view='engine_comparison': compare rankings across engines (requires site_id). view='engine_summary': aggregate rank/visits/revenue (requires site_id)."""
        if view not in _SERP_VIEWS:
            raise ValueError(
                f"Invalid view '{view}'. Must be one of: {', '.join(sorted(_SERP_VIEWS))}"
            )

        if view == "performance":
            if not global_key:
                raise ValueError("global_key is required for view='performance'")
        else:
            if not site_id:
                raise ValueError(f"site_id is required for view='{view}'")

        validate_date_range(from_date, to_date)

        if view == "performance":
            limit = clamp_limit(limit)
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
                    "Use serp_analytics(view='trends') with site_id to see position history over time.",
                    "Use get_landing_matches to check if the right pages are ranking.",
                ],
            )
            return attach_hints(result, hints)

        if view == "trends":
            limit = clamp_limit(limit)
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

        if view == "engine_comparison":
            limit = clamp_limit(limit)
            params = {
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
                    "Use serp_analytics(view='performance') for detailed per-keyword metrics on a single engine.",
                ],
            )
            return attach_hints(result, hints)

        # engine_summary
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
                "Use serp_analytics(view='performance') for per-keyword breakdown.",
                "Use serp_analytics(view='trends') for position history over time.",
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
                "Use serp_analytics(view='trends', grouped=True) to see rank trends by group.",
                "Use serp_analytics(view='performance') with global_key for per-keyword detail.",
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
                "Results are per-location. Use serp_analytics(view='trends') for non-local rank history.",
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
