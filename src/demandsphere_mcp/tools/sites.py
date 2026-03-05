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
        return raw.get("propertyList", raw)

    @mcp.tool()
    @safe_tool
    async def list_sites_flat() -> dict:
        """List all sites as a flat array. Returns id, name, url, keyword count."""
        raw = await client.post("/sites/hierarchy/list")
        return raw.get("hierarchyList", raw)
