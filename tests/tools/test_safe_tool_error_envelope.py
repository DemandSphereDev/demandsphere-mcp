"""Verify safe_tool surfaces isError=True on the MCP envelope for upstream errors."""

from __future__ import annotations

import json

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from demandsphere_mcp.client import DSApiError
from demandsphere_mcp.tools.utils import safe_tool


@pytest.mark.asyncio
async def test_safe_tool_returns_iserror_true_on_dsapierror():
    mcp = FastMCP("test")

    @mcp.tool()
    @safe_tool
    async def always_fails() -> dict:
        raise DSApiError(400, "boom")

    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        await client.initialize()
        result = await client.call_tool("always_fails", {})

    assert result.isError is True, (
        f"Expected isError=True on envelope, got {result.isError}. " f"Content: {result.content}"
    )
    payload = json.loads(result.content[0].text)
    assert payload["error"] is True
    assert payload["error_type"] == "validation_error"
    assert payload["status_code"] == 400
