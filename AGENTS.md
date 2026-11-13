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

| File | Generator | Guard test |
| :--- | :--- | :--- |
| `docs/tools.md` | `scripts/generate_tool_docs.py` | `server/tests/unit/test_tool_docs.py` |

Run `uv run python ../scripts/generate_tool_docs.py` from `server/` after adding,
renaming or removing any tool, or CI will fail.

The website catalog generator (`scripts/generate_website_catalog.py` and
`server/tests/unit/test_website_catalog.py`) exists only on `main` / `v1.0.0`,
not on this branch; do not expect it here.

## Quality gate

From `server/`: `uv run poe check` runs `ruff format --check`, `ruff check`,
`mypy` and `pytest` (excluding `real_studio`). Keep it green before pushing.

## Conventions

- README and the website both lead with zero-install `uvx synfig-mcp`; keep the
  client config examples in `README.md`, `examples/*.json` and
  `website/index.html` consistent.
- `LICENSE` is MIT (server); the bridge's GPL-3.0 notice is in `LICENSE-BRIDGE`.
- Image uploads: an MCP client attaches `ImageContent` (base64), which the server
  cannot read as a path. `characters/image_input.py` decodes + hardens it
  (reusing `assets/security/raster_hardening.sanitize_raster_bytes`) and writes
  it inside a granted root via `security/sandbox.safe_write_bytes`. Exposed as
  `rig_sheet_from_image`.
- Tests that need a granted root patch
  `synfig_mcp.security.permissions.permissions` and
  `synfig_mcp.security.sandbox.get_default_allowed_roots` (see
  `tests/unit/test_permissions.py` for the canonical fixture).
- Production runs are resumable. `production/pipeline.py` writes
  `pipeline_state.json` into the output directory and saves the working document
  at checkpoints; a stage is only restored when its effect is already in the
  reopened document (`AnimeProductionPipeline.run(..., resume=True)`). Keep
  `saved_through` monotonic and never restore a stage whose layers were not
  saved, or a resumed run will duplicate layers.
- The story stage (`production/story.py`) derives a continuity bible
  (`story_bible.json`) and a screenplay view. The server has no LLM, so a derived
  bible is a structural summary (`authored=False`); a client authors prose by
  editing the bible and passing it back as `ProductionBrief.story`. Validation is
  structural (`validate_story`): an inconsistent bible fails the `story` stage.
- The motion library lives in `characters/cutout.py` (`MOTIONS` /
  `SPECIAL_MOTIONS`). Add a motion there and a parametrized test in
  `tests/unit/test_cutout_rig.py`; the guide (`resources/guides.py`) and
  `docs/characters.md` list the motions and must stay in step. A motion may only
  name joints the cut-out rig actually has (rotate layers), so no facial or
  IK-style motions.
- `docs/protocol.md` is the honest bridge contract: a method marked **Not
  implemented** must be absent from the C++ dispatcher, and vice versa
  (`tests/unit/test_protocol_docs.py`). Do not mark a method verified without an
  entry in `handlers.cpp`.
