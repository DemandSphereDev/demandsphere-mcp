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
import logging
import re
from datetime import date
from typing import Any, Callable, Coroutine
from urllib.parse import urlparse, urlunparse

import httpx

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


# ── Tool error handling decorator ─────────────────────────────────────

def safe_tool(fn: Callable[..., Coroutine[Any, Any, dict]]) -> Callable[..., Coroutine[Any, Any, dict]]:
    """Decorator that catches API and network errors, returning structured error dicts.

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
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict:
        try:
            return await fn(*args, **kwargs)
        except DSApiError as exc:
            detail = redact_secrets(exc.detail)
            logger.warning("DS API error in %s: %s", fn.__name__, detail)
            error_type = _classify_api_error(exc.status_code)
            return {
                "error": True,
                "error_type": error_type,
                "status_code": exc.status_code,
                "message": detail,
                "tool": fn.__name__,
            }
        except httpx.TimeoutException:
            logger.warning("Timeout in %s", fn.__name__)
            return {
                "error": True,
                "error_type": "timeout",
                "status_code": 408,
                "message": "Request timed out. Try again or use a smaller date range / limit.",
                "tool": fn.__name__,
            }
        except httpx.HTTPError as exc:
            logger.warning("Network error in %s: %s", fn.__name__, type(exc).__name__)
            return {
                "error": True,
                "error_type": "network_error",
                "status_code": 0,
                "message": f"Network error: {type(exc).__name__}",
                "tool": fn.__name__,
            }
        except Exception:
            logger.exception("Unexpected error in %s", fn.__name__)
            return {
                "error": True,
                "error_type": "internal_error",
                "status_code": 500,
                "message": "Internal error. Please try again.",
                "tool": fn.__name__,
            }

    return wrapper


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
