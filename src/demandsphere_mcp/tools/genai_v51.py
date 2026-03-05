"""GenAI visibility tools (v5.1 API)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import DSClient, validate_path_param
from .utils import safe_tool, clamp_limit, validate_date, validate_date_range


def register(mcp: FastMCP, client: DSClient) -> None:

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
        raw = await client.get(f"/v5_1/accounts/sites/{key}/mentions", params=params)
        return client.shape_v51(raw)

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
        raw = await client.post(
            f"/v5_1/accounts/sites/{key}/queries/citations",
            params={
                "search_engine": search_engine,
                "target_date": target_date,
                "query_keyword_name": keyword_name,
            },
        )
        return client.shape_v51(raw)

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
        raw = await client.post(
            f"/v5_1/accounts/sites/{key}/queries/bulk_citations",
            params={
                "search_engine": search_engine,
                "target_date": target_date,
            },
            json_body={"query_keyword_names": keyword_names[:50]},
        )
        return client.shape_v51(raw)

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
        raw = await client.get(f"/v5_1/accounts/sites/{key}/citations", params=params)
        return client.shape_v51(raw)

    # ── LLM Traffic Analytics ─────────────────────────────────────────

    @mcp.tool()
    @safe_tool
    async def get_llm_stats(
        site_global_key: str,
        from_date: str | None = None,
        to_date: str | None = None,
        llms_list: str | None = None,
        channels_list: str | None = None,
    ) -> dict:
        """Aggregated LLM traffic stats: visits, page views, performance metrics. Filter by LLM names or channels (comma-separated)."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date_range(from_date, to_date)
        params: dict = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if llms_list:
            params["llms_list"] = llms_list
        if channels_list:
            params["channels_list"] = channels_list
        raw = await client.get(
            f"/v5_1/accounts/sites/{key}/analytics/site_visits/llms/stats",
            params=params,
        )
        return client.shape_v51(raw)

    @mcp.tool()
    @safe_tool
    async def get_llm_performance_summary(
        site_global_key: str,
        from_date: str | None = None,
        to_date: str | None = None,
        metric: str = "visits",
        llms_list: str | None = None,
        channels_list: str | None = None,
    ) -> dict:
        """Side-by-side performance comparison across LLMs. Metric: visits|page_views|new_visits|bounces|conversions|value."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date_range(from_date, to_date)
        params: dict = {"metric": metric}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if llms_list:
            params["llms_list"] = llms_list
        if channels_list:
            params["channels_list"] = channels_list
        raw = await client.get(
            f"/v5_1/accounts/sites/{key}/analytics/site_visits/llms/llms_performance_summary",
            params=params,
        )
        return client.shape_v51(raw)

    @mcp.tool()
    @safe_tool
    async def get_channels_performance_summary(
        site_global_key: str,
        from_date: str | None = None,
        to_date: str | None = None,
        metric: str = "visits",
    ) -> dict:
        """Performance comparison across traffic channels for LLM traffic."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date_range(from_date, to_date)
        params: dict = {"metric": metric}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        raw = await client.get(
            f"/v5_1/accounts/sites/{key}/analytics/site_visits/llms/channels_performance_summary",
            params=params,
        )
        return client.shape_v51(raw)

    @mcp.tool()
    @safe_tool
    async def get_cross_channel_overview(
        site_global_key: str,
        from_date: str | None = None,
        to_date: str | None = None,
        metric: str = "visits",
    ) -> dict:
        """Overview of LLM traffic across all channels."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date_range(from_date, to_date)
        params: dict = {"metric": metric}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        raw = await client.get(
            f"/v5_1/accounts/sites/{key}/analytics/site_visits/llms/cross_channel_overview",
            params=params,
        )
        return client.shape_v51(raw)

    @mcp.tool()
    @safe_tool
    async def get_cross_llms_overview(
        site_global_key: str,
        from_date: str | None = None,
        to_date: str | None = None,
        metric: str = "visits",
    ) -> dict:
        """Compare traffic across all LLM platforms (ChatGPT, Gemini, Perplexity, etc.)."""
        key = validate_path_param(site_global_key, "site_global_key")
        validate_date_range(from_date, to_date)
        params: dict = {"metric": metric}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        raw = await client.get(
            f"/v5_1/accounts/sites/{key}/analytics/site_visits/llms/cross_llms_overview",
            params=params,
        )
        return client.shape_v51(raw)

    @mcp.tool()
    @safe_tool
    async def get_llm_filters(site_global_key: str) -> dict:
        """Available filter values for LLM analytics: channels, LLM names, metrics."""
        key = validate_path_param(site_global_key, "site_global_key")
        raw = await client.get(
            f"/v5_1/accounts/sites/{key}/analytics/site_visits/llms/filters",
        )
        return client.shape_v51(raw)

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
        raw = await client.get(
            f"/v5_1/accounts/sites/{key}/people_also_asks",
            params=params,
        )
        return client.shape_v51(raw)
