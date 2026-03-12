# Changelog

All notable changes to the DemandSphere MCP Server will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/). Subscribe to releases on GitHub to be notified of updates.

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
