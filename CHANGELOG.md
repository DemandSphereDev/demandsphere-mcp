# Changelog

All notable changes to the DemandSphere MCP Server will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/). Subscribe to releases on GitHub to be notified of updates.

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
