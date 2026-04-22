"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_client_state():
    """Reset ``_default_client`` between tests so file order is irrelevant.

    ``set_default_client`` mutates a module global in
    ``demandsphere_mcp.client``. Each test that installs a FakeClient via
    ``set_default_client`` would otherwise leak that stub into later tests.

    ContextVar state does not need manual reset — pytest runs each test
    function in a fresh task context, so any ``_current_client.set()`` call
    is automatically scoped to the test.
    """
    from demandsphere_mcp import client as _client_mod

    saved_default = _client_mod._default_client
    try:
        yield
    finally:
        _client_mod._default_client = saved_default
