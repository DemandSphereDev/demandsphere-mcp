"""Brand management tools (v5.1 API)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import DSClient
from .utils import safe_tool, validate_str, attach_hints


def register(mcp: FastMCP, client: DSClient) -> None:

    @mcp.tool()
    @safe_tool
    async def list_brands(global_key: str) -> dict:
        """List brands configured for a site (used for GenAI mention/citation tracking)."""
        global_key = validate_str(global_key, "global_key")
        raw = await client.get(
            "/api/v5_1/brands/list_brands",
            params={"global_key": global_key},
        )
        result = client.shape_v51(raw)
        return attach_hints(
            result,
            [
                "Use create_brand to add a new brand for GenAI visibility tracking.",
                "Brand names are used by get_mentions and citation tools to track AI mentions.",
            ],
        )

    @mcp.tool()
    @safe_tool
    async def create_brand(
        global_key: str,
        brand_name: str,
        brand_description: str = "",
    ) -> dict:
        """Create a new brand for GenAI visibility tracking."""
        global_key = validate_str(global_key, "global_key")
        raw = await client.post(
            "/api/v5_1/brands",
            json_body={
                "global_key": global_key,
                "brand_name": brand_name,
                "brand_description": brand_description,
            },
        )
        result = client.shape_v51(raw)
        return attach_hints(
            result,
            [
                "Brand created. Use list_brands to verify.",
                "Use get_mentions with this site to see AI mentions for the new brand.",
            ],
        )

    @mcp.tool()
    @safe_tool
    async def update_brand(
        global_key: str,
        brand_id: int,
        brand_name: str | None = None,
        brand_description: str | None = None,
    ) -> dict:
        """Update an existing brand's name or description."""
        global_key = validate_str(global_key, "global_key")
        body: dict = {"global_key": global_key, "brand_id": brand_id}
        if brand_name is not None:
            body["brand_name"] = brand_name
        if brand_description is not None:
            body["brand_description"] = brand_description
        raw = await client.post("/api/v5_1/brands/update_brand", json_body=body)
        result = client.shape_v51(raw)
        return attach_hints(
            result,
            [
                "Brand updated. Use list_brands to verify the changes.",
            ],
        )

    @mcp.tool()
    @safe_tool
    async def delete_brands(
        global_key: str,
        brand_ids: list[int],
    ) -> dict:
        """Delete one or more brands by ID."""
        global_key = validate_str(global_key, "global_key")
        raw = await client.post(
            "/api/v5_1/brands/delete_brands",
            json_body={"global_key": global_key, "brand_ids": brand_ids},
        )
        result = client.shape_v51(raw)
        return attach_hints(
            result,
            [
                "Brands deleted. Use list_brands to verify.",
            ],
        )
