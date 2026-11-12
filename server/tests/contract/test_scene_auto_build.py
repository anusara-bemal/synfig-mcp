"""
Contract: a rig sheet and a background become an animated scene in one call.

The flow is the one an MCP client follows: slice the sheet, name the parts,
build the scene.  It runs through the public MCP tools on both backends; the
headless document is inspected to prove that the layers, the hierarchy and the
waypoints are really there.  ``test_sif_synfig_validity`` additionally loads
and renders the same scene with the real Synfig engine.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent

from synfig_mcp.backend.headless import HeadlessBackend
from synfig_mcp.backend.live import LiveBackend
from synfig_mcp.protocol.client import BridgeClient
from synfig_mcp.protocol.fake_bridge import FakeBridgeServer
from synfig_mcp.server import create_server
from tests.support.rig_assets import PART_NAMES, make_assets, scene_spec


def _data(result: Any) -> dict[str, Any]:
    assert not result.is_error, result.content[0].text
    first = result.content[0]
    assert isinstance(first, TextContent)
    loaded: dict[str, Any] = json.loads(first.text)
    return loaded


@pytest_asyncio.fixture(params=["headless", "live_fake"])
async def server(
    request: pytest.FixtureRequest,
) -> AsyncIterator[tuple[str, MCPServer, HeadlessBackend | None]]:
    if request.param == "headless":
        backend = HeadlessBackend()
        yield ("headless", create_server(backend=backend, profile="all"), backend)
        return
    fake = FakeBridgeServer(port=0)
    await fake.start()
    client = BridgeClient(host=fake.host, port=fake.assigned_port, token=fake.token)
    await client.connect()
    try:
        yield ("live_fake", create_server(backend=LiveBackend(client=client), profile="all"), None)
    finally:
        await client.close()
        await fake.stop()


async def _slice(client: Client, assets: dict[str, str]) -> str:
    first = _data(await client.call_tool("rig_sheet_slice", {"file_path": assets["sheet"]}))
    assert first["detected_parts"] == 9  # eight parts and the caption box
    assert first["preview_base64"]
    named = _data(
        await client.call_tool(
            "rig_sheet_slice",
            {"file_path": assets["sheet"], "names": PART_NAMES, "preview": False},
        )
    )
    assert [p["name"] for p in named["parts"]] == list(PART_NAMES.values())
    return str(named["manifest"])


@pytest.mark.asyncio
async def test_sheet_to_animated_scene(
    server: tuple[str, MCPServer, HeadlessBackend | None], tmp_path: Path
) -> None:
    mode, app, backend = server
    assets = make_assets(tmp_path)
    async with Client(app) as client:
        manifest = await _slice(client, assets)
        spec = scene_spec(assets, manifest)
        spec["save_path"] = str(tmp_path / "scene.sif")

        plan = _data(await client.call_tool("scene_auto_build", {"spec": spec, "dry_run": True}))
        assert plan["dry_run"] is True
        assert "import:hero_torso_img" in plan["plan"]["layers"]
        assert plan["plan"]["groups"][-1] == "Character_sun"
        assert len(_data_list(await client.call_tool("doc_list", {}))) <= 1, "dry run made a doc"

        built = _data(await client.call_tool("scene_auto_build", {"spec": spec}))
        assert built["success"] is True
        hero = built["characters"][0]
        assert hero["parts"] == 8 and hero["motions"] == ["walk", "wave"]
        assert hero["waypoints"] > 40
        assert built["props"][0]["id"] == "sun"
        assert built["camera"] == {"keys": 2, "animated": True}
        assert any("forearm_r" in w for w in built["warnings"]), "missing joints must be reported"
        doc_id = built["doc_id"]

        # The rig can be animated further by name.
        more = _data(
            await client.call_tool(
                "character_pose_apply",
                {"doc_id": doc_id, "character_id": "hero", "angles": {"head": 15}, "time": 3.5},
            )
        )
        assert more["applied_bones"] == ["hero_head_rot"]

        if mode != "headless" or backend is None:
            return

        assert Path(built["saved_to"]).is_file()
        doc = backend._documents[doc_id]
        assert doc.end_time == 4.0
        top = [layer.desc for layer in doc.get_layers()]
        assert top == [
            "Camera_zoom",
            "Camera_pan",
            "Character_sun",
            "Character_hero",
            "Background",
            "Background_color",
        ]
        inside = [layer.desc for layer in doc.get_layers("Character_hero")]
        assert inside == ["hero_pos", "hero_torso"]
        torso = [layer.desc for layer in doc.get_layers("Character_hero/hero_torso")]
        assert torso[0] == "hero_torso_rot", "the joint must be on top of its group"
        assert torso.index("hero_head") < torso.index("hero_torso_img")
        assert torso.index("hero_torso_img") < torso.index("hero_upper_leg_l")
        leg = [layer.desc for layer in doc.get_layers("Character_hero/hero_torso/hero_upper_leg_l")]
        assert leg == [
            "hero_upper_leg_l_rot",
            "hero_upper_leg_l_img",
            "hero_lower_leg_l",
        ]  # shin behind

        swing = doc.get_layer("hero_upper_leg_r_rot")
        assert swing is not None
        assert len(swing.get_waypoints("amount")) == 14  # 3 walk cycles + settle
        travel = doc.get_layer("hero_pos")
        assert travel is not None
        xs = [wp["value"]["x"] for wp in travel.get_waypoints("origin")]
        assert xs[0] < 0 < xs[-1]

        # One undo step removes the whole scene.
        _data(await client.call_tool("history_undo", {"doc_id": doc_id}))  # the pose
        _data(await client.call_tool("history_undo", {"doc_id": doc_id}))  # the time range
        _data(await client.call_tool("history_undo", {"doc_id": doc_id}))  # the scene
        assert doc_id in backend._documents
        assert backend._documents[doc_id].get_layers() == []


def _data_list(result: Any) -> list[Any]:
    assert not result.is_error
    return [json.loads(c.text) for c in result.content if isinstance(c, TextContent)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"background": {"file": "missing.png"}}, "denied by workspace sandbox"),
        ({"duration": -1}, "duration"),
        ({"characters": [{"id": "hero", "parts": []}]}, "no parts"),
        ({"props": [{"id": "hero", "file": "BG"}]}, "must be unique"),
        ({"camera": [{"time": 0, "zoom": 0}]}, "camera.0.zoom"),
    ],
)
async def test_invalid_scene_leaves_no_document_behind(
    tmp_path: Path, change: dict[str, Any], message: str
) -> None:
    backend = HeadlessBackend()
    app = create_server(backend=backend, profile="all")
    assets = make_assets(tmp_path)
    async with Client(app) as client:
        manifest = await _slice(client, assets)
        spec = {**scene_spec(assets, manifest), **change}
        for prop in spec.get("props", []):
            if prop["file"] == "BG":
                prop["file"] = assets["background"]
        res = await client.call_tool("scene_auto_build", {"spec": spec})
        assert res.is_error
        text = "".join(c.text for c in res.content if isinstance(c, TextContent))
        assert message in text
    assert backend._documents == {}, "a rejected scene must not leave a document open"


@pytest.mark.asyncio
async def test_unknown_motion_is_rejected_before_anything_is_built(tmp_path: Path) -> None:
    backend = HeadlessBackend()
    app = create_server(backend=backend, profile="all")
    assets = make_assets(tmp_path)
    async with Client(app) as client:
        manifest = await _slice(client, assets)
        doc_id = _data(await client.call_tool("doc_new", {"width": 640, "height": 360}))["id"]
        spec = scene_spec(assets, manifest)
        spec["doc_id"] = doc_id
        spec["characters"][0]["actions"] = [{"motion": "moonwalk"}]
        res = await client.call_tool("scene_auto_build", {"spec": spec})
        assert res.is_error
        assert "Unknown motion 'moonwalk'" in res.content[0].text  # type: ignore[union-attr]
    assert backend._documents[doc_id].get_layers() == []
