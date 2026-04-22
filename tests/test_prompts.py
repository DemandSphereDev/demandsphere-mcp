"""Tests for MCP Prompts (SEO workflow templates)."""

from __future__ import annotations

from demandsphere_mcp.tools.prompts import register

# ── Helpers ──────────────────────────────────────────────────────────


class FakeClient:
    pass


class FakeMCP:
    def __init__(self) -> None:
        self.prompts: dict[str, object] = {}

    def prompt(self, **kwargs):
        name = kwargs.get("name")

        def decorator(fn):
            self.prompts[name or fn.__name__] = fn
            return fn

        return decorator

    def tool(self):
        def decorator(fn):
            return fn

        return decorator


def _setup() -> FakeMCP:
    mcp = FakeMCP()
    client = FakeClient()
    register(mcp, client)
    return mcp


# ── weekly-ranking-report ────────────────────────────────────────────


class TestWeeklyRankingReport:
    def test_registered(self):
        mcp = _setup()
        assert "weekly-ranking-report" in mcp.prompts

    def test_returns_string(self):
        mcp = _setup()
        result = mcp.prompts["weekly-ranking-report"](
            site_global_key="my-site",
            search_engine="google_us",
        )
        assert isinstance(result, str)

    def test_contains_tool_name(self):
        mcp = _setup()
        result = mcp.prompts["weekly-ranking-report"](site_global_key="my-site")
        assert "serp_analytics" in result

    def test_contains_site_key(self):
        mcp = _setup()
        result = mcp.prompts["weekly-ranking-report"](site_global_key="abc-123")
        assert "abc-123" in result

    def test_default_search_engine(self):
        mcp = _setup()
        result = mcp.prompts["weekly-ranking-report"](site_global_key="s")
        assert "google_us" in result

    def test_custom_search_engine(self):
        mcp = _setup()
        result = mcp.prompts["weekly-ranking-report"](site_global_key="s", search_engine="bing_uk")
        assert "bing_uk" in result


# ── genai-visibility-check ───────────────────────────────────────────


class TestGenaiVisibilityCheck:
    def test_registered(self):
        mcp = _setup()
        assert "genai-visibility-check" in mcp.prompts

    def test_returns_string(self):
        mcp = _setup()
        result = mcp.prompts["genai-visibility-check"](site_global_key="my-site")
        assert isinstance(result, str)

    def test_contains_tool_names(self):
        mcp = _setup()
        result = mcp.prompts["genai-visibility-check"](site_global_key="s")
        assert "get_mentions" in result
        assert "get_site_citations" in result

    def test_covers_multiple_platforms(self):
        mcp = _setup()
        result = mcp.prompts["genai-visibility-check"](site_global_key="s")
        assert "chatgpt" in result.lower()
        assert "gemini" in result.lower()
        assert "perplexity" in result.lower()


# ── competitor-gap ───────────────────────────────────────────────────


class TestCompetitorGap:
    def test_registered(self):
        mcp = _setup()
        assert "competitor-gap" in mcp.prompts

    def test_returns_string(self):
        mcp = _setup()
        result = mcp.prompts["competitor-gap"](site_global_key="us", competitor_global_key="them")
        assert isinstance(result, str)

    def test_contains_both_sites(self):
        mcp = _setup()
        result = mcp.prompts["competitor-gap"](
            site_global_key="our-site", competitor_global_key="rival-site"
        )
        assert "our-site" in result
        assert "rival-site" in result

    def test_contains_tool_name(self):
        mcp = _setup()
        result = mcp.prompts["competitor-gap"](site_global_key="a", competitor_global_key="b")
        assert "serp_analytics" in result


# ── landing-page-audit ───────────────────────────────────────────────


class TestLandingPageAudit:
    def test_registered(self):
        mcp = _setup()
        assert "landing-page-audit" in mcp.prompts

    def test_returns_string(self):
        mcp = _setup()
        result = mcp.prompts["landing-page-audit"](site_global_key="my-site")
        assert isinstance(result, str)

    def test_contains_tool_names(self):
        mcp = _setup()
        result = mcp.prompts["landing-page-audit"](site_global_key="s")
        assert "get_landing_matches" in result
        assert "get_landings_history" in result

    def test_contains_site_key(self):
        mcp = _setup()
        result = mcp.prompts["landing-page-audit"](site_global_key="xyz-789")
        assert "xyz-789" in result
