# DemandSphere MCP Server

An MCP (Model Context Protocol) server that connects AI assistants to the DemandSphere search intelligence platform. Supports both traditional SERP analytics (v5.0) and GenAI visibility tracking (v5.1).

## What It Does

This server exposes **27 tools** across five domains:

| Domain | Tools | API Version |
|---|---|---|
| **Site Discovery** | `list_sites`, `list_sites_flat` | v5.0 |
| **SERP Analytics** | `get_keyword_performance`, `get_keyword_groups`, `get_ranking_trends`, `get_search_engine_comparison`, `get_local_rankings`, `get_landing_matches`, `get_landings_history`, `get_search_engine_summary` | v5.0 |
| **GenAI Visibility** | `get_mentions`, `get_keyword_citations`, `get_bulk_citations`, `get_site_citations`, `get_llm_stats`, `get_llm_performance_summary`, `get_channels_performance_summary`, `get_cross_channel_overview`, `get_cross_llms_overview`, `get_llm_filters`, `get_people_also_ask` | v5.1 |
| **Brand Management** | `list_brands`, `create_brand`, `update_brand`, `delete_brands` | v5.1 |
| **ChatGPT Deep Research** | `search`, `fetch` | compat |

## Quick Start

### 1. Install

**With uv (recommended):**

```bash
git clone https://github.com/DemandSphereDev/demandsphere-mcp.git
cd demandsphere-mcp
uv sync
```

**With pip:**

```bash
git clone https://github.com/DemandSphereDev/demandsphere-mcp.git
cd demandsphere-mcp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure API Key

Choose one method:

```bash
# Option A: Environment variable
export DEMANDSPHERE_API_KEY="your-api-key"

# Option B: Config file
mkdir -p ~/.config/demandsphere
echo '{"api_key": "your-api-key"}' > ~/.config/demandsphere/config.json

# Option C: .env file in project root
echo 'DEMANDSPHERE_API_KEY=your-api-key' > .env
```

### 3. Run

**With uv:**

```bash
# stdio (default — for Claude Code, Claude Desktop, Cursor)
uv run demandsphere-mcp

# HTTP (for hosted/remote deployment)
DEMANDSPHERE_TRANSPORT=streamable-http uv run demandsphere-mcp
```

**With pip (after install):**

```bash
# stdio
demandsphere-mcp

# HTTP
DEMANDSPHERE_TRANSPORT=streamable-http demandsphere-mcp
```

### 4. Connect to Your MCP Client

**Claude Desktop / Cursor** — add to your MCP config:

With uv:

```json
{
  "mcpServers": {
    "demandsphere": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/demandsphere-mcp", "demandsphere-mcp"],
      "env": {
        "DEMANDSPHERE_API_KEY": "your-api-key"
      }
    }
  }
}
```

With pip (after `pip install -e .`):

```json
{
  "mcpServers": {
    "demandsphere": {
      "command": "demandsphere-mcp",
      "env": {
        "DEMANDSPHERE_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add demandsphere \
  -e DEMANDSPHERE_API_KEY=your-api-key \
  -- uv run --directory /path/to/demandsphere-mcp demandsphere-mcp
```

**Claude (web) and ChatGPT** — see [Hosted Deployment](#hosted-deployment) below.

## Security Model

### Transport Modes

| Transport | Use Case | Security Boundary |
|---|---|---|
| **stdio** | Local (Claude Code, Cursor) | OS process isolation; no network exposure |
| **Streamable HTTP** | Hosted/enterprise | HTTPS + OAuth 2.1 |

### API Key Handling

The DemandSphere API uses query-parameter auth. The MCP server holds the key and injects it into every outbound request. The AI model never sees the key.

**Important:** Because the API key is in the URL query string, it may appear in reverse proxy access logs, CDN logs, or network monitoring tools. If deploying behind a reverse proxy, configure it to strip or redact query strings from access logs.

| Method | Best For |
|---|---|
| Environment variable | Local dev, CI/CD |
| Config file (`~/.config/demandsphere/`) | Personal machines |
| `.env` file | Local dev |

### Hosted Deployment

For remote deployment (serving Claude web, ChatGPT, or other remote MCP clients):

1. Deploy behind HTTPS with a reverse proxy
2. Add OAuth 2.1 via your identity provider
3. Users connect via `https://mcp.demandsphere.com/mcp` and authenticate in-browser

**Claude (web)** — Pro, Max, Team, Enterprise: Settings → Integrations → Add Integration → enter server URL.

**ChatGPT** — Plus, Pro, Business, Enterprise, Education: Settings → Apps & Connectors → Add Connector → enter server URL with OAuth.

ChatGPT Deep Research is also supported via the built-in `search` and `fetch` compatibility tools.

See the [hosted deployment guide](https://docs.demandsphere.com/mcp/deployment) for full setup instructions including OAuth configuration.

### Self-Hosting

You can deploy the MCP server yourself on any platform that supports Docker or Python:

**Docker:**

```bash
docker build -t demandsphere-mcp .
docker run -p 127.0.0.1:8765:8765 \
  -e DEMANDSPHERE_API_KEY=your-api-key \
  demandsphere-mcp
```

The server is available at `http://localhost:8765/mcp`. Works with Cloudflare Workers, Railway, Fly.io, Northflank, Render, Google Cloud Run, AWS Fargate, or any container platform. A `docker-compose.yml` is included with production hardening (cap_drop, read_only, non-root).

**Without Docker:**

```bash
DEMANDSPHERE_TRANSPORT=streamable-http \
DEMANDSPHERE_HOST=0.0.0.0 \
DEMANDSPHERE_API_KEY=your-api-key \
demandsphere-mcp
```

Put an HTTPS reverse proxy (Caddy, nginx, Cloudflare Tunnel) in front for production use.

### Rate Limiting

Client-side token-bucket rate limiter (default: 60 req/min). Response shaping caps result sets at 100 rows per tool call to keep LLM token costs manageable. Both are configurable via environment variables.

## Configuration Reference

All settings via environment variables (prefix `DEMANDSPHERE_`):

| Variable | Default | Description |
|---|---|---|
| `DEMANDSPHERE_API_KEY` | (required for stdio) | DemandSphere API key |
| `DEMANDSPHERE_BASE_URL` | `https://api.demandsphere.com` | API base URL |
| `DEMANDSPHERE_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `DEMANDSPHERE_HOST` | `127.0.0.1` | HTTP server bind address |
| `DEMANDSPHERE_PORT` | `8765` | HTTP server port |
| `DEMANDSPHERE_REQUEST_TIMEOUT` | `30.0` | HTTP timeout (seconds) |
| `DEMANDSPHERE_MAX_REQUESTS_PER_MINUTE` | `60` | Rate limit cap |
| `DEMANDSPHERE_MAX_RESULTS_PER_TOOL_CALL` | `100` | Max rows per response |

## Project Structure

```
demandsphere-mcp/
├── pyproject.toml                          # Package config + deps
├── Dockerfile                              # Container deployment
├── docker-compose.yml                      # Production hardening example
├── CHANGELOG.md                            # Version history
├── CONTRIBUTING.md                         # Contribution guidelines
├── config.example.json                     # API key config example
├── examples/
│   ├── mcp-config-uv.json                 # MCP client config (uv)
│   └── mcp-config-pip.json                # MCP client config (pip)
├── tests/
│   └── test_core.py                       # Unit tests
└── src/demandsphere_mcp/
    ├── __init__.py
    ├── py.typed                            # PEP 561 type marker
    ├── server.py                           # MCP server entry point
    ├── config.py                           # Settings (env vars + config file)
    ├── client.py                           # Async HTTP client + rate limiter
    └── tools/
        ├── __init__.py
        ├── utils.py                        # Shared error handling decorator
        ├── sites.py                        # Site discovery (v5.0)
        ├── keywords_v50.py                 # SERP analytics (v5.0)
        ├── genai_v51.py                    # GenAI visibility (v5.1)
        ├── brands_v51.py                   # Brand management (v5.1)
        └── chatgpt_compat.py              # ChatGPT Deep Research (search/fetch)
```

## Development

```bash
# With uv
uv sync --extra dev
uv run pytest
uv run ruff check src/
uv run mcp dev src/demandsphere_mcp/server.py

# With pip
pip install -e ".[dev]"
pytest
ruff check src/
```

## Upgrades

This project uses [semantic versioning](https://semver.org/). To stay up to date:

- **Watch releases** on [GitHub](https://github.com/DemandSphereDev/demandsphere-mcp/releases) to be notified of new versions
- **Pull latest** and re-install:
  ```bash
  git pull
  uv sync     # or: pip install -e .
  ```
- See [CHANGELOG.md](CHANGELOG.md) for what changed in each release

## License

MIT

## Documentation

Additional documentation including API guides, use case examples, and integration walkthroughs is available at the [DemandSphere Help Center](https://help.demandsphere.com) (login required).
