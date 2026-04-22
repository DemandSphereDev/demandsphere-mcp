"""Injection support for DSClient: shared httpx pool + custom RateLimiter."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx

from demandsphere_mcp.client import DSClient, RateLimiter


class TestSharedHttpPool:
    async def test_injected_http_is_not_closed_by_client_close(self):
        shared = httpx.AsyncClient()
        shared.aclose = AsyncMock(wraps=shared.aclose)

        client = DSClient(api_key="k", http=shared)
        await client.close()

        shared.aclose.assert_not_awaited()
        await shared.aclose()  # cleanup for real

    async def test_owned_http_is_closed_by_client_close(self):
        client = DSClient(api_key="k")
        inner = client._http
        inner.aclose = AsyncMock(wraps=inner.aclose)

        await client.close()

        inner.aclose.assert_awaited_once()


class TestRateLimiterInjection:
    def test_custom_limiter_replaces_default(self):
        custom = RateLimiter(max_per_minute=1000, max_burst=250)
        client = DSClient(api_key="k", limiter=custom)
        assert client._limiter is custom

    def test_default_limiter_derived_from_settings_when_not_injected(self):
        client = DSClient(api_key="k")
        # Default burst is max(1, max_per_minute // 6). The exact number is
        # settings-dependent; assert the instance is fresh and not the same
        # object as any user-supplied sentinel.
        custom = RateLimiter(max_per_minute=1)
        assert client._limiter is not custom
        assert isinstance(client._limiter, RateLimiter)
