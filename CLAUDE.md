# CLAUDE.md

Agent rules and conventions for `demandsphere-mcp`. Tools using the `AGENTS.md` convention (Codex, Cursor, Aider, etc.) should also read this file — `AGENTS.md` is a stub that points here.

## Project snapshot

Public MCP (Model Context Protocol) server that brokers the DemandSphere search-intelligence API (v5.0 SERP analytics + v5.1 GenAI visibility) to AI assistants. Python 3.11+, MIT-licensed, distributed via GitHub. PyPI publishing is deferred to Phase 2.

## Run & test commands

```bash
uv sync --extra dev                     # install dev deps
uv run pytest                           # run tests
uv run ruff check src/ tests/           # lint
uv run ruff format src/ tests/          # format
uv run demandsphere-mcp                 # run server (stdio)
```

## Architecture map

- `src/demandsphere_mcp/server.py` — MCP server entry point, tool/prompt/resource registration
- `src/demandsphere_mcp/config.py` — settings loaded from env vars and `~/.config/demandsphere/config.json`
- `src/demandsphere_mcp/client.py` — async HTTP client and token-bucket rate limiter
- `src/demandsphere_mcp/tools/` — one file per domain:
  - `sites.py` — site discovery (v5.0)
  - `keywords_v50.py` — SERP analytics (v5.0)
  - `genai_v51.py` — GenAI visibility (v5.1)
  - `brands_v51.py` — brand management (v5.1)
  - `chatgpt_compat.py` — ChatGPT Deep Research `search`/`fetch`
  - `prompts.py` — MCP Prompts (workflow templates)
  - `resources.py` — MCP Resources (parameter discovery)
  - `utils.py` — error handling, validation, hint builders

## Code conventions

- Type hints required on all public APIs — we ship `py.typed`
- Ruff target `py311`, line length 100
- Async HTTP via `httpx.AsyncClient` only — never `requests`
- All schemas via `pydantic` v2
- New tools live in `src/demandsphere_mcp/tools/<domain>.py` and register in `server.py`

## Testing rules

- Every new tool needs tests in `tests/test_<name>.py`
- No real API calls — mock `httpx` (see `tests/test_core.py` for patterns)
- Async tests use `pytest-asyncio` configured with `asyncio_mode = "auto"` — no per-test decorator needed
- Unit tests cover validators, response shaping, and error paths
- Integration-style tests for multi-tool flows live in `test_consolidated.py`

## Forbidden patterns (rejected in review)

- Never log API keys, full URLs with query strings, or request bodies that contain credentials. Precedent: commit `29f2424` ("Suppress httpx request logging — leaks API keys").
- Never use bare `except:` or `except Exception: pass` — surface the error or narrow the except clause.
- Never commit `config.json`, `.env`, any `*.pem`/`*.key`, or anything under `.ai/`.
- Never edit `CHANGELOG.md` in a feature PR — the changelog is curated at release time.
- Never inline a live API key in tests, docstrings, examples, or fixtures.

## Before committing

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pytest
pre-commit run --all-files   # if pre-commit is installed
```

## Secret handling

The DemandSphere API key is loaded from, in order: `DEMANDSPHERE_API_KEY` env var → `~/.config/demandsphere/config.json` → `.env` in the working directory. See `src/demandsphere_mcp/config.py`. The key travels in the DemandSphere API's URL query string — this is why server-side `httpx` request logging is suppressed. Do not re-enable it.

## Working artifacts

`.ai/` at the repo root is the gitignored scratch space for agent specs, plans, and notes (see `.ai/README.md`). Nothing under `.ai/` is ever committed. If an artifact becomes durable project documentation, move it to the repo proper under `docs/`.
