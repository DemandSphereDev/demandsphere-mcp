"""Shared helpers for tests."""

from __future__ import annotations

import json
from typing import Any

from mcp.types import CallToolResult


def unwrap_error(result: Any) -> dict:
    """Unwrap a safe_tool error return into its structured dict.

    ``safe_tool`` wraps error payloads in ``CallToolResult(isError=True)``
    so the MCP envelope surfaces failure correctly, but the structured
    dict still lives inside the content as JSON. Tests that assert on
    the dict shape go through this helper.

    Passes plain dicts through unchanged so success-path and legacy
    assertions keep working.
    """
    if isinstance(result, CallToolResult):
        assert result.isError is True, "unwrap_error called on a non-error CallToolResult"
        assert result.content, "CallToolResult has no content"
        return json.loads(result.content[0].text)
    return result
