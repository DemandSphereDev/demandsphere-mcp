# Contributing to DemandSphere MCP Server

Thanks for your interest in contributing. This project follows a lightweight workflow: fork, branch, PR, automated checks, review.

## Code of Conduct

Participation in this project is governed by the [Contributor Covenant Code of Conduct](./CODE_OF_CONDUCT.md). Report unacceptable behavior to `dev@demandsphere.com`.

## Development setup

```bash
git clone https://github.com/DemandSphereDev/demandsphere-mcp.git
cd demandsphere-mcp
uv sync --extra dev
```

Optional but recommended — install pre-commit hooks so local commits run the same checks CI does:

```bash
uv run pre-commit install
```

## Running tests

```bash
uv run pytest
```

## Code style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

Project-wide conventions (type hints, async patterns, tool layout, forbidden patterns) live in [`CLAUDE.md`](./CLAUDE.md). Humans should read it too — the rules apply to all contributors, not only AI agents.

## Pull requests

1. Fork the repo and create a feature branch from `main`
2. Add tests for any new functionality
3. Ensure `ruff check`, `ruff format --check`, and `pytest` all pass locally
4. Open a PR with a clear description of the change
5. CI (lint + test matrix + secret scan) must be green before review

The PR template includes a checklist — please fill it in honestly.

## Reporting issues

Use the issue templates on [GitHub](https://github.com/DemandSphereDev/demandsphere-mcp/issues). They collect the environment details we need (Python version, OS, MCP client, transport).

## Security issues

Do not open public issues for security reports. See [`SECURITY.md`](./SECURITY.md) for the private reporting flow.
