"""Tests for MCP Resources (parameter discovery)."""

from __future__ import annotations

import json

import pytest

from demandsphere_mcp.client import set_default_client
from demandsphere_mcp.tools.resources import register

# ── Helpers ──────────────────────────────────────────────────────────


class FakeClient:
    """Stub client that returns canned site data."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def post(self, path: str, **kwargs) -> dict:
        self.calls.append(("POST", {"path": path, **kwargs}))
        return {
            "hierarchyList": [
                {"id": "s1", "global_key": "gk1", "name": "Site One", "url": "https://one.com"},
                {"id": "s2", "global_key": "gk2", "name": "Site Two", "url": "https://two.com"},
            ]
        }


class FakeMCP:
    """Stub that captures resource registrations."""

    def __init__(self) -> None:
        self.resources: dict[str, object] = {}

    def resource(self, uri: str, **kwargs):
        def decorator(fn):
            self.resources[uri] = fn
            return fn

        return decorator

    def tool(self):
        def decorator(fn):
            return fn

        return decorator


def _setup() -> tuple[FakeMCP, FakeClient]:
    mcp = FakeMCP()
    client = FakeClient()
    set_default_client(client)  # type: ignore[arg-type]
    register(mcp)
    return mcp, client


# ── search-engines ───────────────────────────────────────────────────


class TestSearchEngines:
    def test_registered(self):
        mcp, _ = _setup()
        assert "data://search-engines" in mcp.resources

    def test_returns_valid_json(self):
        mcp, _ = _setup()
        result = json.loads(mcp.resources["data://search-engines"]())
        assert "standard" in result
        assert "ai_platforms" in result
        assert "mobile_variants" in result

    def test_contains_common_engines(self):
        mcp, _ = _setup()
        result = json.loads(mcp.resources["data://search-engines"]())
        assert "google_us" in result["standard"]
        assert "bing_us" in result["standard"]

    def test_contains_ai_platforms(self):
        mcp, _ = _setup()
        result = json.loads(mcp.resources["data://search-engines"]())
        assert "chatgpt_us" in result["ai_platforms"]
        assert "gemini_us" in result["ai_platforms"]
        assert "perplexity_us" in result["ai_platforms"]


# ── sort-options ─────────────────────────────────────────────────────


class TestSortOptions:
    def test_registered(self):
        mcp, _ = _setup()
        assert "data://sort-options" in mcp.resources

    def test_has_all_categories(self):
        mcp, _ = _setup()
        result = json.loads(mcp.resources["data://sort-options"]())
        assert "keyword_performance" in result
        assert "keyword_groups" in result
        assert "landing_matches" in result

    def test_keyword_performance_options(self):
        mcp, _ = _setup()
        result = json.loads(mcp.resources["data://sort-options"]())
        kp = result["keyword_performance"]
        assert "keyword_name" in kp
        assert "rank" in kp
        assert "search_volume" in kp
        assert "ctr" in kp


# ── granularity ──────────────────────────────────────────────────────


class TestGranularity:
    def test_registered(self):
        mcp, _ = _setup()
        assert "data://granularity" in mcp.resources

    def test_values(self):
        mcp, _ = _setup()
        result = json.loads(mcp.resources["data://granularity"]())
        assert result["values"] == ["daily", "weekly", "monthly"]
        assert result["default"] == "daily"


# ── metrics ──────────────────────────────────────────────────────────


class TestMetrics:
    def test_registered(self):
        mcp, _ = _setup()
        assert "data://metrics" in mcp.resources

    def test_values(self):
        mcp, _ = _setup()
        result = json.loads(mcp.resources["data://metrics"]())
        assert "visits" in result["values"]
        assert "page_views" in result["values"]
        assert "conversions" in result["values"]
        assert result["default"] == "visits"


# ── sites (dynamic) ─────────────────────────────────────────────────


class TestSites:
    def test_registered(self):
        mcp, _ = _setup()
        assert "data://sites" in mcp.resources

    @pytest.mark.asyncio
    async def test_calls_api(self):
        mcp, client = _setup()
        raw = await mcp.resources["data://sites"]()
        result = json.loads(raw)
        assert len(client.calls) == 1
        assert client.calls[0][1]["path"] == "/sites/hierarchy/list"
        assert len(result["sites"]) == 2

    @pytest.mark.asyncio
    async def test_returns_site_data(self):
        mcp, _ = _setup()
        raw = await mcp.resources["data://sites"]()
        result = json.loads(raw)
        site = result["sites"][0]
        assert site["id"] == "s1"
        assert site["global_key"] == "gk1"

    @pytest.mark.asyncio
    async def test_includes_note(self):
        mcp, _ = _setup()
        raw = await mcp.resources["data://sites"]()
        result = json.loads(raw)
        assert "note" in result
        assert "site_id" in result["note"]
        assert "global_key" in result["note"]
