"""
Unit tests for the production system: strict briefs, deterministic task
graphs, the resumable workspace, quality control and the orchestrator's
verified end-to-end run against the headless backend.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.errors import SynfigError
from synfig_mcp.production import (
    ProductionBrief,
    ProductionOrchestrator,
    ProductionWorkspace,
    QualityControl,
    TaskStatus,
    build_plan,
    order_tasks,
    slugify,
)
from synfig_mcp.security import access as access_mod
from synfig_mcp.security.access import AccessController


@pytest.fixture(autouse=True)
def isolated_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Fresh access controller per test; the production root is approved."""
    controller = AccessController(approvals_file=tmp_path / "approvals.json")
    monkeypatch.setattr(access_mod, "_controller", controller)
    monkeypatch.setattr(
        "synfig_mcp.security.sandbox.get_temp_root", lambda: tmp_path / "temp_root"
    )
    controller.approve_folder(tmp_path, reason="test")
    yield controller
    access_mod.reset_access_controller()


def _brief(**overrides) -> ProductionBrief:
    data = {
        "title": "Unit Production",
        "width": 160,
        "height": 120,
        "fps": 12.0,
        "backgrounds": [{"name": "sky", "color": "#3366cc"}],
        "episodes": [
            {
                "id": "ep1",
                "sequences": [
                    {
                        "id": "sq1",
                        "shots": [
                            {
                                "id": "sh010",
                                "duration": 0.5,
                                "background": "sky",
                                "effects": [{"name": "vignette", "params": {"opacity": 0.3}}],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    data.update(overrides)
    return ProductionBrief.model_validate(data)


def _make_part(path: Path, color: str) -> None:
    Image.new("RGBA", (40, 60), color).save(path)


# ---------------------------------------------------------------------------
# Models & planner
# ---------------------------------------------------------------------------


def test_slugify() -> None:
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("///") == "production"


def test_brief_rejects_incoherent_shots() -> None:
    with pytest.raises(ValueError):
        _brief(episodes=[{"id": "e", "sequences": [{"id": "s", "shots": [{"id": " "}]}]}])
    with pytest.raises(ValueError):
        _brief(
            episodes=[
                {"id": "e", "sequences": [{"id": "s", "shots": [{"id": "x", "duration": 0}]}]}
            ]
        )
    with pytest.raises(ValueError):
        _brief(fps=0)


def test_brief_shots_and_duration() -> None:
    brief = _brief()
    assert [s.id for s in brief.shots] == ["sh010"]
    assert brief.total_duration == pytest.approx(0.5)
    assert brief.project_slug == "unit-production"


def test_plan_is_deterministic_and_dependency_ordered() -> None:
    brief = _brief()
    plan_a = build_plan(brief)
    plan_b = build_plan(brief)
    assert [t.id for t in plan_a.tasks] == [t.id for t in plan_b.tasks]

    ordered = order_tasks(plan_a)
    seen: set[str] = set()
    for task in ordered:
        assert all(dep in seen for dep in task.depends_on)
        seen.add(task.id)
    assert ordered[0].id == "document"
    assert ordered[-1].id == "report"


def test_plan_final_render_gated_by_brief() -> None:
    assert not any(t.kind == "render_final" for t in build_plan(_brief()).tasks)
    assert any(t.kind == "render_final" for t in build_plan(_brief(render_final=True)).tasks)


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


def test_workspace_create_open_and_manifest(tmp_path: Path) -> None:
    brief = _brief()
    ws = ProductionWorkspace.create(brief, tmp_path)
    assert ws.project_dir.is_dir()
    for name in ("assets", "shots", "renders", "logs", "checkpoints", "reports"):
        assert (ws.project_dir / name).is_dir()

    manifest = ws.read_manifest() if ws.manifest_path.is_file() else None
    assert manifest is None  # the orchestrator writes the first manifest

    with pytest.raises(SynfigError):
        ProductionWorkspace.create(brief, tmp_path)

    from synfig_mcp.production.models import ProductionManifest

    ws.write_manifest(ProductionManifest(title=brief.title, slug=brief.project_slug))
    reopened = ProductionWorkspace.open(ws.root, brief.project_slug)
    assert reopened.read_manifest().title == brief.title


def test_workspace_state_and_log_roundtrip(tmp_path: Path) -> None:
    ws = ProductionWorkspace.create(_brief(), tmp_path)
    assert ws.read_state("state.json") is None
    ws.write_state("state.json", {"plan": {"project": "x"}})
    assert ws.read_state("state.json") == {"plan": {"project": "x"}}
    ws.log_event({"event": "task.done", "task": "document"})
    events = ws.read_log()
    assert events and events[-1]["event"] == "task.done"
    assert "time" in events[-1]


def test_workspace_path_cannot_escape(tmp_path: Path) -> None:
    from synfig_mcp.errors import SecuritySandboxError

    ws = ProductionWorkspace.create(_brief(), tmp_path)
    with pytest.raises(SecuritySandboxError):
        ws.path("..", "outside.txt")


# ---------------------------------------------------------------------------
# Quality control
# ---------------------------------------------------------------------------


def test_qc_render_checks(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    qc = QualityControl(backend)

    missing = tmp_path / "missing.png"
    issues = qc.validate_render(missing)
    assert any(i["code"] == "render.failed" for i in issues)

    flat = tmp_path / "flat.png"
    Image.new("RGBA", (160, 120), (10, 20, 30, 255)).save(flat)
    issues = qc.validate_render(flat, expected_width=160, expected_height=120)
    codes = {i["code"] for i in issues}
    assert "frame.blank" in codes
    assert "alpha.flat" in codes

    wrong_size = tmp_path / "wrong.png"
    Image.new("RGBA", (80, 60), (10, 20, 30, 255)).save(wrong_size)
    issues = qc.validate_render(wrong_size, expected_width=160, expected_height=120)
    assert any(i["code"] == "resolution.mismatch" for i in issues)


def test_qc_rig_validation() -> None:
    qc = QualityControl(HeadlessBackend())
    tree = {"layers": [{"id": "hero_pos", "children": [{"id": "hero_torso_rot"}]}]}
    assert qc.validate_rig(tree, "hero") == []
    issues = qc.validate_rig({"layers": []}, "hero")
    assert len(issues) == 2
    assert all(i["code"] == "rig.invalid" for i in issues)


# ---------------------------------------------------------------------------
# Orchestrator (verified end-to-end against the headless backend)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_end_to_end(tmp_path: Path, headless_backend: HeadlessBackend) -> None:
    brief = _brief()
    ws = ProductionWorkspace.create(brief, tmp_path)
    orch = ProductionOrchestrator(headless_backend, ws)
    result = await orch.run(brief, max_attempts=1)

    assert result["failed"] == 0, result
    assert result["done"] == result["tasks"]
    assert result["status"] == "previewed"
    assert ws.shot_file("sh010").is_file()
    assert (ws.render_dir("sh010") / "preview.png").is_file()
    assert (ws.reports_dir / "production-report.md").is_file()
    assert (ws.reports_dir / "production-report.json").is_file()
    manifest = ws.read_manifest()
    assert manifest.status == "previewed"
    assert manifest.project_file and Path(manifest.project_file).is_file()
    assert manifest.versions  # master + shot layout recorded


@pytest.mark.asyncio
async def test_orchestrator_checkpoint_approve_resume(
    tmp_path: Path, headless_backend: HeadlessBackend
) -> None:
    brief = _brief(checkpoints=["layout"])
    ws = ProductionWorkspace.create(brief, tmp_path)
    orch = ProductionOrchestrator(headless_backend, ws)

    first = await orch.run(brief, max_attempts=1)
    assert first["status"] == "awaiting_approval"
    assert first["awaiting_approval"] == ["layout"]
    assert not ws.shot_file("sh010").exists()  # nothing built past the gate

    still_gated = await orch.resume(max_attempts=1)
    assert still_gated["awaiting_approval"] == ["layout"]  # resume cannot bypass approval

    await orch.approve("layout")
    # A brand-new instance resumes purely from the on-disk state.
    resumed = ProductionOrchestrator(headless_backend, ws)
    second = await resumed.resume(max_attempts=1)
    assert second["failed"] == 0, second
    assert second["status"] == "previewed"
    assert ws.shot_file("sh010").is_file()


@pytest.mark.asyncio
async def test_orchestrator_missing_asset_fails_and_skips_dependents(
    tmp_path: Path, headless_backend: HeadlessBackend
) -> None:
    brief = _brief(
        characters=[
            {
                "id": "hero",
                "parts": [{"name": "torso", "file": str(tmp_path / "nope.png")}],
            }
        ],
        episodes=[
            {
                "id": "ep1",
                "sequences": [
                    {
                        "id": "sq1",
                        "shots": [
                            {
                                "id": "sh010",
                                "duration": 0.5,
                                "background": "sky",
                                "characters": ["hero"],
                            }
                        ],
                    }
                ],
            }
        ],
    )
    ws = ProductionWorkspace.create(brief, tmp_path)
    orch = ProductionOrchestrator(headless_backend, ws)
    result = await orch.run(brief, max_attempts=1)

    assert result["status"] == "failed"
    states = {t["id"]: t for t in result["task_states"]}
    assert states["character:hero"]["status"] == TaskStatus.FAILED.value
    assert states["shot:sh010:layout"]["status"] == TaskStatus.SKIPPED.value
    assert not ws.shot_file("sh010").exists()


@pytest.mark.asyncio
async def test_orchestrator_rigged_character_render_final(
    tmp_path: Path, headless_backend: HeadlessBackend
) -> None:
    parts = tmp_path / "parts"
    parts.mkdir()
    _make_part(parts / "torso.png", "#cc3333")
    _make_part(parts / "head.png", "#ffcc99")
    brief = _brief(
        render_final=True,
        characters=[
            {
                "id": "hero",
                "parts": [
                    {"name": "torso", "file": str(parts / "torso.png")},
                    {"name": "head", "file": str(parts / "head.png"), "parent": "torso"},
                ],
                "position": {"x": 80, "y": 100},
                "height": 80,
                "actions": [{"motion": "idle"}],
            }
        ],
        episodes=[
            {
                "id": "ep1",
                "sequences": [
                    {
                        "id": "sq1",
                        "shots": [
                            {
                                "id": "sh010",
                                "duration": 0.5,
                                "background": "sky",
                                "characters": ["hero"],
                            }
                        ],
                    }
                ],
            }
        ],
    )
    ws = ProductionWorkspace.create(brief, tmp_path)
    orch = ProductionOrchestrator(headless_backend, ws)
    result = await orch.run(brief, max_attempts=1)

    assert result["failed"] == 0, result
    assert result["status"] == "rendered"
    manifest = ws.read_manifest()
    assert {a.id for a in manifest.assets} == {"character:hero:torso", "character:hero:head"}
    assert all(a.sha256 for a in manifest.assets)
    finals = list((ws.render_dir("sh010") / "final").glob("*.png"))
    assert len(finals) >= 6


# ---------------------------------------------------------------------------
# MCP tool layer (production_run / resume / approve / status)
# ---------------------------------------------------------------------------


def _tool_data(res) -> dict:
    import json

    from mcp.types import TextContent

    first = res.content[0] if res.content else None
    text = first.text if isinstance(first, TextContent) else ""
    return json.loads(text)


@pytest.mark.asyncio
async def test_production_tools_dry_run_run_status(
    tmp_path: Path, headless_backend: HeadlessBackend
) -> None:
    from mcp.client import Client

    from synfig_mcp.server import create_server

    brief = _brief(root=str(tmp_path)).model_dump(mode="json")
    app = create_server(backend=headless_backend, profile="all")
    async with Client(app) as client:
        plan = _tool_data(
            await client.call_tool("production_run", {"brief": brief, "dry_run": True})
        )
        assert plan["dry_run"] is True
        assert any(t["kind"] == "create_document" for t in plan["tasks"])
        assert not (tmp_path / "projects").exists()  # dry run touched nothing

        run = _tool_data(await client.call_tool("production_run", {"brief": brief}))
        assert run["failed"] == 0, run
        assert run["status"] == "previewed"
        assert Path(run["project_dir"]).is_dir()

        status = _tool_data(
            await client.call_tool(
                "production_status", {"slug": run["project"], "root": str(tmp_path)}
            )
        )
        assert status["status"] == "previewed"
        assert status["tasks"] and all(t["status"] == "done" for t in status["tasks"])
        assert status["versions"]


@pytest.mark.asyncio
async def test_production_tools_checkpoint_flow(
    tmp_path: Path, headless_backend: HeadlessBackend
) -> None:
    from mcp.client import Client

    from synfig_mcp.server import create_server

    brief = _brief(checkpoints=["layout"], root=str(tmp_path)).model_dump(mode="json")
    app = create_server(backend=headless_backend, profile="all")
    async with Client(app) as client:
        first = _tool_data(await client.call_tool("production_run", {"brief": brief}))
        assert first["awaiting_approval"] == ["layout"]
        args = {"slug": first["project"], "root": str(tmp_path)}

        gated = _tool_data(await client.call_tool("production_resume", args))
        assert gated["awaiting_approval"] == ["layout"]  # resume cannot bypass the gate

        approved = _tool_data(
            await client.call_tool("production_approve", {**args, "checkpoint": "layout"})
        )
        assert approved["approved"] == "layout"

        resumed = _tool_data(await client.call_tool("production_resume", args))
        assert resumed["failed"] == 0, resumed
        assert resumed["status"] == "previewed"