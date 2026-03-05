# Contributing to DemandSphere MCP Server

Thanks for your interest in contributing.

## Development Setup

```bash
git clone https://github.com/DemandSphereDev/demandsphere-mcp.git
cd demandsphere-mcp
uv sync --extra dev
```

## Running Tests

```bash
uv run pytest
```

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting:

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Pull Requests

1. Fork the repo and create a feature branch from `main`
2. Add tests for any new functionality
3. Ensure all tests pass and ruff is clean
4. Open a PR with a clear description of the change

## Reporting Issues

Open an issue on [GitHub](https://github.com/DemandSphereDev/demandsphere-mcp/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (Python version, OS, MCP client)

## Security Issues

If you discover a security vulnerability, please email security@demandsphere.com instead of opening a public issue.
