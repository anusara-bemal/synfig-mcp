# Synfig MCP Wire Protocol

This directory contains the single source of truth for the JSON-RPC wire protocol between `server/` and `bridge/`:

- `schema/`: JSON Schema definitions for every request, response, and event.
- `fixtures/`: Golden request and response payloads shared across Python and C++ test suites.
