"""Site discovery tools (v5.0)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import get_client
from .utils import safe_tool


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @safe_tool
    async def list_sites() -> dict:
        """List all sites with org/account hierarchy. Returns site IDs needed by other tools."""
        raw = await get_client().post("/sites/properties/list")
        data = raw.get("propertyList", raw)
        hints = [
            "The site `id` field returned above is the identifier to pass as `site_id` (v5.0 tools like serp_analytics view='trends') OR as `site_global_key` / `global_key` (v5.1 GenAI and brand tools). There is no separate `global_key` field to look up.",
            "Use list_sites_flat for a simpler flat list with keyword counts.",
        ]
        if isinstance(data, dict):
            data["hints"] = hints
            return data
        return {"sites": data, "hints": hints}

    @mcp.tool()
    @safe_tool
    async def list_sites_flat() -> dict:
        """List all sites as a flat array. Returns id, name, url, keyword count."""
        raw = await get_client().post("/sites/hierarchy/list")
        data = raw.get("hierarchyList", raw)
        hints = [
            "Use the id field as site_id for v5.0 keyword tools. Use global_key (from list_sites) for serp_analytics(view='performance') and v5.1 tools.",
            "Next step: call serp_analytics, get_mentions, or llm_analytics with a site identifier.",
        ]
        if isinstance(data, dict):
            data["hints"] = hints
            return data
        return {"sites": data, "hints": hints}
