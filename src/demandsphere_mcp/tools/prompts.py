"""MCP Prompts for common SEO and GenAI visibility workflows."""

from __future__ import annotations

from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

from ..client import DSClient


def register(mcp: FastMCP, client: DSClient) -> None:
    @mcp.prompt(
        name="weekly-ranking-report",
        description="Analyze keyword rankings for the last 7 days. Highlights drops, gains, and new top-10 entries.",
    )
    def weekly_ranking_report(
        site_global_key: str,
        search_engine: str = "google_us",
    ) -> str:
        today = date.today()
        from_date = (today - timedelta(days=7)).isoformat()
        to_date = today.isoformat()
        return (
            f"Analyze keyword ranking changes for site '{site_global_key}' "
            f"on {search_engine} over the last 7 days ({from_date} to {to_date}).\n\n"
            "Steps:\n"
            f"1. Call serp_analytics(view='performance') with global_key='{site_global_key}', "
            f"search_engine='{search_engine}', from_date='{from_date}', to_date='{to_date}', "
            "sort_by='keyword_name', limit=25. Paginate through all results.\n"
            "2. Identify keywords that dropped more than 5 positions.\n"
            "3. Identify keywords that entered the top 10.\n"
            "4. Summarize the overall ranking trend (improving, stable, or declining).\n"
            "5. Highlight any keywords with significant traffic or search volume changes.\n\n"
            "Present findings in a structured report with sections for drops, gains, "
            "and overall summary."
        )

    @mcp.prompt(
        name="genai-visibility-check",
        description="Check AI citation visibility across ChatGPT, Gemini, and Perplexity.",
    )
    def genai_visibility_check(
        site_global_key: str,
    ) -> str:
        target_date = date.today().isoformat()
        return (
            f"Check GenAI visibility for site '{site_global_key}' "
            f"as of {target_date}.\n\n"
            "Steps:\n"
            "1. Call get_mentions for each AI platform:\n"
            f"   - search_engine='chatgpt_us', site_global_key='{site_global_key}', target_date='{target_date}'\n"
            f"   - search_engine='gemini_us', site_global_key='{site_global_key}', target_date='{target_date}'\n"
            f"   - search_engine='perplexity_us', site_global_key='{site_global_key}', target_date='{target_date}'\n"
            "2. For each platform, report total mention count and breakdown by brand.\n"
            f"3. Call get_site_citations with site_global_key='{site_global_key}' for each platform "
            "to see which URLs are being cited.\n"
            "4. Compare client mentions vs competitor mentions.\n"
            "5. Identify keywords where the site is mentioned but not cited (and vice versa).\n\n"
            "Present a cross-platform comparison table and highlight opportunities "
            "to improve AI visibility."
        )

    @mcp.prompt(
        name="competitor-gap",
        description="Compare keyword rankings between two sites to find competitive gaps and opportunities.",
    )
    def competitor_gap(
        site_global_key: str,
        competitor_global_key: str,
        search_engine: str = "google_us",
    ) -> str:
        today = date.today()
        from_date = (today - timedelta(days=30)).isoformat()
        to_date = today.isoformat()
        return (
            f"Compare keyword rankings: '{site_global_key}' vs '{competitor_global_key}' "
            f"on {search_engine} over the last 30 days ({from_date} to {to_date}).\n\n"
            "Steps:\n"
            f"1. Call serp_analytics(view='performance') for site_global_key='{site_global_key}', "
            f"search_engine='{search_engine}', from_date='{from_date}', to_date='{to_date}'. "
            "Paginate to get all keywords.\n"
            f"2. Call serp_analytics(view='performance') for site_global_key='{competitor_global_key}', "
            f"search_engine='{search_engine}', from_date='{from_date}', to_date='{to_date}'. "
            "Paginate to get all keywords.\n"
            "3. Find keywords where the competitor ranks but our site does not (competitor-only keywords).\n"
            "4. Find shared keywords where the competitor ranks higher than our site.\n"
            "5. Find keywords where our site ranks but the competitor does not (our advantages).\n"
            "6. Rank opportunities by search volume and traffic potential.\n\n"
            "Present findings as:\n"
            "- Competitor-only keywords (highest opportunity)\n"
            "- Shared keywords where we trail (quick wins)\n"
            "- Our unique advantages (defend these)"
        )

    @mcp.prompt(
        name="landing-page-audit",
        description="Audit landing page match/mismatch status and identify keywords pointing to wrong pages.",
    )
    def landing_page_audit(
        site_global_key: str,
        search_engine: str = "google_us",
    ) -> str:
        today = date.today()
        from_date = (today - timedelta(days=7)).isoformat()
        to_date = today.isoformat()
        return (
            f"Audit landing page alignment for site '{site_global_key}' "
            f"on {search_engine} ({from_date} to {to_date}).\n\n"
            "Steps:\n"
            f"1. Call get_landing_matches with site_id='{site_global_key}', "
            f"search_engine='{search_engine}', from_date='{from_date}', to_date='{to_date}', "
            "limit=25. Paginate through all results.\n"
            "2. Separate results into three categories:\n"
            "   - Match: ranking page equals preferred landing page\n"
            "   - Mismatch: ranking page differs from preferred landing page\n"
            "   - None: no preferred landing page set\n"
            "3. For mismatches, show the keyword, the preferred page, and the actual ranking page.\n"
            "4. For keywords with high search volume and mismatched landing pages, "
            "call get_landings_history to check if the mismatch is recent or persistent.\n\n"
            "Present findings with:\n"
            "- Summary stats (match %, mismatch %, unset %)\n"
            "- Priority mismatches sorted by search volume\n"
            "- Recommendations for fixing the top mismatches"
        )
