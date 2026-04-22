"""ContextVar / default-client routing for DSClient resolution."""

from __future__ import annotations

import pytest

from demandsphere_mcp.client import (
    DSClient,
    _current_client,
    get_client,
    set_default_client,
)


class TestGetClientFallback:
    def test_raises_when_no_context_and_no_default(self):
        from demandsphere_mcp import client as _client_mod

        _client_mod._default_client = None
        with pytest.raises(RuntimeError, match="No DSClient in context"):
            get_client()

    def test_returns_default_when_no_context_set(self):
        sentinel = DSClient(api_key="default-key")
        set_default_client(sentinel)
        assert get_client() is sentinel


class TestGetClientContextOverride:
    def test_contextvar_takes_precedence_over_default(self):
        default = DSClient(api_key="default-key")
        scoped = DSClient(api_key="scoped-key")
        set_default_client(default)

        token = _current_client.set(scoped)
        try:
            assert get_client() is scoped
        finally:
            _current_client.reset(token)

        # After reset, the default is visible again.
        assert get_client() is default
