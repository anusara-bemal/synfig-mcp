# AGENTS.md

Repository-specific guidance for agents working in `synfig-mcp`.

## Layout

- `server/` — the Python MCP server (package `synfig_mcp`). All tooling
  (`pyproject.toml`, `poe` tasks, tests) lives here.
- `bridge/` — the native C++ GTK bridge (GPL-3.0, see `LICENSE-BRIDGE`).
- `website/` — the static marketing site (plain HTML/CSS/JS, no build step).
- `docs/` — MkDocs source; `scripts/` — repo-level generators.

## Generated files (do not hand-edit)

These are produced from the live tool registry and checked by tests, so the
docs and the site can never advertise a tool that does not exist:

| File | Generator | Task | Guard test |
| :--- | :--- | :--- | :--- |
| `docs/tools.md` | `scripts/generate_tool_docs.py` | `poe docs-tools` | `server/tests/unit/test_tool_docs.py` |
| `website/script.js` + `website/index.html` | `scripts/generate_website_catalog.py` | `poe docs-website` | `server/tests/unit/test_website_catalog.py` |

Run `poe docs` (from `server/`) to regenerate both. Run it after adding,
renaming or removing any tool, or CI will fail.

## Quality gate

From `server/`: `uv run poe check` runs `ruff format --check`, `ruff check`,
`mypy` and `pytest` (excluding `real_studio`). Keep it green before pushing.

## Conventions

- README and the website both lead with zero-install `uvx synfig-mcp`; keep the
  client config examples in `README.md`, `examples/*.json` and
  `website/index.html` consistent.
- `LICENSE` is MIT (server); the bridge's GPL-3.0 notice is in `LICENSE-BRIDGE`.
