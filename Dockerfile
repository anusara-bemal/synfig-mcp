# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)

FROM python:3.11-slim-bookworm

# Install Synfig CLI and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    synfig \
    ffmpeg \
    imagemagick \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and workspace directory
RUN useradd -m -u 1000 synfiguser && \
    mkdir -p /workspace && \
    chown -R synfiguser:synfiguser /workspace

WORKDIR /app

# Copy dependency specifications and install
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

USER synfiguser
WORKDIR /workspace

ENV SYNFIG_MCP_WORKSPACE=/workspace \
    SYNFIG_BIN=/usr/bin/synfig \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["synfig-mcp"]
