"""Verify list_sites hint does not misrepresent global_key vs id."""

from __future__ import annotations

import pytest

from demandsphere_mcp.client import set_default_client
from demandsphere_mcp.tools.sites import register as register_sites


class _FakeClient:
    async def post(self, path: str, **kwargs) -> dict:
        return {"organizations": [], "accounts": []}


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.mark.asyncio
async def test_list_sites_hint_clarifies_id_is_global_key():
    mcp = _FakeMCP()
    set_default_client(_FakeClient())  # type: ignore[arg-type]
    register_sites(mcp)

    result = await mcp.tools["list_sites"]()
    hints = result["hints"]
    combined = " ".join(hints).lower()

    assert "global_key" in combined
    assert "id" in combined
    # The previous wording implied id and global_key were distinct fields.
    assert "and an id/site_id" not in combined
