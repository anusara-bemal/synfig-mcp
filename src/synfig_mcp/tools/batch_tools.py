# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Batch tools: atomic multi-operation execution, undo/redo, templates."""

from __future__ import annotations

import json
from typing import Any

import mcp.types as mcp_types
from lxml import etree

from ..document.model import ProjectSession
from ..errors import BatchOperationError, ParameterError
from .common import AppContext, json_dumps, tool

FORBIDDEN_IN_BATCH = frozenset(
    {
        "batch_operations",
        "render_frame",
        "render_animation",
        "render_preview",
        "render_thumbnail",
        "cancel_render",
        "undo",
        "redo",
    }
)


def register(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def batch_operations(
        operations: list[dict[str, Any]],
        project_id: str | None = None,
        rollback_on_error: bool = True,
    ) -> str:
        """Run an ordered list of tool calls atomically.

        operations: [{"tool": "add_layer", "arguments": {...}}, ...]
        All operations run against the same project (project_id is injected
        into each operation that accepts it). On any failure the whole batch
        is rolled back (if rollback_on_error=true) and the error reports the
        failing operation index. Render tools are not allowed inside a batch.
        """
        if not operations:
            raise ParameterError("operations must be a non-empty list.")
        if len(operations) > 200:
            raise ParameterError("batch_operations accepts at most 200 operations.")
        target_id = project_id
        if target_id is None:
            for op in operations:
                args = op.get("arguments") or {}
                if isinstance(args, dict) and args.get("project_id"):
                    target_id = str(args["project_id"])
                    break
        if target_id is None:
            raise ParameterError(
                "Pass project_id (or include project_id in the first operation's arguments)."
            )
        session = await ctx.registry.get(target_id)

        async with session.lock:
            pre_snapshot = session.snapshot()
            session.batch_depth += 1
            results: list[dict[str, Any]] = []
            try:
                for index, op in enumerate(operations):
                    name = str(op.get("tool", "")).strip()
                    arguments = op.get("arguments") or {}
                    if not name:
                        raise BatchOperationError(f"Operation #{index} is missing 'tool'.")
                    if name in FORBIDDEN_IN_BATCH:
                        raise BatchOperationError(
                            f"Operation #{index}: tool {name!r} is not allowed inside batch_operations.",
                            hint="Renders and batch/undo must be issued as separate top-level tool calls.",
                        )
                    if not isinstance(arguments, dict):
                        raise BatchOperationError(
                            f"Operation #{index}: 'arguments' must be an object."
                        )
                    arguments = {**arguments, "project_id": target_id}
                    try:
                        result = await server.call_tool(name, arguments)
                    except Exception as exc:
                        raise BatchOperationError(
                            f"Operation #{index} ({name}) failed: {exc}",
                            hint="Batch aborted; earlier operations in this batch were rolled back.",
                            context={"operation_index": index, "tool": name},
                        ) from exc
                    results.append(
                        {
                            "index": index,
                            "tool": name,
                            "ok": True,
                            "result": _stringify_result(result),
                        }
                    )
            except BatchOperationError:
                session.batch_depth -= 1
                if rollback_on_error:
                    session._restore(pre_snapshot)
                    session.clear_history()
                raise
            session.batch_depth -= 1
            session.record_history(pre_snapshot)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": target_id,
                "operations_run": len(results),
                "rolled_back": False,
                "results": results,
            }
        )

    @tool(server)
    async def undo(project_id: str) -> str:
        """Undo the last mutation on this project (in-memory history)."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.undo()
        return json_dumps({"project_id": project_id, "undone": True, "info": session.info()})

    @tool(server)
    async def redo(project_id: str) -> str:
        """Redo the last undone mutation on this project."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.redo()
        return json_dumps({"project_id": project_id, "redone": True, "info": session.info()})

    @tool(server)
    async def apply_template(
        project_id: str,
        template: str,
        name: str | None = None,
    ) -> str:
        """Apply a built-in template.

        Templates: 'bouncing-ball', 'title-card', 'logo-reveal'.
        Templates create a small, ready-to-render scene using only public
        layer parameters; they never overwrite existing layers.
        """
        session = await ctx.registry.get(project_id)
        maker = _TEMPLATES.get(template.strip().lower())
        if maker is None:
            raise ParameterError(
                f"Unknown template {template!r}.",
                hint=f"Available templates: {', '.join(sorted(_TEMPLATES))}.",
            )
        async with session.lock:
            session.record_history()
            created = maker(session, name=name)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "template": template,
                "created_layers": created,
            }
        )


def _stringify_result(result: Any) -> Any:
    if isinstance(result, dict):
        return result
    if isinstance(result, (list, tuple)):
        out: list[Any] = []
        for item in result:
            if isinstance(item, mcp_types.TextContent):
                try:
                    out.append(json.loads(item.text))
                except (json.JSONDecodeError, TypeError):
                    out.append(item.text)
            elif isinstance(item, mcp_types.ImageContent):
                out.append({"type": "image", "mime": getattr(item, "mimeType", "image/png")})
            else:
                out.append(str(item))
        return out
    return str(result)


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------


def _template_layer(
    session: ProjectSession,
    layer_type: str,
    *,
    desc: str | None = None,
    params: list[tuple[str, Any, str | None]] | None = None,
) -> etree._Element:
    from ..document.layers import insert_layer, set_or_create_param

    layer = etree.Element(
        "layer",
        attrib={"type": layer_type, "active": "true", "version": "0.1"},
    )
    if desc:
        layer.set("desc", desc)
    set_or_create_param(layer, "z_depth", 0.0, tag="real")
    set_or_create_param(layer, "amount", 1.0, tag="real")
    set_or_create_param(layer, "blend_method", 0, tag="integer")
    fps = float(session.root.get("fps", "24") or 24)
    for pname, value, tag in params or []:
        set_or_create_param(
            layer,
            pname,
            value,
            tag=tag,
            fps=fps,
            unit_px=session.settings.unit_px,
            unit_system=session.settings.unit_system,
        )
    insert_layer(session.root, layer, None)
    return layer


def _template_bouncing_ball(session: ProjectSession, *, name: str | None) -> list[dict[str, Any]]:
    label = name or "Bouncing Ball"
    created: list[dict[str, Any]] = []
    ball = _template_layer(
        session,
        "circle",
        desc=label,
        params=[
            ("origin", [0.0, 2.0], "vector"),
            ("radius", 0.5, "real"),
            ("color", "#ff5522", "color"),
        ],
    )
    created.append({"index": None, "type": "circle", "desc": label})
    # Bounce animation: fall from y=2 to y=-1 with linear fall, constant bounce.
    from ..document import animation as anim

    origin_param = ball.find("param[@name='origin']")
    assert origin_param is not None
    anim.animate_param(
        origin_param,
        [
            {"time": "0f", "value": [0.0, 2.0]},
            {"time": "24f", "value": [0.0, -1.0]},
            {"time": "36f", "value": [0.0, 0.5]},
            {"time": "48f", "value": [0.0, -1.0]},
        ],
        interpolation="tcb",
        fps=float(session.root.get("fps", "24") or 24),
        unit_px=session.settings.unit_px,
        unit_system=session.settings.unit_system,
    )
    shadow = _template_layer(
        session,
        "circle",
        desc=f"{label} Shadow",
        params=[
            ("origin", [0.0, -1.6], "vector"),
            ("radius", 0.6, "real"),
            ("color", "#1a1a1a", "color"),
            ("amount", 0.5, "real"),
        ],
    )
    created.append({"index": None, "type": "circle", "desc": f"{label} Shadow"})
    scene = _template_layer(
        session,
        "solid_color",
        desc=f"{label} Background",
        params=[("color", "#20242c", "color")],
    )
    # Move background to the very back (paint first).
    from ..document import layers as lay

    lay.move_layer(session.root, scene, 0)
    created.append({"index": 0, "type": "solid_color", "desc": f"{label} Background"})
    return [
        {**c, "index": session.layers().index(el)}
        for c, el in zip(created, [ball, shadow, scene], strict=True)
    ]


def _template_title_card(session: ProjectSession, *, name: str | None) -> list[dict[str, Any]]:
    label = name or "Title Card"
    bg = _template_layer(
        session,
        "solid_color",
        desc=f"{label} Background",
        params=[("color", "#101820", "color")],
    )
    title = _template_layer(
        session,
        "text",
        desc=f"{label} Title",
        params=[
            ("text", label, "string"),
            ("orient", [0.5, 0.5], "vector"),
            ("origin", [0.0, 0.6], "vector"),
            ("family", "sans-serif", "string"),
            ("weight", 700, "integer"),
            ("size", [1.1, 1.1], "vector"),
            ("color", "#f2f4f8", "color"),
        ],
    )
    subtitle = _template_layer(
        session,
        "text",
        desc=f"{label} Subtitle",
        params=[
            ("text", "an animation", "string"),
            ("orient", [0.5, 0.5], "vector"),
            ("origin", [0.0, -0.5], "vector"),
            ("family", "sans-serif", "string"),
            ("weight", 400, "integer"),
            ("size", [0.5, 0.5], "vector"),
            ("color", "#9fb4c8", "color"),
        ],
    )
    from ..document import layers as lay

    lay.move_layer(session.root, bg, 0)
    return [
        {"index": 0, "type": "solid_color", "desc": f"{label} Background"},
        {"index": session.layers().index(title), "type": "text", "desc": f"{label} Title"},
        {"index": session.layers().index(subtitle), "type": "text", "desc": f"{label} Subtitle"},
    ]


def _template_logo_reveal(session: ProjectSession, *, name: str | None) -> list[dict[str, Any]]:
    label = name or "Logo Reveal"
    bg = _template_layer(
        session,
        "solid_color",
        desc=f"{label} Background",
        params=[("color", "#0d1117", "color")],
    )
    disc = _template_layer(
        session,
        "circle",
        desc=f"{label} Disc",
        params=[
            ("origin", [0.0, 0.0], "vector"),
            ("radius", 1.2, "real"),
            ("color", "#2f81f7", "color"),
        ],
    )
    ring = _template_layer(
        session,
        "outline",
        desc=f"{label} Ring",
        params=[
            (
                "bline",
                {
                    "vertices": [[-1.6, 0.0], [0.0, 1.6], [1.6, 0.0], [0.0, -1.6], [-1.6, 0.0]],
                    "loop": True,
                    "width": 1.0,
                },
                "bline",
            ),
            ("color", "#58a6ff", "color"),
            ("width", 0.08, "real"),
        ],
    )
    from ..document import layers as lay

    lay.move_layer(session.root, bg, 0)
    return [
        {"index": 0, "type": "solid_color", "desc": f"{label} Background"},
        {"index": session.layers().index(disc), "type": "circle", "desc": f"{label} Disc"},
        {"index": session.layers().index(ring), "type": "outline", "desc": f"{label} Ring"},
    ]


_TEMPLATES = {
    "bouncing-ball": _template_bouncing_ball,
    "title-card": _template_title_card,
    "logo-reveal": _template_logo_reveal,
}
