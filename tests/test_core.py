"""Tests for demandsphere-mcp.

Covers: imports, config loading, response shaping, path validation,
rate limiter, LRU cache, error handling decorator.
"""

from __future__ import annotations

import asyncio
import pytest


# ── Import smoke tests ────────────────────────────────────────────────

def test_import_package():
    import demandsphere_mcp
    assert hasattr(demandsphere_mcp, "__version__")


def test_import_config():
    from demandsphere_mcp.config import Settings
    s = Settings(api_key="test", base_url="https://example.com")
    assert s.api_key == "test"
    assert s.transport == "stdio"


def test_import_client():
    from demandsphere_mcp.client import DSClient, DSApiError, validate_path_param
    assert DSClient is not None


def test_import_server():
    """Server module should import without side effects (no sys.exit)."""
    from demandsphere_mcp.server import create_server
    assert callable(create_server)


def test_import_tools():
    from demandsphere_mcp.tools import sites, keywords_v50, genai_v51, brands_v51, chatgpt_compat
    assert callable(sites.register)


# ── Path validation (#4) ──────────────────────────────────────────────

def test_validate_path_param_valid():
    from demandsphere_mcp.client import validate_path_param
    assert validate_path_param("abc123", "test") == "abc123"
    assert validate_path_param("e6e1f8c13bd4", "key") == "e6e1f8c13bd4"
    assert validate_path_param("my-site_key.v2", "key") == "my-site_key.v2"


def test_validate_path_param_rejects_traversal():
    from demandsphere_mcp.client import validate_path_param, DSApiError
    with pytest.raises(DSApiError, match="Invalid"):
        validate_path_param("../../admin", "site_key")


def test_validate_path_param_rejects_slashes():
    from demandsphere_mcp.client import validate_path_param, DSApiError
    with pytest.raises(DSApiError, match="Invalid"):
        validate_path_param("foo/bar", "site_key")


def test_validate_path_param_rejects_empty():
    from demandsphere_mcp.client import validate_path_param, DSApiError
    with pytest.raises(DSApiError, match="Invalid"):
        validate_path_param("", "site_key")


def test_validate_path_param_rejects_spaces():
    from demandsphere_mcp.client import validate_path_param, DSApiError
    with pytest.raises(DSApiError, match="Invalid"):
        validate_path_param("foo bar", "site_key")


# ── Response shaping (#9, #15) ────────────────────────────────────────

def test_shape_tabular_normal():
    from demandsphere_mcp.client import DSClient
    raw = {
        "tabularData": [{
            "results": [
                {"keyword_name": {"label": "Keyword", "value": "laptop", "dataType": "string"}},
                {"keyword_name": {"label": "Keyword", "value": "desktop", "dataType": "string"}},
            ],
            "page_info": {"total_count": 2, "returned_count": 2},
        }]
    }
    shaped = DSClient.shape_tabular(raw, max_rows=10)
    assert shaped["total_count"] == 2
    assert shaped["returned_count"] == 2
    assert shaped["results"][0]["keyword_name"] == "laptop"
    assert not shaped["truncated"]


def test_shape_tabular_truncation():
    from demandsphere_mcp.client import DSClient
    raw = {
        "tabularData": [{
            "results": [{"kw": {"value": f"kw{i}"}} for i in range(50)],
            "page_info": {"total_count": 50},
        }]
    }
    shaped = DSClient.shape_tabular(raw, max_rows=5)
    assert shaped["returned_count"] == 5
    assert shaped["truncated"] is True


def test_shape_tabular_empty_array():
    """Fix #15 — should not crash on empty tabularData array."""
    from demandsphere_mcp.client import DSClient
    raw = {"tabularData": []}
    shaped = DSClient.shape_tabular(raw)
    assert shaped == raw  # pass-through


def test_shape_tabular_missing_key():
    from demandsphere_mcp.client import DSClient
    raw = {"something_else": 123}
    shaped = DSClient.shape_tabular(raw)
    assert shaped == raw


def test_shape_v51_success():
    from demandsphere_mcp.client import DSClient
    raw = {"status": "success", "message": "ok", "data": {"records": [1, 2, 3]}}
    shaped = DSClient.shape_v51(raw)
    assert shaped == {"records": [1, 2, 3]}


def test_shape_v51_error_status():
    """Fix #9 — should detect error status in 200 responses."""
    from demandsphere_mcp.client import DSClient
    raw = {"status": "error", "message": "Site not found"}
    shaped = DSClient.shape_v51(raw)
    assert shaped["error"] is True
    assert shaped["message"] == "Site not found"


def test_shape_v51_data_array():
    from demandsphere_mcp.client import DSClient
    raw = {"status": "success", "data": [1, 2, 3]}
    shaped = DSClient.shape_v51(raw)
    assert shaped == {"records": [1, 2, 3]}


# ── LRU cache (#3) ───────────────────────────────────────────────────

def test_lru_cache_basic():
    from demandsphere_mcp.tools.chatgpt_compat import _LRUCache
    cache = _LRUCache(max_size=3)
    cache.put("a", {"v": 1})
    cache.put("b", {"v": 2})
    cache.put("c", {"v": 3})
    assert cache.get("a")["v"] == 1


def test_lru_cache_eviction():
    from demandsphere_mcp.tools.chatgpt_compat import _LRUCache
    cache = _LRUCache(max_size=2)
    cache.put("a", {"v": 1})
    cache.put("b", {"v": 2})
    cache.put("c", {"v": 3})  # evicts "a"
    assert cache.get("a") is None
    assert cache.get("b")["v"] == 2
    assert cache.get("c")["v"] == 3


def test_lru_cache_access_refreshes():
    from demandsphere_mcp.tools.chatgpt_compat import _LRUCache
    cache = _LRUCache(max_size=2)
    cache.put("a", {"v": 1})
    cache.put("b", {"v": 2})
    cache.get("a")  # refresh "a"
    cache.put("c", {"v": 3})  # evicts "b" (not "a")
    assert cache.get("a")["v"] == 1
    assert cache.get("b") is None


# ── Rate limiter ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limiter_allows_burst_up_to_cap():
    from demandsphere_mcp.client import RateLimiter
    limiter = RateLimiter(max_per_minute=60, max_burst=5)
    # Should allow 5 quick acquires (the burst cap)
    for _ in range(5):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_rate_limiter_default_burst_is_sixth_of_max():
    from demandsphere_mcp.client import RateLimiter
    limiter = RateLimiter(max_per_minute=60)
    assert limiter._burst == 10  # 60 // 6


@pytest.mark.asyncio
async def test_rate_limiter_burst_caps_tokens():
    from demandsphere_mcp.client import RateLimiter
    limiter = RateLimiter(max_per_minute=60, max_burst=3)
    # Tokens start at burst cap (3), not max_per_minute (60)
    assert limiter._tokens == 3.0


# ── Error handling decorator (#10) ────────────────────────────────────

@pytest.mark.asyncio
async def test_safe_tool_catches_api_error():
    from demandsphere_mcp.tools.utils import safe_tool
    from demandsphere_mcp.client import DSApiError

    @safe_tool
    async def failing_tool() -> dict:
        raise DSApiError(403, "Forbidden")

    result = await failing_tool()
    assert result["error"] is True
    assert result["status_code"] == 403
    assert result["error_type"] == "auth_error"


@pytest.mark.asyncio
async def test_safe_tool_catches_generic_exception():
    from demandsphere_mcp.tools.utils import safe_tool

    @safe_tool
    async def crashing_tool() -> dict:
        raise ValueError("boom")

    result = await crashing_tool()
    assert result["error"] is True
    assert result["status_code"] == 500
    assert result["error_type"] == "internal_error"
    assert "boom" not in result["message"]  # no stack trace / internals leak


@pytest.mark.asyncio
async def test_safe_tool_timeout_error_type():
    import httpx
    from demandsphere_mcp.tools.utils import safe_tool

    @safe_tool
    async def timeout_tool() -> dict:
        raise httpx.ReadTimeout("read timed out")

    result = await timeout_tool()
    assert result["error_type"] == "timeout"


@pytest.mark.asyncio
async def test_safe_tool_error_never_leaks_internals():
    from demandsphere_mcp.tools.utils import safe_tool

    @safe_tool
    async def internal_error_tool() -> dict:
        raise RuntimeError("internal traceback with /path/to/secrets.py line 42")

    result = await internal_error_tool()
    # Generic message only — no traceback, no file paths
    assert result["message"] == "Internal error. Please try again."
    assert "/path/to" not in str(result)
    assert "traceback" not in str(result).lower()


@pytest.mark.asyncio
async def test_safe_tool_passes_through_success():
    from demandsphere_mcp.tools.utils import safe_tool

    @safe_tool
    async def good_tool() -> dict:
        return {"data": "ok"}

    result = await good_tool()
    assert result == {"data": "ok"}


# ── Flatten row ───────────────────────────────────────────────────────

def test_flatten_row():
    from demandsphere_mcp.client import _flatten_row
    row = {
        "keyword_name": {"label": "Keyword", "value": "laptop", "dataType": "string"},
        "rank": {"label": "Rank", "value": 3, "dataType": "integer"},
        "features": [
            {"label": "F1", "value": "answer_box", "dataType": "string"},
            {"label": "F2", "value": "knowledge_panel", "dataType": "string"},
        ],
        "raw_field": 42,
    }
    flat = _flatten_row(row)
    assert flat["keyword_name"] == "laptop"
    assert flat["rank"] == 3
    assert flat["features"] == ["answer_box", "knowledge_panel"]
    assert flat["raw_field"] == 42


# ── Limit clamping ────────────────────────────────────────────────────

def test_clamp_limit():
    from demandsphere_mcp.tools.utils import clamp_limit
    assert clamp_limit(25) == 25
    assert clamp_limit(100000) == 100  # default max_results_per_tool_call
    assert clamp_limit(0) == 1
    assert clamp_limit(-5) == 1


# ── User-Agent header ────────────────────────────────────────────────

def test_client_user_agent():
    from demandsphere_mcp.client import DSClient
    from demandsphere_mcp import __version__
    client = DSClient(api_key="test", base_url="https://example.com")
    assert client._http.headers["user-agent"] == f"demandsphere-mcp/{__version__}"


# ── Centralized input gating ─────────────────────────────────────────


def test_validate_date_range_valid():
    from demandsphere_mcp.tools.utils import validate_date_range
    # Should not raise
    validate_date_range("2025-01-01", "2025-06-01")
    validate_date_range(None, None)
    validate_date_range("2025-01-01", None)


def test_validate_date_range_too_wide():
    from demandsphere_mcp.tools.utils import validate_date_range
    from demandsphere_mcp.client import DSApiError
    with pytest.raises(DSApiError, match="exceeds"):
        validate_date_range("2020-01-01", "2025-12-31")


def test_validate_date_range_inverted():
    from demandsphere_mcp.tools.utils import validate_date_range
    from demandsphere_mcp.client import DSApiError
    with pytest.raises(DSApiError, match="must be before"):
        validate_date_range("2025-06-01", "2025-01-01")


def test_validate_date_range_bad_format():
    from demandsphere_mcp.tools.utils import validate_date_range
    from demandsphere_mcp.client import DSApiError
    with pytest.raises(DSApiError, match="Invalid from_date"):
        validate_date_range("not-a-date", "2025-01-01")


def test_validate_str_rejects_empty():
    from demandsphere_mcp.tools.utils import validate_str
    from demandsphere_mcp.client import DSApiError
    with pytest.raises(DSApiError, match="must not be empty"):
        validate_str("", "global_key")
    with pytest.raises(DSApiError, match="must not be empty"):
        validate_str("   ", "global_key")


def test_validate_str_passes():
    from demandsphere_mcp.tools.utils import validate_str
    assert validate_str("abc123", "key") == "abc123"
    assert validate_str("  padded  ", "key") == "padded"


def test_redact_url():
    from demandsphere_mcp.tools.utils import redact_url
    assert redact_url("https://api.example.com/foo?api_key=SECRET&bar=baz") == \
        "https://api.example.com/foo?[REDACTED]"
    assert redact_url("https://api.example.com/foo") == \
        "https://api.example.com/foo"


# ── Error type classification ─────────────────────────────────────────

def test_classify_api_error():
    from demandsphere_mcp.tools.utils import _classify_api_error
    assert _classify_api_error(400) == "validation_error"
    assert _classify_api_error(401) == "auth_error"
    assert _classify_api_error(403) == "auth_error"
    assert _classify_api_error(404) == "not_found"
    assert _classify_api_error(429) == "rate_limited"
    assert _classify_api_error(500) == "upstream_error"
    assert _classify_api_error(502) == "upstream_error"
    assert _classify_api_error(503) == "upstream_error"


# ── Retry jitter ──────────────────────────────────────────────────────

def test_retry_delay_has_jitter():
    from demandsphere_mcp.client import _retry_delay
    # Call multiple times — values should vary due to jitter
    delays = [_retry_delay(0) for _ in range(20)]
    # Base delay for attempt 0 is 1.0, jitter adds 0-0.25
    assert all(1.0 <= d <= 1.25 for d in delays)
    # With jitter, not all values should be identical
    assert len(set(round(d, 4) for d in delays)) > 1


def test_retry_delay_exponential():
    from demandsphere_mcp.client import _retry_delay
    d0 = _retry_delay(0)
    d1 = _retry_delay(1)
    d2 = _retry_delay(2)
    # attempt 0: ~1.0-1.25, attempt 1: ~2.0-2.25, attempt 2: ~4.0-4.25
    assert 1.0 <= d0 <= 1.25
    assert 2.0 <= d1 <= 2.25
    assert 4.0 <= d2 <= 4.25


# ── Granular timeouts ─────────────────────────────────────────────────

def test_client_uses_granular_timeout():
    import httpx
    from demandsphere_mcp.client import DSClient
    client = DSClient(api_key="test", base_url="https://example.com")
    timeout = client._http.timeout
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 5.0
    assert timeout.pool == 5.0


# ── Secret redaction ──────────────────────────────────────────────────

def test_redact_secrets_strips_api_key():
    from demandsphere_mcp.tools.utils import redact_secrets
    assert redact_secrets("error at api_key=SECRET123&foo=bar") == \
        "error at api_key=[REDACTED]&foo=bar"


def test_redact_secrets_no_key_passthrough():
    from demandsphere_mcp.tools.utils import redact_secrets
    assert redact_secrets("normal error message") == "normal error message"


@pytest.mark.asyncio
async def test_safe_tool_redacts_api_key_in_detail():
    from demandsphere_mcp.tools.utils import safe_tool
    from demandsphere_mcp.client import DSApiError

    @safe_tool
    async def leaky_tool() -> dict:
        raise DSApiError(500, "failed at https://api.example.com?api_key=SUPERSECRET")

    result = await leaky_tool()
    assert "SUPERSECRET" not in result["message"]
    assert "api_key=[REDACTED]" in result["message"]


# ── Single date validation ────────────────────────────────────────────

def test_validate_date_valid():
    from demandsphere_mcp.tools.utils import validate_date
    assert validate_date("2025-06-15") == "2025-06-15"


def test_validate_date_bad_format():
    from demandsphere_mcp.tools.utils import validate_date
    from demandsphere_mcp.client import DSApiError
    with pytest.raises(DSApiError, match="Invalid"):
        validate_date("June 15 2025")


def test_validate_date_empty():
    from demandsphere_mcp.tools.utils import validate_date
    from demandsphere_mcp.client import DSApiError
    with pytest.raises(DSApiError, match="Invalid"):
        validate_date("")


# ── Path traversal '..' rejection ─────────────────────────────────────

def test_validate_path_param_rejects_dotdot():
    from demandsphere_mcp.client import validate_path_param, DSApiError
    with pytest.raises(DSApiError, match="traversal"):
        validate_path_param("..", "site_key")


def test_validate_path_param_rejects_single_dot():
    from demandsphere_mcp.client import validate_path_param, DSApiError
    with pytest.raises(DSApiError, match="traversal"):
        validate_path_param(".", "site_key")


def test_validate_path_param_rejects_embedded_dotdot():
    from demandsphere_mcp.client import validate_path_param, DSApiError
    with pytest.raises(DSApiError, match="traversal"):
        validate_path_param("abc..def", "site_key")


# ── Date range: single date validation when other is None ─────────────

def test_validate_date_range_bad_from_with_none_to():
    from demandsphere_mcp.tools.utils import validate_date_range
    from demandsphere_mcp.client import DSApiError
    with pytest.raises(DSApiError, match="Invalid from_date"):
        validate_date_range("not-a-date", None)


def test_validate_date_range_bad_to_with_none_from():
    from demandsphere_mcp.tools.utils import validate_date_range
    from demandsphere_mcp.client import DSApiError
    with pytest.raises(DSApiError, match="Invalid to_date"):
        validate_date_range(None, "not-a-date")


def test_validate_date_range_valid_from_with_none_to():
    from demandsphere_mcp.tools.utils import validate_date_range
    # Should not raise
    validate_date_range("2025-06-01", None)
