FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    synfig \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server /app/server
RUN pip install --no-cache-dir /app/server

ENV BACKEND_MODE=headless
EXPOSE 8000

ENTRYPOINT ["synfig-mcp"]
