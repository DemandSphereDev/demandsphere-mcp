# Pin to exact version for reproducible builds.
FROM python:3.12.8-slim-bookworm

WORKDIR /app

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir .

# Container platforms inject PORT; default to 8765
ENV DEMANDSPHERE_TRANSPORT=streamable-http \
    DEMANDSPHERE_HOST=0.0.0.0 \
    DEMANDSPHERE_PORT=8765

EXPOSE 8765

# Health check — curl the MCP endpoint for liveness.
# Adjust interval/timeout for your platform.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8765/mcp || exit 1

# Run as non-root
RUN useradd -r -s /bin/false mcp
USER mcp

CMD ["demandsphere-mcp"]

# Runtime hardening (apply at orchestration layer):
#   docker run --cap-drop=ALL --read-only --tmpfs /tmp \
#     -p 127.0.0.1:8765:8765 demandsphere-mcp
