"""Guard the one-action-per-intent tool surface.

Two names used to exist for the same intent (`import_asset` /
`asset_import_local` and `produce_anime_project` / `production_plan`). They were
consolidated into `asset_import` and `production_run`; this test keeps the
regression from coming back and verifies the consolidated tools keep both
halves of their behaviour.
"""

from __future__ import annotations

from mcp.client import Client

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.server import create_server


async def test_duplicate_actions_are_not_registered() -> None:
    app = create_server(backend=HeadlessBackend(), profile="all")
    async with Client(app) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}

    assert "asset_import" in names
    assert "production_run" in names
    for removed in (
        "import_asset",
        "asset_import_local",
        "produce_anime_project",
        "production_plan",
    ):
        assert removed not in names, f"{removed} is a duplicate legacy action"


async def test_production_run_exposes_pipeline_mode() -> None:
    """The former one-command build/planner is now `engine='pipeline'`."""
    app = create_server(backend=HeadlessBackend(), profile="all")
    async with Client(app) as client:
        schema = next(
            tool.input_schema
            for tool in (await client.list_tools()).tools
            if tool.name == "production_run"
        )
    props = schema.get("properties", {})
    assert "engine" in props
    assert "stages" in props
    assert "resume" in props
