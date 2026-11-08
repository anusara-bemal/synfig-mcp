# Headless Synfig MCP Server Container
# Includes the synfig CLI for out-of-process renders and pure-Python SIF DOM manipulation.
# No X11 or GUI dependencies required.

FROM python:3.12-slim-bookworm AS base

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

USER synfiguser

ENV SYNFIG_MCP_BACKEND=headless \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Default entrypoint runs stdio MCP transport; can be overridden to streamable HTTP:
# docker run -p 8000:8000 synfig-mcp --transport streamable-http --host 0.0.0.0 --port 8000 --token SECRET
ENTRYPOINT ["synfig-mcp"]
