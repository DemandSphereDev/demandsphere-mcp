"""Shared input gating, error handling, and safety utilities for MCP tools.

Centralizes all validation and safety logic so individual tool modules
don't duplicate or drift:

- ``safe_tool``            — decorator that catches exceptions → structured errors
- ``clamp_limit``          — cap pagination limits to prevent unbounded queries
- ``validate_date``        — reject malformed single date strings (YYYY-MM-DD)
- ``validate_date_range``  — reject malformed or unreasonable date ranges
- ``validate_str``         — reject empty/whitespace-only string params
- ``redact_url``           — strip query params from URLs for safe logging
- ``redact_secrets``       — scrub api_key=... patterns from arbitrary strings
- ``MAX_DATE_RANGE_DAYS``  — cap on how far back tools can look (LLM loop prevention)
"""

from __future__ import annotations

import functools
import json
import logging
import re
from collections.abc import Callable, Coroutine
from datetime import date
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from mcp.types import CallToolResult, TextContent

from ..client import DSApiError
from ..config import settings

logger = logging.getLogger("demandsphere_mcp.tools")

# ── Call budget / runaway prevention ──────────────────────────────────
# An LLM can loop across pages or request huge date ranges. These caps
# provide a safety net independent of the API's own limits.

MAX_DATE_RANGE_DAYS = 365  # max lookback window per tool call


# ── Input validation helpers ──────────────────────────────────────────


def clamp_limit(limit: int) -> int:
    """Clamp a pagination limit to the configured max. Prevents LLMs from requesting limit=100000."""
    return max(1, min(limit, settings.max_results_per_tool_call))


def validate_date(value: str, name: str = "date") -> str:
    """Validate that a single date string is YYYY-MM-DD format."""
    try:
        date.fromisoformat(value)
    except (ValueError, TypeError):
        raise DSApiError(400, f"Invalid {name}: expected YYYY-MM-DD format. Got: {value!r}")
    return value


def validate_str(value: str, name: str) -> str:
    """Reject empty or whitespace-only string parameters."""
    if not value or not value.strip():
        raise DSApiError(400, f"Parameter '{name}' must not be empty.")
    return value.strip()


def validate_date_range(from_date: str | None, to_date: str | None) -> None:
    """Validate date formats and enforce max lookback window.

    Prevents an LLM from requesting 10 years of daily data in one call.
    Either date being None is allowed (the API will use defaults), but
    any provided date is validated for format.
    """
    if from_date is not None:
        try:
            start = date.fromisoformat(from_date)
        except ValueError:
            raise DSApiError(400, f"Invalid from_date: expected YYYY-MM-DD. Got: {from_date!r}")

    if to_date is not None:
        try:
            end = date.fromisoformat(to_date)
        except ValueError:
            raise DSApiError(400, f"Invalid to_date: expected YYYY-MM-DD. Got: {to_date!r}")

    # Range checks only apply when both dates are present
    if from_date is None or to_date is None:
        return

    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)

    if start > end:
        raise DSApiError(400, f"from_date ({from_date}) must be before to_date ({to_date}).")

    if (end - start).days > MAX_DATE_RANGE_DAYS:
        raise DSApiError(
            400,
            f"Date range exceeds {MAX_DATE_RANGE_DAYS} day maximum. "
            f"Requested: {(end - start).days} days ({from_date} to {to_date}).",
        )


# ── URL and secret redaction for safe logging ─────────────────────────

_SECRET_PATTERN = re.compile(r"api_key=[^\s&\"']+", re.IGNORECASE)


def redact_url(url: str) -> str:
    """Strip query parameters from a URL to prevent API key leakage in logs.

    Use this for any log line that might include a request URL.
    """
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="[REDACTED]" if parsed.query else ""))


def redact_secrets(text: str) -> str:
    """Scrub api_key=... patterns from arbitrary strings.

    Applied to error messages before logging or returning to the LLM,
    as a defense-in-depth measure in case a future DSApiError ever
    includes query parameters or URLs in its detail string.
    """
    return _SECRET_PATTERN.sub("api_key=[REDACTED]", text)


# ── Recovery hints for error responses ─────────────────────────────────

_RECOVERY_HINTS: dict[str, str] = {
    "validation_error": (
        "Check parameter formats: dates must be YYYY-MM-DD, "
        "date ranges max 365 days, string params must not be empty."
    ),
    "auth_error": (
        "Check that DEMANDSPHERE_API_KEY is set and valid. "
        "Keys can be generated at app.demandsphere.com/settings."
    ),
    "not_found": (
        "Resource not found. Call list_sites or list_sites_flat "
        "to discover available site IDs and global keys."
    ),
    "rate_limited": (
        "Rate limit reached. Wait a moment and retry — "
        "the built-in rate limiter will handle backoff automatically."
    ),
    "timeout": ("Request timed out. Retry with a smaller date range or lower limit."),
    "upstream_error": (
        "The DemandSphere API returned a server error. Retry once after a brief wait."
    ),
    "network_error": (
        "Could not connect to the DemandSphere API. Check network connectivity and retry."
    ),
    "internal_error": (
        "An unexpected error occurred. Retry once — "
        "if it persists, the issue may need investigation."
    ),
}


def _recovery_hint(error_type: str) -> str:
    """Return actionable recovery guidance for a given error type."""
    return _RECOVERY_HINTS.get(error_type, _RECOVERY_HINTS["internal_error"])


# ── Tool error handling decorator ─────────────────────────────────────


def _error_result(error_dict: dict) -> CallToolResult:
    """Wrap a structured error dict in a CallToolResult with isError=True.

    The structured dict (error_type, recovery_hint, etc.) is preserved
    verbatim inside a single TextContent block so LLM tool-callers can
    still parse it, while the MCP JSON-RPC envelope correctly flags the
    call as failed via ``isError=True``.
    """
    return CallToolResult(
        isError=True,
        content=[TextContent(type="text", text=json.dumps(error_dict))],
    )


def safe_tool(
    fn: Callable[..., Coroutine[Any, Any, dict]],
) -> Callable[..., Coroutine[Any, Any, dict | CallToolResult]]:
    """Decorator that catches API and network errors, returning structured error envelopes.

    Each error includes an ``error_type`` string so the LLM can decide
    whether to retry, rephrase, or give up:

    - ``validation_error`` — bad input params, don't retry
    - ``auth_error`` — bad API key, don't retry
    - ``not_found`` — resource doesn't exist, don't retry
    - ``rate_limited`` — too many requests, retry after delay
    - ``timeout`` — request timed out, retry with smaller range/limit
    - ``upstream_error`` — DS API 5xx, retry once
    - ``network_error`` — connection failed, retry once
    - ``internal_error`` — unexpected, retry once

    On error the decorator returns a ``CallToolResult`` with
    ``isError=True`` so MCP clients that inspect the JSON-RPC envelope
    correctly identify the call as failed. The structured error dict
    is preserved inside the content for LLM consumption.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict | CallToolResult:
        try:
            return await fn(*args, **kwargs)
        except DSApiError as exc:
            detail = redact_secrets(exc.detail)
            logger.warning("DS API error in %s: %s", fn.__name__, detail)
            error_type = _classify_api_error(exc.status_code)
            return _error_result(
                {
                    "error": True,
                    "error_type": error_type,
                    "status_code": exc.status_code,
                    "message": detail,
                    "recovery_hint": _recovery_hint(error_type),
                    "tool": fn.__name__,
                }
            )
        except httpx.TimeoutException:
            logger.warning("Timeout in %s", fn.__name__)
            return _error_result(
                {
                    "error": True,
                    "error_type": "timeout",
                    "status_code": 408,
                    "message": "Request timed out. Try again or use a smaller date range / limit.",
                    "recovery_hint": _recovery_hint("timeout"),
                    "tool": fn.__name__,
                }
            )
        except httpx.HTTPError as exc:
            logger.warning("Network error in %s: %s", fn.__name__, type(exc).__name__)
            return _error_result(
                {
                    "error": True,
                    "error_type": "network_error",
                    "status_code": 0,
                    "message": f"Network error: {type(exc).__name__}",
                    "recovery_hint": _recovery_hint("network_error"),
                    "tool": fn.__name__,
                }
            )
        except Exception:
            logger.exception("Unexpected error in %s", fn.__name__)
            return _error_result(
                {
                    "error": True,
                    "error_type": "internal_error",
                    "status_code": 500,
                    "message": "Internal error. Please try again.",
                    "recovery_hint": _recovery_hint("internal_error"),
                    "tool": fn.__name__,
                }
            )

    return wrapper


# ── Hint helpers ──────────────────────────────────────────────────


def build_hints(
    *,
    total_count: int | None = None,
    returned_count: int | None = None,
    truncated: bool = False,
    page_num: int | None = None,
    limit: int | None = None,
    extra: list[str] | None = None,
) -> list[str]:
    """Build context-aware hint strings for tool responses.

    Handles common cases automatically (empty results, pagination,
    truncation) and appends any tool-specific ``extra`` hints.
    """
    hints: list[str] = []

    # Empty results
    if returned_count is not None and returned_count == 0:
        hints.append("No results returned. Try adjusting date range, search_engine, or filters.")
        if extra:
            hints.extend(extra)
        return hints

    # Truncation (max_results_per_tool_call cap hit)
    if truncated and returned_count is not None:
        hints.append(
            f"Results were truncated to {returned_count} rows. "
            "Use limit and page_num to paginate through all results."
        )

    # Pagination: more pages available
    if (
        total_count is not None
        and returned_count is not None
        and page_num is not None
        and limit is not None
        and total_count > 0
    ):
        fetched_so_far = (page_num - 1) * limit + returned_count
        if fetched_so_far < total_count:
            remaining = total_count - fetched_so_far
            hints.append(
                f"Page {page_num} of results. {remaining} more rows available. "
                f"Set page_num={page_num + 1} to fetch the next page."
            )

    # Tool-specific extras
    if extra:
        hints.extend(extra)

    return hints


def attach_hints(response: dict, hints: list[str]) -> dict:
    """Attach hints to a tool response dict.

    Skips if response is an error or hints list is empty.
    """
    if response.get("error"):
        return response
    if hints:
        response["hints"] = hints
    return response


def _classify_api_error(status_code: int) -> str:
    """Map HTTP status codes to error types for LLM consumption."""
    if status_code == 400:
        return "validation_error"
    if status_code == 401:
        return "auth_error"
    if status_code == 403:
        return "auth_error"
    if status_code == 404:
        return "not_found"
    if status_code == 429:
        return "rate_limited"
    if status_code >= 500:
        return "upstream_error"
    return "upstream_error"
