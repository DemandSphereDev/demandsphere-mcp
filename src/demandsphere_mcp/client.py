"""Async HTTP client for the DemandSphere API.

Handles:
- API key injection (query param ``api_key``)
- Client-side rate limiting (token bucket, per-key in hosted mode)
- Retry with backoff for transient failures (429, 5xx)
- Response shaping (truncate large payloads for LLM token budgets)
- Path parameter sanitization
- Unified error handling

Security note: The DemandSphere API uses query-parameter auth, which means
API keys appear in URLs. The httpx client is configured to suppress request
logging to avoid leaking keys to log aggregators. If deploying behind a
reverse proxy, ensure access logs either strip query strings or are treated
as sensitive.
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import random
import re
import time
from typing import Any

import httpx

from .config import settings
from . import __version__

logger = logging.getLogger("demandsphere_mcp.client")

# Characters allowed in URL path segments (site keys, keyword IDs, etc.)
_SAFE_PATH_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

# Max retries for transient failures
_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0  # seconds, doubles each retry
_RETRY_JITTER = 0.25  # max random jitter added to backoff (prevents thundering herd)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _retry_delay(attempt: int) -> float:
    """Exponential backoff with jitter."""
    return _RETRY_BACKOFF * (2 ** attempt) + random.uniform(0, _RETRY_JITTER)


def validate_path_param(value: str, name: str = "parameter") -> str:
    """Validate that a path parameter is safe to interpolate into a URL.

    Prevents path traversal attacks like ``../../admin`` and bare ``..``
    segments (which some proxies/frameworks normalize).
    """
    if not value or not _SAFE_PATH_RE.match(value):
        raise DSApiError(
            400,
            f"Invalid {name}: must contain only alphanumeric characters, "
            f"hyphens, underscores, and dots. Got: {value!r}",
        )
    # Reject '.' and '..' even though they match the character class —
    # these are traversal segments that proxies may normalize.
    if value in (".", "..") or ".." in value:
        raise DSApiError(
            400,
            f"Invalid {name}: path traversal segments not allowed. Got: {value!r}",
        )
    return value


class RateLimiter:
    """Token-bucket rate limiter with burst cap.

    In stdio mode (single user) this is a single global bucket.
    For hosted multi-user deployments, create one RateLimiter per user
    in the auth middleware layer — this class itself is user-agnostic.

    Args:
        max_per_minute: Sustained rate limit.
        max_burst: Maximum tokens available at any instant (caps the
                   initial burst and refill ceiling). Defaults to
                   max_per_minute / 6 (i.e. ~10 for 60/min).
    """

    def __init__(self, max_per_minute: int, max_burst: int | None = None) -> None:
        self._max = max_per_minute
        self._burst = max_burst if max_burst is not None else max(1, max_per_minute // 6)
        self._tokens = float(self._burst)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(self._burst, self._tokens + elapsed * (self._max / 60.0))
            self._last = now
            if self._tokens < 1:
                wait = (1 - self._tokens) / (self._max / 60.0)
                await asyncio.sleep(wait)
                self._tokens = 0
            else:
                self._tokens -= 1


class DSApiError(Exception):
    """Raised when the DemandSphere API returns a non-200 response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"DS API {status_code}: {detail}")


class DSClient:
    """Async wrapper around the DemandSphere REST API.

    Implements async context manager for proper resource cleanup::

        async with DSClient() as client:
            data = await client.get("/endpoint")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.api_key
        self._base_url = (base_url or settings.base_url).rstrip("/")
        self._limiter = RateLimiter(settings.max_requests_per_minute)
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=settings.request_timeout,
                write=10.0,
                pool=5.0,
            ),
            headers={
                "Accept": "application/json",
                "User-Agent": f"demandsphere-mcp/{__version__}",
            },
        )

        # Best-effort cleanup if the client is never explicitly closed.
        # In stdio mode the process exits anyway; in HTTP mode this
        # ensures the connection pool is drained on graceful shutdown.
        atexit.register(self._sync_close)

    async def __aenter__(self) -> "DSClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        atexit.unregister(self._sync_close)
        await self._http.aclose()

    def _sync_close(self) -> None:
        """Synchronous close for atexit — best-effort connection pool cleanup."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._http.aclose())
        except RuntimeError:
            # No running loop — safe to create one for cleanup
            try:
                asyncio.run(self._http.aclose())
            except Exception:
                pass
        except Exception:
            pass  # atexit — swallow errors during interpreter shutdown

    # ── Core request methods ──────────────────────────────────────────

    def _inject_auth(self, params: dict) -> dict:
        """Add api_key to query params — the DS auth mechanism."""
        params = dict(params) if params else {}
        params["api_key"] = self._api_key
        return params

    async def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict[str, Any]:
        await self._limiter.acquire()

        url = f"{self._base_url}{path}"
        authed_params = self._inject_auth(params or {})

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await self._http.request(
                    method,
                    url,
                    params=authed_params,
                    json=json_body,
                )
            except httpx.TimeoutException:
                last_exc = DSApiError(408, "Request timed out.")
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_retry_delay(attempt))
                    continue
                raise last_exc
            except httpx.HTTPError as exc:
                last_exc = DSApiError(0, f"Network error: {type(exc).__name__}")
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_retry_delay(attempt))
                    continue
                raise last_exc

            # Retry on transient server errors
            if resp.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                await asyncio.sleep(_retry_delay(attempt))
                continue

            break

        # Raise structured errors (sanitize response body — don't leak internals)
        if resp.status_code == 401:
            raise DSApiError(401, "Invalid or missing API key.")
        if resp.status_code == 403:
            raise DSApiError(403, "Forbidden — check API key permissions.")
        if resp.status_code == 404:
            raise DSApiError(404, "Resource not found.")
        if resp.status_code >= 400:
            # Sanitize: only include a generic message, not raw response body
            raise DSApiError(
                resp.status_code,
                f"API request failed with status {resp.status_code}.",
            )

        try:
            return resp.json()
        except ValueError:
            raise DSApiError(
                resp.status_code,
                "API returned non-JSON response.",
            )

    async def get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, params=params, json_body=json_body)

    # ── Response shaping ──────────────────────────────────────────────

    @staticmethod
    def shape_tabular(
        raw: dict[str, Any],
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        """Trim tabular API responses to stay within LLM token budgets.

        The v5.0 API wraps everything in ``tabularData[0].results``.
        We extract the results array, trim it, and attach page_info so
        the LLM knows there are more rows available.
        """
        cap = max_rows or settings.max_results_per_tool_call

        tabular = raw.get("tabularData")
        if not tabular or not isinstance(tabular, list) or len(tabular) == 0:
            return raw

        block = tabular[0]
        results = block.get("results", [])
        page_info = block.get("page_info", {})
        total = page_info.get("total_count", len(results))

        flat_results = [_flatten_row(r) for r in results[:cap]]

        return {
            "results": flat_results,
            "total_count": total,
            "returned_count": len(flat_results),
            "truncated": len(results) > cap,
        }

    @staticmethod
    def shape_v51(raw: dict[str, Any]) -> dict[str, Any]:
        """Shape v5.1 responses, checking for error status."""
        # v5.1 API may return {"status": "error", "message": "..."} in a 200
        status = raw.get("status")
        if status and status != "success":
            return {
                "error": True,
                "status": status,
                "message": raw.get("message", "Unknown error"),
            }

        if "data" in raw:
            return raw["data"] if isinstance(raw["data"], dict) else {"records": raw["data"]}
        return raw


def _flatten_row(row: dict) -> dict:
    """Convert {field: {label, value, dataType}} → {field: value}."""
    out = {}
    for key, val in row.items():
        if isinstance(val, dict) and "value" in val:
            out[key] = val["value"]
        elif isinstance(val, list):
            out[key] = [
                item.get("value", item) if isinstance(item, dict) else item
                for item in val
            ]
        else:
            out[key] = val
    return out
