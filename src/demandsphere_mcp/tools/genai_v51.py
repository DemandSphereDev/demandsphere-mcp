"""GenAI visibility tools (v5.1 API)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import get_client, validate_path_param
from .utils import attach_hints, clamp_limit, safe_tool, validate_date, validate_date_range

_LLM_VIEWS = {"stats", "performance", "channels", "cross_channel", "cross_llms"}

_LLM_ENDPOINTS = {
    "stats": "stats",
    "performance": "llms_performance_summary",
    "channels": "channels_performance_summary",
    "cross_channel": "cross_channel_overview",
    "cross_llms": "cross_llms_overview",
}


def register(mcp: FastMCP) -> None:
    # ── Mentions & Citations ──────────────────────────────────────────

    @mcp.tool()
    @safe_tool
    async def get_mentions(
        site_global_key: str,
        search_engine: str,
        target_date: str,
        keyword_tags: list[str] | None = None,
        keyword_names: list[str] | None = None,
    ) -> dict:
        """Brand mentions and citations in AI responses. Returns per-keyword mention counts, context sentences, cited URLs, client vs competitor breakdown."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date(target_date, "target_date")
        params: dict = {
            "search_engine": search_engine,
            "target_date": target_date,
        }
        if keyword_tags:
            params["keyword_tags[]"] = keyword_tags
        if keyword_names:
            params["keyword_names[]"] = keyword_names
        raw = await get_client().get(f"/v5_1/accounts/sites/{key}/mentions", params=params)
        result = get_client().shape_v51(raw)
        return attach_hints(
            result,
            [
                "Use get_keyword_citations to see citation URLs for a specific keyword.",
                "Use get_site_citations for paginated citations across all keywords.",
                "Filter by keyword_tags or keyword_names to narrow results.",
            ],
        )

    @mcp.tool()
    @safe_tool
    async def get_keyword_citations(
        site_global_key: str,
        search_engine: str,
        target_date: str,
        keyword_name: str,
    ) -> dict:
        """Citation URLs for a single keyword on an AI platform."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date(target_date, "target_date")
        raw = await get_client().post(
            f"/v5_1/accounts/sites/{key}/queries/citations",
            params={
                "search_engine": search_engine,
                "target_date": target_date,
                "query_keyword_name": keyword_name,
            },
        )
        result = get_client().shape_v51(raw)
        return attach_hints(
            result,
            [
                "Use get_bulk_citations to fetch citations for multiple keywords in one call (max 50).",
                "Use get_mentions for brand mention counts and context sentences.",
            ],
        )

    @mcp.tool()
    @safe_tool
    async def get_bulk_citations(
        site_global_key: str,
        search_engine: str,
        target_date: str,
        keyword_names: list[str],
    ) -> dict:
        """Citation URLs for multiple keywords in one call (max 50). Returns keyword→URLs mapping."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date(target_date, "target_date")
        raw = await get_client().post(
            f"/v5_1/accounts/sites/{key}/queries/bulk_citations",
            params={
                "search_engine": search_engine,
                "target_date": target_date,
            },
            json_body={"query_keyword_names": keyword_names[:50]},
        )
        result = get_client().shape_v51(raw)
        hints = [
            "Use get_mentions for mention counts and context sentences alongside citation URLs."
        ]
        if len(keyword_names) > 50:
            hints.insert(
                0,
                "Maximum 50 keywords per call reached. Make additional calls for remaining keywords.",
            )
        return attach_hints(result, hints)

    @mcp.tool()
    @safe_tool
    async def get_site_citations(
        site_global_key: str,
        search_engine: str,
        target_date: str,
        page_number: int = 1,
        page_limit: int = 10,
        keyword_tags: list[str] | None = None,
    ) -> dict:
        """Paginated citations for all keywords on a site. Returns keyword→URLs mapping."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date(target_date, "target_date")
        page_limit = clamp_limit(page_limit)
        params: dict = {
            "search_engine": search_engine,
            "target_date": target_date,
            "page[number]": page_number,
            "page[limit]": page_limit,
        }
        if keyword_tags:
            params["keyword_tags[]"] = keyword_tags
        raw = await get_client().get(f"/v5_1/accounts/sites/{key}/citations", params=params)
        result = get_client().shape_v51(raw)
        extra = [
            "Use get_keyword_citations for detailed citations on a single keyword.",
            "Use get_bulk_citations to fetch citations for up to 50 keywords at once.",
        ]
        records = result.get("records", []) if isinstance(result, dict) else []
        if isinstance(records, list) and len(records) >= page_limit:
            extra.insert(
                0,
                f"Received {len(records)} results (full page). "
                f"There may be more — set page_number={page_number + 1} to continue.",
            )
        return attach_hints(result, extra)

    # ── LLM Traffic Analytics ─────────────────────────────────────────

    @mcp.tool()
    @safe_tool
    async def llm_analytics(
        view: str,
        site_global_key: str,
        from_date: str | None = None,
        to_date: str | None = None,
        metric: str = "visits",
        llms_list: str | None = None,
        channels_list: str | None = None,
    ) -> dict:
        """LLM traffic analytics with multiple views. view='stats': aggregated traffic stats. view='performance': side-by-side LLM comparison. view='channels': per-channel comparison. view='cross_channel': cross-channel overview. view='cross_llms': cross-platform comparison. Use metric param for non-stats views. Filter with llms_list/channels_list (comma-separated) for stats/performance views."""
        if view not in _LLM_VIEWS:
            raise ValueError(
                f"Invalid view '{view}'. Must be one of: {', '.join(sorted(_LLM_VIEWS))}"
            )

        key = validate_path_param(site_global_key, "site_global_key")
        validate_date_range(from_date, to_date)

        params: dict = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        # metric applies to all views except stats
        if view != "stats":
            params["metric"] = metric

        # llms_list/channels_list only for stats and performance
        if view in ("stats", "performance"):
            if llms_list:
                params["llms_list"] = llms_list
            if channels_list:
                params["channels_list"] = channels_list

        endpoint = _LLM_ENDPOINTS[view]
        raw = await get_client().get(
            f"/v5_1/accounts/sites/{key}/analytics/site_visits/llms/{endpoint}",
            params=params,
        )
        result = get_client().shape_v51(raw)

        # View-specific hints
        if view == "stats":
            hints = [
                "Use llm_analytics(view='performance') for side-by-side LLM comparison.",
                "Use llm_analytics(view='cross_llms') to compare traffic across all LLM platforms.",
                "Filter by llms_list or channels_list (comma-separated) to narrow results.",
            ]
        elif view == "performance":
            hints = [
                f"Currently showing metric='{metric}'. Other options: visits, page_views, new_visits, bounces, conversions, value.",
                "Use llm_analytics(view='channels') to compare across traffic channels instead of LLMs.",
            ]
        elif view == "channels":
            hints = [
                f"Currently showing metric='{metric}'. Other options: visits, page_views, new_visits, bounces, conversions, value.",
                "Use llm_analytics(view='performance') to compare across LLM platforms instead of channels.",
            ]
        elif view == "cross_channel":
            hints = [
                f"Currently showing metric='{metric}'. Other options: visits, page_views, new_visits, bounces, conversions, value.",
                "Use llm_analytics(view='channels') for more detailed per-channel comparison.",
            ]
        else:  # cross_llms
            hints = [
                f"Currently showing metric='{metric}'. Other options: visits, page_views, new_visits, bounces, conversions, value.",
                "Use llm_analytics(view='performance') for more detailed per-LLM comparison.",
            ]

        return attach_hints(result, hints)

    @mcp.tool()
    @safe_tool
    async def get_llm_filters(site_global_key: str) -> dict:
        """Available filter values for LLM analytics: channels, LLM names, metrics."""
        key = validate_path_param(site_global_key, "site_global_key")
        raw = await get_client().get(
            f"/v5_1/accounts/sites/{key}/analytics/site_visits/llms/filters",
        )
        result = get_client().shape_v51(raw)
        return attach_hints(
            result,
            [
                "Use the returned filter values as llms_list or channels_list parameters in llm_analytics.",
            ],
        )

    # ── People Also Ask ───────────────────────────────────────────────

    @mcp.tool()
    @safe_tool
    async def get_people_also_ask(
        site_global_key: str,
        search_engine: str,
        from_date: str | None = None,
        to_date: str | None = None,
        keyword_names: list[str] | None = None,
        page_number: int = 1,
        page_limit: int = 10,
        include_search_intents: bool = False,
        include_adword_stats: bool = False,
    ) -> dict:
        """PAA questions from SERPs. Optionally includes search intent and AdWords data (volume, CPC, competition)."""
        key = validate_path_param(site_global_key, "site_global_key")
        page_limit = clamp_limit(page_limit)
        validate_date_range(from_date, to_date)
        params: dict = {
            "search_engine": search_engine,
            "page[number]": page_number,
            "page[limit]": page_limit,
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if keyword_names:
            params["keyword_names[]"] = keyword_names
        includes = []
        if include_search_intents:
            includes.append("search_intents")
        if include_adword_stats:
            includes.append("adword_stats")
        if includes:
            params["includes[]"] = includes
        raw = await get_client().get(
            f"/v5_1/accounts/sites/{key}/people_also_asks",
            params=params,
        )
        result = get_client().shape_v51(raw)
        extra: list[str] = []
        records = result.get("records", []) if isinstance(result, dict) else []
        if isinstance(records, list) and len(records) >= page_limit:
            extra.append(
                f"Received {len(records)} results (full page). "
                f"There may be more — set page_number={page_number + 1} to continue.",
            )
        if not include_search_intents:
            extra.append("Set include_search_intents=True to add search intent data.")
        if not include_adword_stats:
            extra.append("Set include_adword_stats=True to add volume, CPC, and competition data.")
        return attach_hints(result, extra)
