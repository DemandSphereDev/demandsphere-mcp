"""Configuration for the DemandSphere MCP server.

Credentials are resolved in this order:
1. Environment variables  (DEMANDSPHERE_API_KEY, DEMANDSPHERE_BASE_URL)
2. Config file            (~/.config/demandsphere/config.json)
3. Runtime prompt         (server asks MCP client to supply the key)

The API key NEVER appears in tool descriptions — it stays in the server
process and is injected into every outbound request.
"""

from __future__ import annotations

import json
import logging
import stat
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger("demandsphere_mcp.config")

_CONFIG_DIR = Path.home() / ".config" / "demandsphere"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


def _load_file_config() -> dict:
    """Read optional JSON config file, with permissions check."""
    if not _CONFIG_FILE.exists():
        return {}

    # Warn if config file is readable by group or others (like SSH does)
    try:
        mode = _CONFIG_FILE.stat().st_mode
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            logger.warning(
                "Config file %s is readable by group/others. " "Consider running: chmod 600 %s",
                _CONFIG_FILE,
                _CONFIG_FILE,
            )
    except OSError:
        pass

    try:
        return json.loads(_CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


_file_cfg = _load_file_config()


class Settings(BaseSettings):
    """Server-wide settings — populated from env vars or config file."""

    # ── Auth ──────────────────────────────────────────────────────────
    api_key: str = Field(
        default=_file_cfg.get("api_key", ""),
        description="DemandSphere API key (query-param auth).",
    )

    # ── Networking ────────────────────────────────────────────────────
    base_url: str = Field(
        default=_file_cfg.get("base_url", "https://api.demandsphere.com"),
        description="DemandSphere API base URL.",
    )
    request_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds.",
    )

    # ── Rate Limiting ─────────────────────────────────────────────────
    max_requests_per_minute: int = Field(
        default=60,
        description="Client-side rate-limit cap.",
    )
    max_results_per_tool_call: int = Field(
        default=100,
        description="Max rows returned to the LLM per tool call (token budget).",
    )

    # ── Transport ─────────────────────────────────────────────────────
    transport: str = Field(
        default="stdio",
        description="MCP transport: 'stdio' or 'streamable-http'.",
    )
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8765)

    model_config = {
        "env_prefix": "DEMANDSPHERE_",
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
