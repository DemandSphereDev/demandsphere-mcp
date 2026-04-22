# Changelog

All notable changes to the DemandSphere MCP Server will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/). Subscribe to releases on GitHub to be notified of updates.

## [0.3.0] - 2026-04-22

### Breaking

- `tools.<module>.register()` no longer takes a `client` argument. Every tool module's `register(mcp: FastMCP, client: DSClient)` is now `register(mcp: FastMCP)`. Tools resolve the active `DSClient` at call time via `get_client()` instead of closing over a pre-bound instance. Downstream code that imported and called `register(mcp, client)` directly must drop the second argument.

### Added

- `demandsphere_mcp.client.get_client()` — returns the active `DSClient`, preferring the request-scoped `_current_client` ContextVar over the process-wide `_default_client`. Raises `RuntimeError` with an actionable message if neither is installed.
- `demandsphere_mcp.client.set_default_client(client)` — installs the process-wide fallback `DSClient` for stdio and single-tenant streamable-HTTP bootstrap.
- `demandsphere_mcp.client._current_client` — `ContextVar[DSClient]` that external ASGI middleware can populate per request for hosted multi-tenant deployments.
- `DSClient(http=..., limiter=...)` — optional dependency-injection parameters so embedding apps can share a single `httpx.AsyncClient` pool and attach per-user `RateLimiter` instances. `DSClient` tracks pool ownership via a private `_owns_http` flag and skips both the `atexit` cleanup and `aclose()` when the pool is borrowed.
- `demandsphere_mcp.server.create_asgi_app() -> Starlette` — returns the Starlette ASGI app for mounting the MCP inside a larger ASGI stack. Intentionally does not install a default client so that a missing middleware wiring surfaces as a clear error rather than silently routing every tenant through one client.

### Changed

- `create_server()` is now pure — it registers tools without constructing a `DSClient` and never calls `sys.exit`. Safe to import and call from tests or embedding code.
- `main()` now orchestrates the stdio / single-tenant bootstrap: `_check_config()` → `set_default_client(DSClient())` → `create_server()` → transport dispatch.
- Removed the `_get_server()` lazy singleton and `_server` module global from `server.py`; `create_server()` is cheap enough to call once at bootstrap.

### Compatibility

- Self-hosters running `demandsphere-mcp` in stdio or single-tenant streamable-HTTP mode are unaffected. No new required environment variables, no changed CLI invocation, no changed exit codes. The existing `DEMANDSPHERE_API_KEY` / config-file / `.env` precedence is preserved.

## [0.2.0] - 2026-03-11

### Changed

- Consolidated 4 SERP tools into `serp_analytics(view=...)` and 5 LLM traffic tools into `llm_analytics(view=...)`, reducing tool count from 27 to 20
- All hint strings, prompts, and resources updated to reference new consolidated tool names

### Added

- Dynamic hints on all tool responses with pagination guidance and next-step suggestions
- Recovery hints on all error responses mapping error types to actionable guidance
- `dry_run` support on brand mutation tools (`create_brand`, `update_brand`, `delete_brands`)
- 4 MCP Prompts: `weekly-ranking-report`, `genai-visibility-check`, `competitor-gap`, `landing-page-audit`
- 5 MCP Resources for parameter discovery: `data://search-engines`, `data://sort-options`, `data://granularity`, `data://metrics`, `data://sites`
- 169 unit tests (up from 0)

## [0.1.0] - 2026-03-04

### Added

- Initial beta release
- 27 MCP tools across 5 domains: Site Discovery, SERP Analytics (v5.0), GenAI Visibility (v5.1), Brand Management (v5.1), ChatGPT Deep Research compatibility
- Async HTTP client with token-bucket rate limiting and response shaping
- stdio transport for local use (Claude Code, Claude Desktop, Cursor)
- Streamable HTTP transport for remote/hosted deployment
- Configuration via environment variables, config file, or .env
- Dockerfile for container-based deployment
- Token-optimized tool descriptions (~391 tokens for all 27 tools)
