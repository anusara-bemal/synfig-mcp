# Headless Synfig MCP Server Container
# Includes the synfig CLI for out-of-process renders and pure-Python SIF DOM manipulation.
# No X11 or GUI dependencies required.

FROM python:3.12-slim-bookworm AS base

ARG VERSION=0.8.0-rc2

LABEL org.opencontainers.image.title="synfig-mcp" \
      org.opencontainers.image.description="Model Context Protocol server for Synfig Studio" \
      org.opencontainers.image.source="https://github.com/anusara-bemal/synfig-mcp" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="MIT"

# Install synfig CLI, ffmpeg, and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    synfig \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged user
RUN useradd -m -u 1000 synfiguser

WORKDIR /app

# Install Python package
COPY server/pyproject.toml server/README.md ./
COPY server/src ./src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Default sandbox root, writable by the runtime user
RUN mkdir -p /workspace && chown synfiguser:synfiguser /workspace

USER synfiguser
WORKDIR /workspace

ENV SYNFIG_MCP_BACKEND=headless \
    SYNFIG_MCP_WORKSPACE_ROOTS=/workspace \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Default entrypoint runs stdio MCP transport; can be overridden to streamable HTTP:
# docker run -p 8000:8000 synfig-mcp --transport streamable-http --host 0.0.0.0 --port 8000 --token SECRET
ENTRYPOINT ["synfig-mcp"]
