"""Site discovery tools (v5.0)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import DSClient
from .utils import safe_tool


def register(mcp: FastMCP, client: DSClient) -> None:
    @mcp.tool()
    @safe_tool
    async def list_sites() -> dict:
        """List all sites with org/account hierarchy. Returns site IDs needed by other tools."""
        raw = await client.post("/sites/properties/list")
        data = raw.get("propertyList", raw)
        hints = [
            "Each site has a global_key (for serp_analytics view='performance', v5.1 tools) and an id/site_id (for other v5.0 tools).",
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
        raw = await client.post("/sites/hierarchy/list")
        data = raw.get("hierarchyList", raw)
        hints = [
            "Use the id field as site_id for v5.0 keyword tools. Use global_key (from list_sites) for serp_analytics(view='performance') and v5.1 tools.",
            "Next step: call serp_analytics, get_mentions, or llm_analytics with a site identifier.",
        ]
        if isinstance(data, dict):
            data["hints"] = hints
            return data
        return {"sites": data, "hints": hints}
