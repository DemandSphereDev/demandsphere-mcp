"""Brand management tools (v5.1 API)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import get_client
from .utils import attach_hints, safe_tool, validate_str


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @safe_tool
    async def list_brands(global_key: str) -> dict:
        """List brands configured for a site (used for GenAI mention/citation tracking)."""
        global_key = validate_str(global_key, "global_key")
        raw = await get_client().get(
            "/api/v5_1/brands/list_brands",
            params={"global_key": global_key},
        )
        result = get_client().shape_v51(raw)
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
        dry_run: bool = False,
    ) -> dict:
        """Create a new brand for GenAI visibility tracking."""
        global_key = validate_str(global_key, "global_key")
        if dry_run:
            return {
                "dry_run": True,
                "action": "create_brand",
                "would_create": {
                    "brand_name": brand_name,
                    "brand_description": brand_description,
                },
                "hints": ["Set dry_run=False to execute this action."],
            }
        raw = await get_client().post(
            "/api/v5_1/brands",
            json_body={
                "global_key": global_key,
                "brand_name": brand_name,
                "brand_description": brand_description,
            },
        )
        result = get_client().shape_v51(raw)
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
        dry_run: bool = False,
    ) -> dict:
        """Update an existing brand's name or description."""
        global_key = validate_str(global_key, "global_key")
        if dry_run:
            changes: dict = {}
            if brand_name is not None:
                changes["brand_name"] = brand_name
            if brand_description is not None:
                changes["brand_description"] = brand_description
            return {
                "dry_run": True,
                "action": "update_brand",
                "brand_id": brand_id,
                "would_update": changes,
                "hints": ["Set dry_run=False to execute this action."],
            }
        body: dict = {"global_key": global_key, "brand_id": brand_id}
        if brand_name is not None:
            body["brand_name"] = brand_name
        if brand_description is not None:
            body["brand_description"] = brand_description
        raw = await get_client().post("/api/v5_1/brands/update_brand", json_body=body)
        result = get_client().shape_v51(raw)
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
        dry_run: bool = False,
    ) -> dict:
        """Delete one or more brands by ID."""
        global_key = validate_str(global_key, "global_key")
        if dry_run:
            return {
                "dry_run": True,
                "action": "delete_brands",
                "would_delete": brand_ids,
                "hints": [
                    "Set dry_run=False to execute this action.",
                    "Use list_brands to verify brand IDs before deleting.",
                ],
            }
        raw = await get_client().post(
            "/api/v5_1/brands/delete_brands",
            json_body={"global_key": global_key, "brand_ids": brand_ids},
        )
        result = get_client().shape_v51(raw)
        return attach_hints(
            result,
            [
                "Brands deleted. Use list_brands to verify.",
            ],
        )
