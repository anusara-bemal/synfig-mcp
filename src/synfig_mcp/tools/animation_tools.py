# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Animation tools: waypoints, keyframes, baking, time loops, linking, bones."""

from __future__ import annotations

import contextlib
from typing import Any

from lxml import etree

from ..document import animation as anim
from ..document import exported_values as exports
from ..document.bones import (
    bind_skeleton as bones_bind,
)
from ..document.bones import (
    create_bone as bones_create,
)
from ..document.bones import (
    list_bones,
)
from ..document.bones import (
    set_bone_param as bones_set_param,
)
from ..document.keyframes import (
    add_keyframe as kf_add,
)
from ..document.keyframes import (
    list_keyframes as kf_list,
)
from ..document.keyframes import (
    move_keyframe as kf_move,
)
from ..document.keyframes import (
    remove_keyframe as kf_remove,
)
from ..document.layers import get_param, set_or_create_param
from ..document.model import ProjectSession
from ..document.timeutil import format_time, parse_time
from ..errors import ParameterError, WaypointError
from ..security.paths import sanitize_text
from .common import AppContext, json_dumps, tool


def _fps(session: ProjectSession) -> float:
    return float(session.root.get("fps", "24") or 24)


def _layer_and_param(
    session: ProjectSession, layer_ref: str | int, param: str
) -> tuple[int, etree._Element, etree._Element | None]:
    index, layer = session.resolve_layer(layer_ref)
    target = get_param(layer, param)
    return index, layer, target


def register(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def animate_param(
        project_id: str,
        layer: str | int,
        param: str,
        waypoints: list[dict[str, Any]],
        interpolation: str | None = None,
    ) -> str:
        """Animate a parameter with waypoints.

        waypoints: [{"time": "0f", "value": 0.0, "before": "linear"?, "after": "linear"?}, ...]
        interpolation sets all waypoints' before/after (constant, linear, clamped, tcb, ease, halt).
        Re-saving the same time replaces the existing waypoint.
        """
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        async with session.lock:
            session.record_history()
            _, _, target = _layer_and_param(session, layer, param)
            count = anim.animate_param(
                target,
                waypoints,
                interpolation=interpolation,
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "param": param, "waypoints_set": count})

    @tool(server)
    async def add_waypoint(
        project_id: str,
        layer: str | int,
        param: str,
        time: str,
        value: Any,
        interpolation: str | None = None,
    ) -> str:
        """Add or replace a single waypoint on an animated parameter."""
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        async with session.lock:
            session.record_history()
            _, _, target = _layer_and_param(session, layer, param)
            anim.set_waypoint(
                target,
                time,
                value,
                interpolation=interpolation,
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "param": param, "time": time})

    @tool(server)
    async def remove_waypoint(
        project_id: str,
        layer: str | int,
        param: str,
        time: str,
    ) -> str:
        """Remove the waypoint at the given time."""
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        async with session.lock:
            session.record_history()
            _, _, target = _layer_and_param(session, layer, param)
            removed = anim.remove_waypoint(target, time, fps=fps)
            if not removed:
                raise WaypointError(f"No waypoint at {time!r} on parameter {param!r}.")
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "param": param, "removed": True, "time": time})

    @tool(server)
    async def set_interpolation(
        project_id: str,
        layer: str | int,
        param: str,
        interpolation: str,
        time: str | None = None,
    ) -> str:
        """Set waypoint interpolation: constant, linear, clamped, tcb, ease, halt, manual.

        Pass time to update one waypoint; omit to update all waypoints of the parameter.
        """
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        async with session.lock:
            session.record_history()
            _, _, target = _layer_and_param(session, layer, param)
            count = anim.set_interpolation(target, interpolation, time_text=time, fps=fps)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "param": param,
                "interpolation": interpolation,
                "waypoints_updated": count,
            }
        )

    @tool(server)
    async def add_keyframe(project_id: str, time: str, label: str = "") -> str:
        """Add a keyframe (time comment) to the canvas."""
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        async with session.lock:
            session.record_history()
            result = kf_add(session.root, time, sanitize_text(label, max_length=256), fps=fps)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, **result})

    @tool(server)
    async def remove_keyframe(project_id: str, time: str) -> str:
        """Remove the keyframe at the given time."""
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        async with session.lock:
            session.record_history()
            removed = kf_remove(session.root, time, fps=fps)
            if not removed:
                from ..errors import KeyframeNotFoundError

                raise KeyframeNotFoundError(f"No keyframe at {time!r}.")
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "removed": True, "time": time})

    @tool(server)
    async def move_keyframe(project_id: str, from_time: str, to_time: str) -> str:
        """Move a keyframe to a new time."""
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        async with session.lock:
            session.record_history()
            result = kf_move(session.root, from_time, to_time, fps=fps)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, **result})

    @tool(server)
    async def list_keyframes(project_id: str) -> str:
        """List all keyframes on the canvas."""
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        return json_dumps({"project_id": project_id, "keyframes": kf_list(session.root, fps=fps)})

    @tool(server)
    async def set_time_loop(
        project_id: str,
        duration: str = "2s 0f",
        link_time: str = "0f",
        symmetrical: bool = False,
        only_for_positive_duration: bool = True,
        name: str | None = None,
        index: int | None = None,
    ) -> str:
        """Add a timeloop filter layer (loops the layers below it).

        duration: how long one loop iteration lasts; link_time: source start offset.
        """
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        duration_s = parse_time(duration, fps=fps)
        link_s = parse_time(link_time, fps=fps)
        from lxml import etree

        from ..document import layers as lay
        from .layer_shared import (
            default_version,
            ensure_amount,
            ensure_blend,
            ensure_z_depth,
            set_param,
        )

        async with session.lock:
            session.record_history()
            layer = etree.Element(
                "layer",
                attrib={
                    "type": "timeloop",
                    "active": "true",
                    "version": default_version("timeloop"),
                },
            )
            ensure_z_depth(layer)
            ensure_amount(layer)
            ensure_blend(layer)
            if name:
                layer.set("desc", sanitize_text(name, max_length=128))
            set_param(
                layer,
                "duration",
                duration_s,
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
            set_param(
                layer,
                "link_time",
                link_s,
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
            set_param(
                layer,
                "symmetrical",
                bool(symmetrical),
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
            set_param(
                layer,
                "only_for_positive_duration",
                bool(only_for_positive_duration),
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
            lay.insert_layer(session.root, layer, index)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "timeloop": lay.layer_summary(layer)})

    @tool(server)
    async def convert_param(
        project_id: str,
        layer: str | int,
        param: str,
        to: str,
        source_layer: str | int | None = None,
        source_param: str | None = None,
        export_name: str | None = None,
    ) -> str:
        """Convert a parameter's value node type.

        to:
        - 'static': freeze an animated parameter to its first waypoint value
        - 'animated': wrap a constant parameter in a single waypoint at 0f
        - 'linked': link this parameter to another parameter (source_layer/source_param)
        - 'exported': move the value into defs under export_name (auto-generated if omitted)
        """
        session = await ctx.registry.get(project_id)
        target_kind = to.strip().lower()
        if target_kind not in {"static", "animated", "linked", "exported"}:
            raise ParameterError(
                "convert_param 'to' must be one of: static, animated, linked, exported."
            )
        # linked/exported call helpers that record history themselves.
        record_here = target_kind in {"static", "animated"}
        async with session.lock:
            if record_here:
                session.record_history()
            _, _, target = _layer_and_param(session, layer, param)
            if target_kind == "static":
                _freeze_static(session, target)
            elif target_kind == "animated":
                anim.ensure_animated(target)
            elif target_kind == "linked":
                if source_layer is None or source_param is None:
                    raise ParameterError("linked conversion needs source_layer and source_param.")
                exports.link_params(
                    session, source_layer, source_param, layer, param, export_name=export_name
                )
            elif target_kind == "exported":
                if not export_name:
                    export_name = f"{param}_{abs(hash((str(layer), param))) % 10000}"
                exports.export_value(session, layer, param, export_name)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "param": param, "converted_to": target_kind})

    @tool(server)
    async def add_time_offset(project_id: str, layer: str | int, time_offset: str = "0f") -> str:
        """Set the time offset of a layer that supports it (e.g. pastecanvas/group)."""
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        seconds = parse_time(time_offset, fps=fps)
        time_text = format_time(seconds, fps=fps)
        async with session.lock:
            session.record_history()
            _, layer_el = session.resolve_layer(layer)
            from ..document.layers import get_param_or_none

            existing = get_param_or_none(layer_el, "time_offset")
            if existing is None:
                raise ParameterError(
                    f"Layer of type {layer_el.get('type')!r} has no time_offset parameter.",
                    hint="time_offset exists on pastecanvas/group/sound layers etc.",
                )
            set_or_create_param(layer_el, "time_offset", time_text, tag="time")
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "time_offset": time_text})

    @tool(server)
    async def bake_animation(
        project_id: str,
        layer: str | int,
        param: str,
        begin_time: str | None = None,
        end_time: str | None = None,
        step_frames: int = 1,
    ) -> str:
        """Bake an animated parameter into dense linear waypoints.

        Samples the curve every step_frames frames and rewrites the parameter
        with linear-interpolated waypoints. Linear segments are exact; curved
        (TCB/ease) segments are resampled — use Synfig Studio's Bake for exact
        spline evaluation.
        """
        session = await ctx.registry.get(project_id)
        fps = _fps(session)
        begin_s = (
            parse_time(begin_time, fps=fps) if begin_time is not None else _canvas_begin(session)
        )
        end_s = parse_time(end_time, fps=fps) if end_time is not None else _canvas_end(session)
        if end_s <= begin_s:
            raise ParameterError("end_time must be greater than begin_time.")
        if int(step_frames) < 1:
            raise ParameterError("step_frames must be >= 1.")
        max_samples = ctx.settings.max_frames
        samples = int((end_s - begin_s) * fps) + 1
        if samples > max_samples:
            raise ParameterError(
                f"Baking would create {samples} waypoints (> SYNFIG_MCP_MAX_FRAMES={max_samples}).",
                hint="Narrow the range or raise the cap.",
            )
        async with session.lock:
            session.record_history()
            _, _, target = _layer_and_param(session, layer, param)
            try:
                created = _bake(target, begin_s, end_s, fps, step_frames)
            except Exception:
                # Restore the pre-bake snapshot recorded above.
                with contextlib.suppress(Exception):
                    session.undo()
                raise
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "param": param,
                "waypoints_created": created,
                "range": [format_time(begin_s, fps=fps), format_time(end_s, fps=fps)],
            }
        )

    # -- linking / exported values / bones -----------------------------------

    @tool(server)
    async def export_value(project_id: str, layer: str | int, param: str, export_name: str) -> str:
        """Export a parameter value into defs under a name (referenced via use=":name")."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            result = exports.export_value(session, layer, param, export_name)
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, **result})

    @tool(server)
    async def list_exported_values(project_id: str) -> str:
        """List all exported values (defs entries with an id)."""
        session = await ctx.registry.get(project_id)
        return json_dumps(
            {"project_id": project_id, "exported": exports.list_exported(session.root)}
        )

    @tool(server)
    async def link_params(
        project_id: str,
        source_layer: str | int,
        source_param: str,
        target_layer: str | int,
        target_param: str,
        export_name: str | None = None,
    ) -> str:
        """Link two parameters (target references source's exported value)."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            result = exports.link_params(
                session,
                source_layer,
                source_param,
                target_layer,
                target_param,
                export_name=export_name,
            )
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, **result})

    @tool(server)
    async def unlink_params(project_id: str, layer: str | int, param: str) -> str:
        """Unlink a parameter (inline a private copy of the referenced value)."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            result = exports.unlink_params(session, layer, param)
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, **result})

    @tool(server)
    async def create_bone(
        project_id: str,
        name: str,
        origin: list[float] | None = None,
        angle: float = 0.0,
        length: float = 1.0,
        width: float = 0.3,
        tipwidth: float = 0.15,
        parent: str | None = None,
    ) -> str:
        """Create a bone in the canvas skeleton (<bones> section).

        Bones are stored as exported value nodes (Synfig 1.5.x cannot
        round-trip a skeleton layer's bones parameter; Studio manages that
        side on open). Subsequent list_bones/set_bone_param calls address the
        bone by name.
        """
        session = await ctx.registry.get(project_id)
        async with session.lock:
            result = bones_create(
                session,
                name,
                origin=origin,
                angle=angle,
                length=length,
                width=width,
                tipwidth=tipwidth,
                parent=parent,
            )
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, **result})

    @tool(server)
    async def list_bones_tool(project_id: str) -> str:
        """List all bones in the canvas."""
        session = await ctx.registry.get(project_id)
        return json_dumps({"project_id": project_id, "bones": list_bones(session.root)})

    @tool(server)
    async def set_bone_param(project_id: str, bone: str, param: str, value: Any) -> str:
        """Set a bone parameter: name, origin, angle, scalelx, scalex, width,
        tipwidth, bone_depth, length or parent (parent = name of another bone)."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            result = bones_set_param(
                session,
                bone,
                param,
                value,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, **result})

    @tool(server)
    async def bind_skeleton(
        project_id: str,
        layer: str | int,
        param: str,
        bones: list[str],
        weights: list[float] | None = None,
    ) -> str:
        """Bind a vector/bline_point parameter to bones via boneinfluence.

        bones: names/ids/guids of bones created with create_bone. weights:
        relative influence per bone (default 1.0 each).
        """
        session = await ctx.registry.get(project_id)
        async with session.lock:
            result = bones_bind(session, layer, param, bones, weights=weights)
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, **result})


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------


def _canvas_begin(session: ProjectSession) -> float:
    fps = _fps(session)
    return parse_time(session.root.get("begin-time", "0f"), fps=fps)


def _canvas_end(session: ProjectSession) -> float:
    fps = _fps(session)
    return parse_time(session.root.get("end-time", "0f"), fps=fps)


def _freeze_static(session: ProjectSession, param) -> None:  # type: ignore[no-untyped-def]
    """Replace an animated param with a constant of its first waypoint's value."""
    import copy

    from ..document.animation import get_animated, waypoints
    from ..errors import WaypointError

    animated = get_animated(param)
    if animated is None:
        return  # already static
    wps = waypoints(animated)
    if not wps:
        raise WaypointError(
            f"Animated parameter {param.get('name')!r} has no waypoints; cannot freeze to static.",
            hint="Add a waypoint first with add_waypoint.",
        )
    first = wps[0]
    # Waypoints carry exactly one value element.
    child = first[0] if len(first) else None
    payload = child[0] if child is not None and child.tag == "value_node" and len(child) else child
    if payload is None:
        raise WaypointError(f"Waypoint at {first.get('time')!r} has no value to freeze to.")
    param.remove(animated)
    param.append(copy.deepcopy(payload))


def _bake(param, begin_s: float, end_s: float, fps: float, step_frames: int) -> int:  # type: ignore[no-untyped-def]
    from ..document.animation import get_animated, waypoints

    animated = get_animated(param)
    if animated is None:
        anim.ensure_animated(param)
        animated = get_animated(param)
        return 1
    type_name = animated.get("type") or "real"
    wps = waypoints(animated)
    if len(wps) < 2:
        return len(wps)

    keyframes = []
    for wp in wps:
        try:
            seconds = parse_time(wp.get("time"), fps=fps)
        except ParameterError:
            continue
        payload = _waypoint_payload(wp)
        if payload is None:
            continue
        keyframes.append((seconds, payload))
    keyframes.sort(key=lambda item: item[0])
    if not keyframes:
        return 0

    samples: list[tuple[float, Any]] = []
    frame = 0
    t = begin_s
    while t <= end_s + 1e-6:
        samples.append((t, _sample(keyframes, t, type_name)))
        frame += step_frames
        t = begin_s + frame / fps

    # Remove old waypoints and write dense linear ones.
    for wp in wps:
        animated.remove(wp)
    from ..document.animation import set_waypoint

    for t, value in samples:
        interp = "linear"
        set_waypoint(param, format_time(t, fps=fps), value, interpolation=interp, fps=fps)
    return len(samples)


def _waypoint_payload(wp: etree._Element) -> Any:
    for child in wp:
        if child.tag == "value_node" and len(child):
            return _decode_payload(child[0])
        if child.tag != "value_node":
            return _decode_payload(child)
    return None


def _decode_payload(el: etree._Element) -> Any:
    tag = el.tag
    if tag == "real":
        return float(el.get("value", "0") or 0.0)
    if tag == "integer":
        return int(float(el.get("value", "0") or 0))
    if tag == "angle":
        return float(el.get("value", "0") or 0.0)
    if tag == "time":
        return el.get("value", "0f")
    if tag == "bool":
        return (el.get("value", "false") or "false").lower() in {"true", "1"}
    if tag == "string":
        return (el.text or "").strip()
    if tag == "vector":
        from ..document.params import decode_vector

        v = decode_vector(el)
        return [v["x"], v["y"]]
    if tag == "color":
        from ..document.params import decode_color

        c = decode_color(el)
        return [c["r"], c["g"], c["b"], c["a"]]
    return None


def _sample(keyframes, t: float, type_name: str):  # type: ignore[no-untyped-def]
    before = keyframes[0]
    after = keyframes[-1]
    for seconds, payload in keyframes:
        if seconds <= t:
            before = (seconds, payload)
        if seconds >= t:
            after = (seconds, payload)
            break
    if before[0] >= t:
        return before[1]
    if after[0] <= t:
        return after[1]
    span = after[0] - before[0]
    ratio = 0.0 if span <= 0 else (t - before[0]) / span
    return _lerp(before[1], after[1], ratio, type_name)


def _lerp(a: Any, b: Any, ratio: float, type_name: str):  # type: ignore[no-untyped-def]
    if a is None or b is None:
        return a
    if isinstance(a, bool) or isinstance(b, bool):
        return a if ratio < 1.0 else b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if type_name == "angle":
            delta = ((b - a + 540.0) % 360.0) - 180.0
            return a + delta * ratio
        return a + (b - a) * ratio
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [x + (y - x) * ratio for x, y in zip(a, b, strict=True)]
    return a if ratio < 1.0 else b
