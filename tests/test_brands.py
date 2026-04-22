"""Tests for brand mutation dry_run support."""

from __future__ import annotations

import pytest

from demandsphere_mcp.client import set_default_client
from demandsphere_mcp.tools.brands_v51 import register

# ── Helpers ──────────────────────────────────────────────────────────


class FakeClient:
    """Minimal stub that records calls instead of hitting the API."""

    def __init__(self, response: dict | None = None) -> None:
        self._response = response or {"status": "ok", "data": {}}
        self.calls: list[tuple[str, dict]] = []

    async def get(self, path: str, **kwargs) -> dict:
        self.calls.append(("GET", {"path": path, **kwargs}))
        return self._response

    async def post(self, path: str, **kwargs) -> dict:
        self.calls.append(("POST", {"path": path, **kwargs}))
        return self._response

    @staticmethod
    def shape_v51(raw: dict) -> dict:
        data = raw.get("data")
        if data is not None:
            return data if isinstance(data, dict) else {"records": data}
        return raw


class FakeMCP:
    """Minimal stub that captures tool registrations."""

    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def _setup() -> tuple[FakeMCP, FakeClient]:
    mcp = FakeMCP()
    client = FakeClient()
    set_default_client(client)  # type: ignore[arg-type]
    register(mcp)
    return mcp, client


# ── create_brand dry_run ─────────────────────────────────────────────


class TestCreateBrandDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_returns_preview(self):
        mcp, client = _setup()
        result = await mcp.tools["create_brand"](
            global_key="site1",
            brand_name="Acme",
            brand_description="desc",
            dry_run=True,
        )
        assert result["dry_run"] is True
        assert result["action"] == "create_brand"
        assert result["would_create"]["brand_name"] == "Acme"
        assert result["would_create"]["brand_description"] == "desc"
        assert len(client.calls) == 0  # no API call made

    @pytest.mark.asyncio
    async def test_dry_run_false_calls_api(self):
        mcp, client = _setup()
        result = await mcp.tools["create_brand"](
            global_key="site1",
            brand_name="Acme",
            dry_run=False,
        )
        assert "dry_run" not in result
        assert len(client.calls) == 1
        assert client.calls[0][0] == "POST"


# ── update_brand dry_run ─────────────────────────────────────────────


class TestUpdateBrandDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_returns_preview(self):
        mcp, client = _setup()
        result = await mcp.tools["update_brand"](
            global_key="site1",
            brand_id=42,
            brand_name="New Name",
            dry_run=True,
        )
        assert result["dry_run"] is True
        assert result["action"] == "update_brand"
        assert result["brand_id"] == 42
        assert result["would_update"] == {"brand_name": "New Name"}
        assert len(client.calls) == 0

    @pytest.mark.asyncio
    async def test_dry_run_shows_all_changes(self):
        mcp, _client = _setup()
        result = await mcp.tools["update_brand"](
            global_key="site1",
            brand_id=42,
            brand_name="New",
            brand_description="New desc",
            dry_run=True,
        )
        assert result["would_update"] == {
            "brand_name": "New",
            "brand_description": "New desc",
        }

    @pytest.mark.asyncio
    async def test_dry_run_false_calls_api(self):
        mcp, client = _setup()
        result = await mcp.tools["update_brand"](
            global_key="site1",
            brand_id=42,
            brand_name="New",
            dry_run=False,
        )
        assert "dry_run" not in result
        assert len(client.calls) == 1


# ── delete_brands dry_run ────────────────────────────────────────────


class TestDeleteBrandsDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_returns_preview(self):
        mcp, client = _setup()
        result = await mcp.tools["delete_brands"](
            global_key="site1",
            brand_ids=[1, 2, 3],
            dry_run=True,
        )
        assert result["dry_run"] is True
        assert result["action"] == "delete_brands"
        assert result["would_delete"] == [1, 2, 3]
        assert len(client.calls) == 0

    @pytest.mark.asyncio
    async def test_dry_run_hints_include_verify(self):
        mcp, _client = _setup()
        result = await mcp.tools["delete_brands"](
            global_key="site1",
            brand_ids=[1],
            dry_run=True,
        )
        assert any("list_brands" in h for h in result["hints"])

    @pytest.mark.asyncio
    async def test_dry_run_false_calls_api(self):
        mcp, client = _setup()
        result = await mcp.tools["delete_brands"](
            global_key="site1",
            brand_ids=[1],
            dry_run=False,
        )
        assert "dry_run" not in result
        assert len(client.calls) == 1
