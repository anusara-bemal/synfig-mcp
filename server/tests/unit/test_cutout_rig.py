"""Cut-out rig compilation and the motion planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from synfig_mcp.characters.cutout import (
    MOTIONS,
    CanvasFrame,
    CutoutCharacter,
    MotionAction,
    compile_character,
    infer_role,
    plan_actions,
)
from synfig_mcp.errors import SynfigError


def character(**data: Any) -> CutoutCharacter:
    return CutoutCharacter.model_validate(data)


FRAME = CanvasFrame(800, 400, -4.0, 2.0, 4.0, -2.0)  # 100 px per unit


def _png(path: Path, size: tuple[int, int]) -> str:
    Image.new("RGBA", size, (200, 50, 50, 255)).save(path)
    return str(path)


@pytest.fixture
def parts(tmp_path: Path) -> list[dict[str, Any]]:
    return [
        {"name": "torso", "file": _png(tmp_path / "torso.png", (100, 200))},
        {"name": "head", "file": _png(tmp_path / "head.png", (80, 80))},
        {"name": "upper_arm_l", "file": _png(tmp_path / "ual.png", (30, 100))},
        {"name": "forearm_l", "file": _png(tmp_path / "fal.png", (26, 90))},
        {"name": "upper_arm_r", "file": _png(tmp_path / "uar.png", (30, 100))},
        {"name": "upper_leg_r", "file": _png(tmp_path / "ulr.png", (40, 120))},
        {"name": "lower_leg_r", "file": _png(tmp_path / "llr.png", (36, 110))},
    ]


@pytest.mark.parametrize(
    ("name", "role"),
    [
        ("head", "head"),
        ("arm_upper_l", "upper_arm_l"),
        ("LeftUpperArm", "upper_arm_l"),
        ("r_forearm", "forearm_r"),
        ("lower_leg_right", "lower_leg_r"),
        ("shin_l", "lower_leg_l"),
        ("foot_r", "foot_r"),
        ("arm_l", "arm_l"),
        ("Body", "torso"),
        ("sword", None),
        ("part_03", None),
    ],
)
def test_infer_role(name: str, role: str | None) -> None:
    assert infer_role(name) == role


def test_frame_converts_pixels_to_units() -> None:
    assert FRAME.point(0, 0) == (-4.0, 2.0)
    assert FRAME.point(400, 200) == (0.0, 0.0)
    assert FRAME.length(100) == pytest.approx(1.0)
    assert CanvasFrame.for_document(1920, 1080, None).units_per_pixel == pytest.approx(1 / 60)


def test_hierarchy_follows_body_roles(parts: list[dict[str, Any]]) -> None:
    rig = compile_character(character(id="hero", parts=parts), FRAME)
    parents = {p.name: p.parent for p in rig.parts.values()}
    assert parents == {
        "torso": None,
        "head": "torso",
        "upper_arm_l": "torso",
        "forearm_l": "upper_arm_l",
        "upper_arm_r": "torso",
        "upper_leg_r": "torso",
        "lower_leg_r": "upper_leg_r",
    }
    assert rig.root_group == "Character_hero"


def test_groups_nest_children_under_the_joint_of_their_parent(
    parts: list[dict[str, Any]],
) -> None:
    rig = compile_character(character(id="hero", parts=parts), FRAME)
    groups = {g["id"]: g["layer_ids"] for g in rig.groups}

    # A rotate layer turns what is below it: the joint is the last (top) member.
    arm = groups["hero_upper_arm_l"]
    assert arm[-1] == "hero_upper_arm_l_rot"
    assert "hero_forearm_l" in arm and "hero_upper_arm_l_img" in arm
    # Left limbs go behind the torso art, the head and right arm in front of it.
    torso = groups["hero_torso"]
    art = torso.index("hero_torso_img")
    assert torso.index("hero_upper_arm_l") < art < torso.index("hero_upper_arm_r")
    assert art < torso.index("hero_head")
    assert groups["Character_hero"] == ["hero_torso", "hero_pos"]

    # Inner groups are created before the groups that contain them.
    order = [g["id"] for g in rig.groups]
    assert (
        order.index("hero_forearm_l") < order.index("hero_upper_arm_l") < order.index("hero_torso")
    )
    # Layers are emitted bottom to top in the same order as the group members.
    layer_order = [layer["id"] for layer in rig.layers]
    assert layer_order.index("hero_upper_arm_l_img") < layer_order.index("hero_torso_img")


def test_joint_sits_where_the_part_attaches(tmp_path: Path) -> None:
    spec = character(
        id="bot",
        anchor="pivot",
        scale=1.0,
        position={"x": 400, "y": 200},
        parts=[
            {
                "name": "torso",
                "file": _png(tmp_path / "t.png", (100, 200)),
                "pivot": {"fx": 0.5, "fy": 1.0},
            },
            {
                "name": "head",
                "file": _png(tmp_path / "h.png", (80, 80)),
                "pivot": {"x": 40, "y": 80},
                "attach": {"fx": 0.5, "fy": 0.0},
            },
        ],
    )
    rig = compile_character(spec, FRAME)
    layers = {layer["id"]: layer["params"] for layer in rig.layers}
    # Torso: 100x200 px, joint at its bottom centre = local origin; 100 px per unit.
    assert layers["bot_torso_img"]["tl"] == {"type": "vector", "x": -0.5, "y": 2.0}
    assert layers["bot_torso_img"]["br"] == {"type": "vector", "x": 0.5, "y": 0.0}
    # Head joint (its bottom centre) sits on the top centre of the torso.
    assert layers["bot_head_rot"]["origin"] == {"type": "vector", "x": 0.0, "y": 2.0}
    assert layers["bot_head_img"]["tl"] == {"type": "vector", "x": -0.4, "y": 2.8}
    assert layers["bot_pos"]["origin"] == {"type": "vector", "x": 0.0, "y": 0.0}


def test_height_and_feet_anchor(parts: list[dict[str, Any]]) -> None:
    rig = compile_character(
        character(id="hero", parts=parts, height=200, position={"x": 400, "y": 400}), FRAME
    )
    assert rig.height_units == pytest.approx(2.0)
    ys = [
        layer["params"][key]["y"]
        for layer in rig.layers
        if layer["type"] == "import"
        for key in ("tl", "br")
    ]
    assert min(ys) == pytest.approx(0.0, abs=1e-6), "the feet must stand on the anchor"
    assert max(ys) == pytest.approx(2.0, abs=1e-6)
    assert rig.position == (0.0, -2.0)


def test_flip_adds_a_mirror_layer(parts: list[dict[str, Any]]) -> None:
    rig = compile_character(character(id="hero", parts=parts, flip=True), FRAME)
    flip = next(layer for layer in rig.layers if layer["id"] == "hero_flip")
    assert flip["type"] == "stretch"
    assert flip["params"]["amount"] == {"type": "vector", "x": -1.0, "y": 1.0}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"id": "1bad"}, "must start with a letter"),
        ({"root": "tail"}, "not one of the parts"),
        ({"parts": []}, "no parts"),
    ],
)
def test_invalid_character_specs_are_rejected(
    parts: list[dict[str, Any]], change: dict[str, Any], message: str
) -> None:
    data: dict[str, Any] = {"id": "hero", "parts": parts, **change}
    with pytest.raises(SynfigError, match=message):
        compile_character(character(**data), FRAME)


def test_unknown_part_without_placement_is_rejected(
    parts: list[dict[str, Any]], tmp_path: Path
) -> None:
    extra = {"name": "sword", "file": _png(tmp_path / "sword.png", (10, 90))}
    with pytest.raises(SynfigError, match="'parent' and 'attach'"):
        compile_character(character(id="hero", parts=[*parts, extra]), FRAME)
    placed = {**extra, "parent": "forearm_l", "attach": {"fx": 0.5, "fy": 0.95}}
    rig = compile_character(character(id="hero", parts=[*parts, placed]), FRAME)
    assert rig.parts["sword"].parent == "forearm_l"


def test_cycles_and_missing_files_are_rejected(parts: list[dict[str, Any]]) -> None:
    looped = [dict(p) for p in parts]
    looped[1]["parent"] = "forearm_l"
    looped[3]["parent"] = "head"
    with pytest.raises(SynfigError, match="cycle"):
        compile_character(character(id="hero", parts=looped), FRAME)
    missing = [dict(p) for p in parts]
    missing[0]["file"] = missing[0]["file"].replace("torso", "nothing")
    with pytest.raises(FileNotFoundError):
        compile_character(character(id="hero", parts=missing), FRAME)


def test_walk_loops_until_the_end_and_travels(parts: list[dict[str, Any]]) -> None:
    rig = compile_character(character(id="hero", parts=parts, position={"x": 100, "y": 400}), FRAME)
    action = MotionAction(motion="walk", start=1.0, end=3.5, move_to={"x": 700, "y": 400})
    plan = plan_actions(rig, [action], FRAME, default_end=10.0)

    leg = plan.waypoints("hero_upper_leg_r_rot", "amount")
    leg = [wp for wp in leg if wp["time"] <= 3.5]
    assert leg[0]["time"] == 1.0 and leg[-1]["time"] == 3.5
    assert leg[0]["value"]["degrees"] == pytest.approx(26.0)
    assert leg[4]["time"] == 2.0 and leg[4]["value"]["degrees"] == pytest.approx(26.0)
    assert leg[-1]["value"]["degrees"] == pytest.approx(-26.0), "half a cycle after 2.5 loops"

    track = plan.waypoints("hero_pos", "origin")
    assert track[0]["value"]["x"] == pytest.approx(-3.0)
    assert track[-1]["value"]["x"] == pytest.approx(3.0)
    xs = [wp["value"]["x"] for wp in track]
    assert xs == sorted(xs), "the character must not step backwards"
    assert "lower_leg_l" in plan.skipped_roles
    assert plan.end_time == 3.5
    # After the walk the joints ease back to the rest pose.
    settled = plan.waypoints("hero_upper_leg_r_rot", "amount")[-1]
    assert (settled["time"], settled["value"]["degrees"]) == (3.8, 0.0)


def test_one_shot_motion_and_pose(parts: list[dict[str, Any]]) -> None:
    rig = compile_character(character(id="hero", parts=parts), FRAME)
    plan = plan_actions(
        rig,
        [
            MotionAction(motion="wave", start=2.0),
            MotionAction(motion="pose", start=5.0, angles={"head": 12, "forearm_l": -30}),
        ],
        FRAME,
        default_end=10.0,
    )
    arm = plan.waypoints("hero_upper_arm_r_rot", "amount")
    assert (arm[0]["time"], arm[-1]["time"]) == (2.0, 2.0 + MOTIONS["wave"].period)
    assert max(wp["value"]["degrees"] for wp in arm) == 150
    assert plan.waypoints("hero_head_rot", "amount")[-1]["value"]["degrees"] == 12
    assert plan.waypoints("hero_forearm_l_rot", "amount")[-1]["time"] == 5.0


def test_motion_errors_are_actionable(parts: list[dict[str, Any]], tmp_path: Path) -> None:
    rig = compile_character(character(id="hero", parts=parts), FRAME)
    with pytest.raises(SynfigError, match="Unknown motion 'moonwalk'"):
        plan_actions(rig, [MotionAction(motion="moonwalk")], FRAME, 5.0)
    with pytest.raises(SynfigError, match="neither a part nor a role"):
        plan_actions(rig, [MotionAction(motion="pose", angles={"tail": 5})], FRAME, 5.0)

    crate = character(
        id="crate", parts=[{"name": "art", "file": _png(tmp_path / "crate.png", (50, 50))}]
    )
    with pytest.raises(SynfigError, match="has none of these parts"):
        plan_actions(compile_character(crate, FRAME), [MotionAction(motion="walk")], FRAME, 5.0)


#: The motions added to broaden the action library.
NEW_MOTIONS = (
    "breath",
    "kick",
    "block",
    "dodge",
    "fall",
    "land",
    "turn",
    "react",
    "crouch",
    "stomp",
    "shake",
)


@pytest.fixture
def full_body(tmp_path: Path) -> list[dict[str, Any]]:
    """A rig with every joint the library addresses."""
    names = [
        ("torso", (100, 200)),
        ("head", (80, 80)),
        ("upper_arm_l", (30, 100)),
        ("forearm_l", (26, 90)),
        ("upper_arm_r", (30, 100)),
        ("forearm_r", (26, 90)),
        ("upper_leg_l", (40, 120)),
        ("lower_leg_l", (36, 110)),
        ("upper_leg_r", (40, 120)),
        ("lower_leg_r", (36, 110)),
    ]
    return [{"name": name, "file": _png(tmp_path / f"{name}.png", size)} for name, size in names]


def test_new_motions_are_in_the_catalog() -> None:
    for name in NEW_MOTIONS:
        assert name in MOTIONS, f"{name} is missing from the motion library"
        assert MOTIONS[name].description and MOTIONS[name].period > 0


@pytest.mark.parametrize("motion", NEW_MOTIONS)
def test_new_motion_plans_waypoints(motion: str, full_body: list[dict[str, Any]]) -> None:
    rig = compile_character(character(id="hero", parts=full_body), FRAME)
    plan = plan_actions(rig, [MotionAction(motion=motion, start=1.0)], FRAME, default_end=10.0)
    assert plan.applied == [motion]
    assert plan.count() > 0, f"{motion} produced no waypoints"
    # Every curve the motion names must resolve to a joint of the full-body rig.
    assert plan.skipped_roles == [], f"{motion} could not address {plan.skipped_roles}"
    assert plan.end_time >= 1.0


@pytest.mark.parametrize("motion", NEW_MOTIONS)
def test_new_one_shot_motions_use_their_own_period(
    motion: str, full_body: list[dict[str, Any]]
) -> None:
    spec = MOTIONS[motion]
    if spec.loop:
        pytest.skip("looping motion runs until the end of its action")
    rig = compile_character(character(id="hero", parts=full_body), FRAME)
    plan = plan_actions(rig, [MotionAction(motion=motion, start=2.0)], FRAME, default_end=10.0)
    assert plan.end_time == pytest.approx(2.0 + spec.period)
