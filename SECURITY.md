# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| `main` branch | Yes |
| Latest tagged release | Yes |
| Older releases | No |

## Reporting a vulnerability

**Do not open a public issue or discussion for security reports.**

Email `security@demandsphere.com` with:

- A description of the vulnerability
- Steps to reproduce (or a proof of concept)
- The impact you believe it has
- Any mitigations you have identified

We will acknowledge your report within **3 business days**. For confirmed issues, the target fix window is **30 days for critical severity**; lower severities are prioritized alongside normal work.

## Scope

In scope:

- Code in this repository (`src/`, `tests/`, `Dockerfile`, `.github/workflows/`)
- Direct Python dependencies declared in `pyproject.toml`

Out of scope:

- The DemandSphere API itself — contact DemandSphere support via the [Help Center](https://help.demandsphere.com)
- Third-party MCP clients (Claude Desktop, Cursor, ChatGPT, etc.) — report to the respective vendor
- Reverse proxies or hosting platforms you deploy this server behind

## Known considerations

- The DemandSphere API uses query-parameter authentication. The API key may appear in URL query strings sent to DemandSphere's backend. This server suppresses `httpx` request logging (see [commit 29f2424](https://github.com/DemandSphereDev/demandsphere-mcp/commit/29f2424)) to prevent local log leaks. If you deploy the `streamable-http` transport behind a reverse proxy, configure it to strip or redact query strings from access logs.
- The AI model using this MCP server never sees the API key — the server holds the key and injects it into outbound requests.
