"""Tests for consolidated serp_analytics and llm_analytics tools."""

from __future__ import annotations

import pytest
from _helpers import unwrap_error

from demandsphere_mcp.client import set_default_client
from demandsphere_mcp.tools.genai_v51 import register as register_genai
from demandsphere_mcp.tools.keywords_v50 import register as register_keywords

# ── Helpers ──────────────────────────────────────────────────────────


class FakeClient:
    """Stub client that records calls and returns canned data."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def get(self, path: str, **kwargs) -> dict:
        self.calls.append(("GET", {"path": path, **kwargs}))
        return {"data": {"records": []}}

    async def post(self, path: str, **kwargs) -> dict:
        self.calls.append(("POST", {"path": path, **kwargs}))
        return {"results": [], "totalResults": 0}

    @staticmethod
    def shape_tabular(raw: dict) -> dict:
        return {
            "results": raw.get("results", []),
            "total_count": raw.get("totalResults", 0),
            "returned_count": len(raw.get("results", [])),
            "truncated": False,
        }

    @staticmethod
    def shape_v51(raw: dict) -> dict:
        data = raw.get("data")
        if data is not None:
            return data if isinstance(data, dict) else {"records": data}
        return raw


class FakeMCP:
    """Stub that captures tool registrations."""

    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def _setup_keywords() -> tuple[FakeMCP, FakeClient]:
    mcp = FakeMCP()
    client = FakeClient()
    set_default_client(client)  # type: ignore[arg-type]
    register_keywords(mcp)
    return mcp, client


def _setup_genai() -> tuple[FakeMCP, FakeClient]:
    mcp = FakeMCP()
    client = FakeClient()
    set_default_client(client)  # type: ignore[arg-type]
    register_genai(mcp)
    return mcp, client


# ── serp_analytics ───────────────────────────────────────────────────


class TestSerpAnalytics:
    def test_registered(self):
        mcp, _ = _setup_keywords()
        assert "serp_analytics" in mcp.tools

    def test_old_tools_removed(self):
        mcp, _ = _setup_keywords()
        for name in (
            "get_keyword_performance",
            "get_ranking_trends",
            "get_search_engine_comparison",
            "get_search_engine_summary",
        ):
            assert name not in mcp.tools

    def test_remaining_tools_present(self):
        mcp, _ = _setup_keywords()
        for name in (
            "get_keyword_groups",
            "get_local_rankings",
            "get_landing_matches",
            "get_landings_history",
        ):
            assert name in mcp.tools

    @pytest.mark.asyncio
    async def test_invalid_view(self):
        mcp, _ = _setup_keywords()
        result = unwrap_error(
            await mcp.tools["serp_analytics"](
                view="bad",
                search_engine="google_us",
                from_date="2025-01-01",
                to_date="2025-01-07",
            )
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_performance_requires_global_key(self):
        mcp, _ = _setup_keywords()
        result = unwrap_error(
            await mcp.tools["serp_analytics"](
                view="performance",
                search_engine="google_us",
                from_date="2025-01-01",
                to_date="2025-01-07",
            )
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_trends_requires_site_id(self):
        mcp, _ = _setup_keywords()
        result = unwrap_error(
            await mcp.tools["serp_analytics"](
                view="trends",
                search_engine="google_us",
                from_date="2025-01-01",
                to_date="2025-01-07",
            )
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_engine_comparison_requires_site_id(self):
        mcp, _ = _setup_keywords()
        result = unwrap_error(
            await mcp.tools["serp_analytics"](
                view="engine_comparison",
                search_engine="google_us",
                from_date="2025-01-01",
                to_date="2025-01-07",
            )
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_engine_summary_requires_site_id(self):
        mcp, _ = _setup_keywords()
        result = unwrap_error(
            await mcp.tools["serp_analytics"](
                view="engine_summary",
                search_engine="google_us",
                from_date="2025-01-01",
                to_date="2025-01-07",
            )
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_performance_calls_correct_endpoint(self):
        mcp, client = _setup_keywords()
        await mcp.tools["serp_analytics"](
            view="performance",
            search_engine="google_us",
            from_date="2025-01-01",
            to_date="2025-01-07",
            global_key="gk1",
        )
        assert len(client.calls) == 1
        assert client.calls[0][0] == "POST"
        assert "keywords_performance_detail" in client.calls[0][1]["path"]
        assert client.calls[0][1]["params"]["global_key"] == "gk1"

    @pytest.mark.asyncio
    async def test_trends_calls_correct_endpoint(self):
        mcp, client = _setup_keywords()
        await mcp.tools["serp_analytics"](
            view="trends",
            search_engine="google_us",
            from_date="2025-01-01",
            to_date="2025-01-07",
            site_id="s1",
        )
        assert len(client.calls) == 1
        assert "ranking_trends" in client.calls[0][1]["path"]
        assert client.calls[0][1]["params"]["site_id"] == "s1"

    @pytest.mark.asyncio
    async def test_engine_comparison_calls_correct_endpoint(self):
        mcp, client = _setup_keywords()
        await mcp.tools["serp_analytics"](
            view="engine_comparison",
            search_engine="google_us,bing_us",
            from_date="2025-01-01",
            to_date="2025-01-07",
            site_id="s1",
        )
        assert len(client.calls) == 1
        assert "search_engines" in client.calls[0][1]["path"]

    @pytest.mark.asyncio
    async def test_engine_summary_calls_correct_endpoint(self):
        mcp, client = _setup_keywords()
        await mcp.tools["serp_analytics"](
            view="engine_summary",
            search_engine="google_us",
            from_date="2025-01-01",
            to_date="2025-01-07",
            site_id="s1",
        )
        assert len(client.calls) == 1
        assert "summary" in client.calls[0][1]["path"]

    @pytest.mark.asyncio
    async def test_trends_grouped_param(self):
        mcp, client = _setup_keywords()
        await mcp.tools["serp_analytics"](
            view="trends",
            search_engine="google_us",
            from_date="2025-01-01",
            to_date="2025-01-07",
            site_id="s1",
            grouped=True,
        )
        assert client.calls[0][1]["params"]["grouped"] == "true"

    @pytest.mark.asyncio
    async def test_engine_summary_no_pagination(self):
        mcp, client = _setup_keywords()
        await mcp.tools["serp_analytics"](
            view="engine_summary",
            search_engine="google_us",
            from_date="2025-01-01",
            to_date="2025-01-07",
            site_id="s1",
        )
        params = client.calls[0][1]["params"]
        assert "limit" not in params
        assert "page_num" not in params
        assert "sort_by" not in params

    @pytest.mark.asyncio
    async def test_performance_returns_hints(self):
        mcp, _ = _setup_keywords()
        result = await mcp.tools["serp_analytics"](
            view="performance",
            search_engine="google_us",
            from_date="2025-01-01",
            to_date="2025-01-07",
            global_key="gk1",
        )
        assert "hints" in result


# ── llm_analytics ────────────────────────────────────────────────────


class TestLlmAnalytics:
    def test_registered(self):
        mcp, _ = _setup_genai()
        assert "llm_analytics" in mcp.tools

    def test_old_tools_removed(self):
        mcp, _ = _setup_genai()
        for name in (
            "get_llm_stats",
            "get_llm_performance_summary",
            "get_channels_performance_summary",
            "get_cross_channel_overview",
            "get_cross_llms_overview",
        ):
            assert name not in mcp.tools

    def test_remaining_tools_present(self):
        mcp, _ = _setup_genai()
        for name in (
            "get_mentions",
            "get_keyword_citations",
            "get_bulk_citations",
            "get_site_citations",
            "get_llm_filters",
            "get_people_also_ask",
        ):
            assert name in mcp.tools

    @pytest.mark.asyncio
    async def test_invalid_view(self):
        mcp, _ = _setup_genai()
        result = unwrap_error(
            await mcp.tools["llm_analytics"](
                view="bad",
                site_global_key="site1",
            )
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_stats_calls_correct_endpoint(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="stats",
            site_global_key="site1",
        )
        assert len(client.calls) == 1
        assert client.calls[0][0] == "GET"
        assert "llms/stats" in client.calls[0][1]["path"]

    @pytest.mark.asyncio
    async def test_performance_calls_correct_endpoint(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="performance",
            site_global_key="site1",
            metric="page_views",
        )
        assert "llms_performance_summary" in client.calls[0][1]["path"]
        assert client.calls[0][1]["params"]["metric"] == "page_views"

    @pytest.mark.asyncio
    async def test_channels_calls_correct_endpoint(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="channels",
            site_global_key="site1",
        )
        assert "channels_performance_summary" in client.calls[0][1]["path"]

    @pytest.mark.asyncio
    async def test_cross_channel_calls_correct_endpoint(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="cross_channel",
            site_global_key="site1",
        )
        assert "cross_channel_overview" in client.calls[0][1]["path"]

    @pytest.mark.asyncio
    async def test_cross_llms_calls_correct_endpoint(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="cross_llms",
            site_global_key="site1",
        )
        assert "cross_llms_overview" in client.calls[0][1]["path"]

    @pytest.mark.asyncio
    async def test_stats_no_metric_param(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="stats",
            site_global_key="site1",
        )
        assert "metric" not in client.calls[0][1]["params"]

    @pytest.mark.asyncio
    async def test_performance_has_metric_param(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="performance",
            site_global_key="site1",
        )
        assert client.calls[0][1]["params"]["metric"] == "visits"

    @pytest.mark.asyncio
    async def test_llms_list_only_for_stats_and_performance(self):
        mcp, client = _setup_genai()
        # stats: should include llms_list
        await mcp.tools["llm_analytics"](
            view="stats",
            site_global_key="site1",
            llms_list="chatgpt,gemini",
        )
        assert client.calls[0][1]["params"]["llms_list"] == "chatgpt,gemini"

        # channels: should NOT include llms_list
        await mcp.tools["llm_analytics"](
            view="channels",
            site_global_key="site1",
            llms_list="chatgpt,gemini",
        )
        assert "llms_list" not in client.calls[1][1]["params"]

    @pytest.mark.asyncio
    async def test_date_params_passed_when_provided(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="stats",
            site_global_key="site1",
            from_date="2025-01-01",
            to_date="2025-01-31",
        )
        params = client.calls[0][1]["params"]
        assert params["from"] == "2025-01-01"
        assert params["to"] == "2025-01-31"

    @pytest.mark.asyncio
    async def test_date_params_omitted_when_none(self):
        mcp, client = _setup_genai()
        await mcp.tools["llm_analytics"](
            view="stats",
            site_global_key="site1",
        )
        params = client.calls[0][1]["params"]
        assert "from" not in params
        assert "to" not in params

    @pytest.mark.asyncio
    async def test_returns_hints(self):
        mcp, _ = _setup_genai()
        result = await mcp.tools["llm_analytics"](
            view="stats",
            site_global_key="site1",
        )
        assert "hints" in result
