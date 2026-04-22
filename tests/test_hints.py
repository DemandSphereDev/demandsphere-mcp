"""Tests for the build_hints() and attach_hints() utility functions."""

from __future__ import annotations

from demandsphere_mcp.tools.utils import attach_hints, build_hints

# ── build_hints tests ─────────────────────────────────────────────


class TestBuildHints:
    def test_no_args_returns_empty(self):
        assert build_hints() == []

    def test_empty_results(self):
        hints = build_hints(returned_count=0)
        assert len(hints) == 1
        assert "No results" in hints[0]

    def test_empty_results_with_extra(self):
        hints = build_hints(returned_count=0, extra=["Try a different date."])
        assert len(hints) == 2
        assert "No results" in hints[0]
        assert hints[1] == "Try a different date."

    def test_empty_results_skips_pagination(self):
        """When returned_count=0, pagination hints should not appear."""
        hints = build_hints(
            total_count=100,
            returned_count=0,
            page_num=1,
            limit=25,
        )
        assert len(hints) == 1
        assert "page_num" not in hints[0]

    def test_truncated(self):
        hints = build_hints(returned_count=100, truncated=True)
        assert any("truncated" in h.lower() for h in hints)
        assert any("100" in h for h in hints)

    def test_not_truncated_no_hint(self):
        hints = build_hints(returned_count=25, truncated=False)
        assert not any("truncated" in h.lower() for h in hints)

    def test_pagination_more_pages(self):
        hints = build_hints(
            total_count=100,
            returned_count=25,
            page_num=1,
            limit=25,
        )
        assert any("page_num=2" in h for h in hints)
        assert any("75 more" in h for h in hints)

    def test_pagination_middle_page(self):
        hints = build_hints(
            total_count=100,
            returned_count=25,
            page_num=2,
            limit=25,
        )
        assert any("page_num=3" in h for h in hints)
        assert any("50 more" in h for h in hints)

    def test_pagination_last_page(self):
        hints = build_hints(
            total_count=50,
            returned_count=25,
            page_num=2,
            limit=25,
        )
        assert not any("page_num=" in h for h in hints)

    def test_pagination_exact_fit(self):
        """When total_count equals fetched_so_far, no pagination hint."""
        hints = build_hints(
            total_count=25,
            returned_count=25,
            page_num=1,
            limit=25,
        )
        assert not any("page_num=" in h for h in hints)

    def test_pagination_requires_all_params(self):
        """Pagination hint only appears when all four params are provided."""
        hints = build_hints(total_count=100, returned_count=25)
        assert not any("page_num=" in h for h in hints)

    def test_extra_passthrough(self):
        hints = build_hints(extra=["Use get_mentions for brand data."])
        assert hints == ["Use get_mentions for brand data."]

    def test_multiple_extras(self):
        hints = build_hints(extra=["hint1", "hint2"])
        assert hints == ["hint1", "hint2"]

    def test_combined_truncated_and_pagination(self):
        hints = build_hints(
            total_count=200,
            returned_count=100,
            truncated=True,
            page_num=1,
            limit=100,
            extra=["Custom hint."],
        )
        assert any("truncated" in h.lower() for h in hints)
        assert any("page_num=2" in h for h in hints)
        assert "Custom hint." in hints


# ── attach_hints tests ────────────────────────────────────────────


class TestAttachHints:
    def test_adds_hints_to_response(self):
        resp = {"results": []}
        result = attach_hints(resp, ["hint1", "hint2"])
        assert result["hints"] == ["hint1", "hint2"]
        assert result is resp  # mutates in place

    def test_skips_error_responses(self):
        resp = {"error": True, "error_type": "auth_error", "message": "bad key"}
        result = attach_hints(resp, ["hint1"])
        assert "hints" not in result

    def test_skips_empty_hints(self):
        resp = {"results": []}
        result = attach_hints(resp, [])
        assert "hints" not in result

    def test_preserves_existing_data(self):
        resp = {"results": [1, 2, 3], "total_count": 3}
        attach_hints(resp, ["hint"])
        assert resp["results"] == [1, 2, 3]
        assert resp["total_count"] == 3
        assert resp["hints"] == ["hint"]
