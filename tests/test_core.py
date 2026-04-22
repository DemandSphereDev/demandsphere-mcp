"""Unit tests for core components: validators, response shaping, error handling, rate limiter, redaction."""

from __future__ import annotations

import httpx
import pytest

from demandsphere_mcp.client import (
    DSApiError,
    DSClient,
    RateLimiter,
    _flatten_row,
    validate_path_param,
)
from demandsphere_mcp.tools.utils import (
    _classify_api_error,
    clamp_limit,
    redact_secrets,
    redact_url,
    safe_tool,
    validate_date,
    validate_date_range,
    validate_str,
)

# ── validate_date ─────────────────────────────────────────────────


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("2025-01-15") == "2025-01-15"

    def test_valid_leap_day(self):
        assert validate_date("2024-02-29") == "2024-02-29"

    def test_invalid_format(self):
        with pytest.raises(DSApiError, match="Invalid date"):
            validate_date("01-15-2025")

    def test_invalid_string(self):
        with pytest.raises(DSApiError):
            validate_date("not-a-date")

    def test_empty_string(self):
        with pytest.raises(DSApiError):
            validate_date("")

    def test_custom_name(self):
        with pytest.raises(DSApiError, match="target_date"):
            validate_date("bad", "target_date")


# ── validate_date_range ───────────────────────────────────────────


class TestValidateDateRange:
    def test_valid_range(self):
        validate_date_range("2025-01-01", "2025-01-31")

    def test_none_dates_ok(self):
        validate_date_range(None, None)
        validate_date_range("2025-01-01", None)
        validate_date_range(None, "2025-01-31")

    def test_from_after_to(self):
        with pytest.raises(DSApiError, match="must be before"):
            validate_date_range("2025-02-01", "2025-01-01")

    def test_exceeds_max_range(self):
        with pytest.raises(DSApiError, match="365 day maximum"):
            validate_date_range("2024-01-01", "2025-06-01")

    def test_invalid_from_format(self):
        with pytest.raises(DSApiError, match="from_date"):
            validate_date_range("bad", "2025-01-01")

    def test_invalid_to_format(self):
        with pytest.raises(DSApiError, match="to_date"):
            validate_date_range("2025-01-01", "bad")

    def test_same_day_ok(self):
        validate_date_range("2025-06-15", "2025-06-15")

    def test_exactly_365_days(self):
        validate_date_range("2025-01-01", "2025-12-31")


# ── validate_str ──────────────────────────────────────────────────


class TestValidateStr:
    def test_valid_string(self):
        assert validate_str("hello", "param") == "hello"

    def test_strips_whitespace(self):
        assert validate_str("  hello  ", "param") == "hello"

    def test_empty_string(self):
        with pytest.raises(DSApiError, match="must not be empty"):
            validate_str("", "site_id")

    def test_whitespace_only(self):
        with pytest.raises(DSApiError, match="must not be empty"):
            validate_str("   ", "site_id")


# ── clamp_limit ───────────────────────────────────────────────────


class TestClampLimit:
    def test_within_range(self):
        assert clamp_limit(25) == 25

    def test_zero_becomes_one(self):
        assert clamp_limit(0) == 1

    def test_negative_becomes_one(self):
        assert clamp_limit(-5) == 1

    def test_very_large_clamped(self):
        result = clamp_limit(999999)
        assert result <= 100  # default max_results_per_tool_call


# ── validate_path_param ───────────────────────────────────────────


class TestValidatePathParam:
    def test_valid_alphanumeric(self):
        assert validate_path_param("site123") == "site123"

    def test_valid_with_hyphens(self):
        assert validate_path_param("my-site-key") == "my-site-key"

    def test_valid_with_underscores(self):
        assert validate_path_param("my_site_key") == "my_site_key"

    def test_valid_with_dots(self):
        assert validate_path_param("site.key.v2") == "site.key.v2"

    def test_empty_string(self):
        with pytest.raises(DSApiError):
            validate_path_param("")

    def test_path_traversal_dotdot(self):
        with pytest.raises(DSApiError, match="traversal"):
            validate_path_param("..")

    def test_path_traversal_embedded(self):
        with pytest.raises(DSApiError, match="traversal"):
            validate_path_param("foo..bar")

    def test_single_dot(self):
        with pytest.raises(DSApiError, match="traversal"):
            validate_path_param(".")

    def test_special_chars_rejected(self):
        with pytest.raises(DSApiError):
            validate_path_param("site/key")

    def test_spaces_rejected(self):
        with pytest.raises(DSApiError):
            validate_path_param("site key")


# ── redact_url ────────────────────────────────────────────────────


class TestRedactUrl:
    def test_strips_query_params(self):
        result = redact_url("https://api.example.com/path?api_key=secret&foo=bar")
        assert "secret" not in result
        assert "[REDACTED]" in result

    def test_no_query_params(self):
        result = redact_url("https://api.example.com/path")
        assert result == "https://api.example.com/path"
        assert "[REDACTED]" not in result

    def test_preserves_path(self):
        result = redact_url("https://api.example.com/v5/keywords?key=val")
        assert "/v5/keywords" in result


# ── redact_secrets ────────────────────────────────────────────────


class TestRedactSecrets:
    def test_scrubs_api_key(self):
        result = redact_secrets("api_key=abc123def456 some text")
        assert "abc123" not in result
        assert "api_key=[REDACTED]" in result

    def test_no_api_key(self):
        result = redact_secrets("some normal text")
        assert result == "some normal text"

    def test_multiple_occurrences(self):
        result = redact_secrets("api_key=first&api_key=second")
        assert "first" not in result
        assert "second" not in result

    def test_case_insensitive(self):
        result = redact_secrets("API_KEY=secret123")
        assert "secret123" not in result


# ── _classify_api_error ───────────────────────────────────────────


class TestClassifyApiError:
    def test_400_validation(self):
        assert _classify_api_error(400) == "validation_error"

    def test_401_auth(self):
        assert _classify_api_error(401) == "auth_error"

    def test_403_auth(self):
        assert _classify_api_error(403) == "auth_error"

    def test_404_not_found(self):
        assert _classify_api_error(404) == "not_found"

    def test_429_rate_limited(self):
        assert _classify_api_error(429) == "rate_limited"

    def test_500_upstream(self):
        assert _classify_api_error(500) == "upstream_error"

    def test_502_upstream(self):
        assert _classify_api_error(502) == "upstream_error"

    def test_unknown_status(self):
        assert _classify_api_error(418) == "upstream_error"


# ── safe_tool decorator ──────────────────────────────────────────


class TestSafeTool:
    @pytest.mark.asyncio
    async def test_passes_through_success(self):
        @safe_tool
        async def good_tool() -> dict:
            return {"data": "ok"}

        result = await good_tool()
        assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_catches_ds_api_error(self):
        @safe_tool
        async def bad_tool() -> dict:
            raise DSApiError(401, "Invalid API key")

        result = await bad_tool()
        assert result["error"] is True
        assert result["error_type"] == "auth_error"
        assert result["status_code"] == 401
        assert result["tool"] == "bad_tool"
        assert "recovery_hint" in result
        assert "DEMANDSPHERE_API_KEY" in result["recovery_hint"]

    @pytest.mark.asyncio
    async def test_catches_timeout(self):
        @safe_tool
        async def timeout_tool() -> dict:
            raise httpx.ReadTimeout("read timeout")

        result = await timeout_tool()
        assert result["error"] is True
        assert result["error_type"] == "timeout"
        assert "recovery_hint" in result
        assert "smaller date range" in result["recovery_hint"]

    @pytest.mark.asyncio
    async def test_catches_network_error(self):
        @safe_tool
        async def net_tool() -> dict:
            raise httpx.ConnectError("connection refused")

        result = await net_tool()
        assert result["error"] is True
        assert result["error_type"] == "network_error"
        assert "recovery_hint" in result
        assert "connectivity" in result["recovery_hint"]

    @pytest.mark.asyncio
    async def test_catches_unexpected_error(self):
        @safe_tool
        async def crash_tool() -> dict:
            raise RuntimeError("unexpected")

        result = await crash_tool()
        assert result["error"] is True
        assert result["error_type"] == "internal_error"
        assert result["status_code"] == 500
        assert "recovery_hint" in result
        assert "Retry once" in result["recovery_hint"]

    @pytest.mark.asyncio
    async def test_redacts_api_key_in_error(self):
        @safe_tool
        async def leaky_tool() -> dict:
            raise DSApiError(400, "Bad request at url?api_key=secret123")

        result = await leaky_tool()
        assert "secret123" not in result["message"]
        assert "api_key=[REDACTED]" in result["message"]

    @pytest.mark.asyncio
    async def test_recovery_hint_validation_error(self):
        @safe_tool
        async def val_tool() -> dict:
            raise DSApiError(400, "Invalid date format")

        result = await val_tool()
        assert result["error_type"] == "validation_error"
        assert "YYYY-MM-DD" in result["recovery_hint"]

    @pytest.mark.asyncio
    async def test_recovery_hint_not_found(self):
        @safe_tool
        async def missing_tool() -> dict:
            raise DSApiError(404, "Site not found")

        result = await missing_tool()
        assert result["error_type"] == "not_found"
        assert "list_sites" in result["recovery_hint"]

    @pytest.mark.asyncio
    async def test_recovery_hint_rate_limited(self):
        @safe_tool
        async def throttled_tool() -> dict:
            raise DSApiError(429, "Too many requests")

        result = await throttled_tool()
        assert result["error_type"] == "rate_limited"
        assert "Wait" in result["recovery_hint"]

    @pytest.mark.asyncio
    async def test_recovery_hint_upstream_error(self):
        @safe_tool
        async def upstream_tool() -> dict:
            raise DSApiError(502, "Bad gateway")

        result = await upstream_tool()
        assert result["error_type"] == "upstream_error"
        assert "server error" in result["recovery_hint"]


# ── shape_tabular ─────────────────────────────────────────────────


class TestShapeTabular:
    def test_extracts_and_flattens(self):
        raw = {
            "tabularData": [
                {
                    "results": [
                        {"keyword": {"value": "seo", "label": "Keyword"}},
                        {"keyword": {"value": "mcp", "label": "Keyword"}},
                    ],
                    "page_info": {"total_count": 100},
                }
            ]
        }
        result = DSClient.shape_tabular(raw, max_rows=10)
        assert result["total_count"] == 100
        assert result["returned_count"] == 2
        assert result["truncated"] is False
        assert result["results"][0] == {"keyword": "seo"}
        assert result["results"][1] == {"keyword": "mcp"}

    def test_truncates_when_over_cap(self):
        results = [{"kw": {"value": f"kw{i}"}} for i in range(20)]
        raw = {"tabularData": [{"results": results, "page_info": {"total_count": 200}}]}
        result = DSClient.shape_tabular(raw, max_rows=5)
        assert result["returned_count"] == 5
        assert result["truncated"] is True
        assert result["total_count"] == 200

    def test_no_tabular_data_returns_raw(self):
        raw = {"some_other": "data"}
        assert DSClient.shape_tabular(raw) == raw

    def test_empty_tabular_array(self):
        raw = {"tabularData": []}
        assert DSClient.shape_tabular(raw) == raw

    def test_total_count_fallback(self):
        """When page_info is missing, total_count falls back to len(results)."""
        raw = {
            "tabularData": [
                {
                    "results": [{"kw": {"value": "a"}}, {"kw": {"value": "b"}}],
                }
            ]
        }
        result = DSClient.shape_tabular(raw, max_rows=10)
        assert result["total_count"] == 2


# ── shape_v51 ─────────────────────────────────────────────────────


class TestShapeV51:
    def test_success_with_dict_data(self):
        raw = {"status": "ok", "data": {"records": [1, 2, 3]}}
        result = DSClient.shape_v51(raw)
        assert result == {"records": [1, 2, 3]}

    def test_success_with_list_data(self):
        raw = {"status": "success", "data": [1, 2, 3]}
        result = DSClient.shape_v51(raw)
        assert result == {"records": [1, 2, 3]}

    def test_error_status(self):
        raw = {"status": "error", "message": "Something went wrong"}
        result = DSClient.shape_v51(raw)
        assert result["error"] is True
        assert result["status"] == "error"
        assert result["message"] == "Something went wrong"

    def test_error_missing_message(self):
        raw = {"status": "failed"}
        result = DSClient.shape_v51(raw)
        assert result["error"] is True
        assert result["message"] == "Unknown error"

    def test_no_status_no_data(self):
        raw = {"something": "else"}
        result = DSClient.shape_v51(raw)
        assert result == raw

    def test_no_status_with_data(self):
        raw = {"data": {"key": "val"}}
        result = DSClient.shape_v51(raw)
        assert result == {"key": "val"}


# ── _flatten_row ──────────────────────────────────────────────────


class TestFlattenRow:
    def test_extracts_value(self):
        row = {"keyword": {"value": "seo", "label": "Keyword", "dataType": "string"}}
        assert _flatten_row(row) == {"keyword": "seo"}

    def test_passes_through_plain(self):
        row = {"count": 42}
        assert _flatten_row(row) == {"count": 42}

    def test_handles_list_of_dicts(self):
        row = {"tags": [{"value": "a"}, {"value": "b"}]}
        assert _flatten_row(row) == {"tags": ["a", "b"]}

    def test_handles_list_of_plain(self):
        row = {"tags": ["a", "b"]}
        assert _flatten_row(row) == {"tags": ["a", "b"]}

    def test_mixed_row(self):
        row = {
            "keyword": {"value": "seo", "label": "KW"},
            "rank": 5,
            "tags": [{"value": "branded"}, "generic"],
        }
        result = _flatten_row(row)
        assert result == {"keyword": "seo", "rank": 5, "tags": ["branded", "generic"]}


# ── RateLimiter ───────────────────────────────────────────────────


class TestRateLimiter:
    def test_default_burst(self):
        limiter = RateLimiter(60)
        assert limiter._burst == 10  # 60 // 6

    def test_custom_burst(self):
        limiter = RateLimiter(60, max_burst=5)
        assert limiter._burst == 5

    def test_min_burst(self):
        limiter = RateLimiter(1)
        assert limiter._burst == 1  # max(1, 1//6) = 1

    @pytest.mark.asyncio
    async def test_acquire_consumes_token(self):
        limiter = RateLimiter(60, max_burst=3)
        limiter._tokens = 3.0
        await limiter.acquire()
        assert limiter._tokens < 3.0

    @pytest.mark.asyncio
    async def test_burst_acquires_succeed(self):
        """Multiple acquires within burst limit should not block significantly."""
        limiter = RateLimiter(600, max_burst=10)
        for _ in range(5):
            await limiter.acquire()


# ── DSApiError ────────────────────────────────────────────────────


class TestDSApiError:
    def test_attributes(self):
        err = DSApiError(404, "Not found")
        assert err.status_code == 404
        assert err.detail == "Not found"

    def test_str_representation(self):
        err = DSApiError(500, "Server error")
        assert "500" in str(err)
        assert "Server error" in str(err)


class TestCreateAsgiApp:
    def test_returns_asgi_app_without_touching_default_client(self):
        from starlette.applications import Starlette

        from demandsphere_mcp import client as _client_mod
        from demandsphere_mcp.server import create_asgi_app

        _client_mod._default_client = None
        app = create_asgi_app()

        assert isinstance(app, Starlette)
        # Critical contract: embedding apps install their own middleware, so
        # create_asgi_app() must NOT install a default client behind their back.
        assert _client_mod._default_client is None
