# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Layer tools: create, modify, reorder, group, inspect."""

from __future__ import annotations

from typing import Any

from lxml import etree

from ..document import layers as lay
from ..document.canvas import parse_blend_method
from ..document.params import decode_param
from ..errors import ParameterError, UnknownLayerTypeError
from ..security.limits import Limits
from ..security.paths import sanitize_text
from .common import AppContext, json_dumps, tool
from .layer_shared import (
    blend_name,
    clone_with_fresh_guids,
    default_version,
    ensure_amount,
    ensure_blend,
    ensure_z_depth,
    set_param,
)


async def _set_active(
    ctx: AppContext,
    project_id: str,
    layer: str | int,
    active: bool,
) -> str:
    session = await ctx.registry.get(project_id)
    async with session.lock:
        session.record_history()
        _, target = session.resolve_layer(layer)
        lay.set_active(target, active)
        session.touch()
    await ctx.after_mutation(session)
    return json_dumps({"project_id": project_id, "active": active})


def register(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def add_layer(
        project_id: str,
        layer_type: str,
        name: str | None = None,
        params: dict[str, Any] | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
        active: bool = True,
    ) -> str:
        """Add a layer of any type to the project.

        params is a dict like {"radius": 0.5, "center": [0, 0], "color": "#ff8800"}.
        index is the paint position (0 = painted first = background).
        """
        known = await ctx.known_layer_types()
        if layer_type not in known:
            raise UnknownLayerTypeError(layer_type, known)
        session = await ctx.registry.get(project_id)
        async with session.lock:
            limits = Limits(session.settings)
            limits.check_layer_count(len(session.layers()) + 1)
            session.record_history()
            layer = etree.Element(
                "layer",
                attrib={
                    "type": layer_type,
                    "active": "true" if active else "false",
                    "version": default_version(layer_type),
                },
            )
            ensure_z_depth(layer)
            if name:
                layer.set("desc", sanitize_text(name, max_length=128))
            fps = float(session.root.get("fps", "24") or 24)
            vocab = await ctx.layer_vocab(layer_type)
            for key, value in (params or {}).items():
                set_param(
                    layer,
                    key,
                    value,
                    fps=fps,
                    unit_px=ctx.settings.unit_px,
                    unit_system=ctx.settings.unit_system,
                    vocab=vocab,
                )
            if amount is not None:
                lay.set_or_create_param(layer, "amount", float(amount), tag="real")
            else:
                ensure_amount(layer)
            if blend_method is not None:
                lay.set_or_create_param(
                    layer, "blend_method", parse_blend_method(blend_method), tag="integer"
                )
            else:
                ensure_blend(layer)
            inserted_index = lay.insert_layer(session.root, layer, index)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "index": inserted_index,
                "layer": lay.layer_summary(layer),
            }
        )

    @tool(server)
    async def delete_layer(project_id: str, layer: str | int) -> str:
        """Delete a layer (by index or name)."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            index, target = session.resolve_layer(layer)
            lay.remove_layer(session.root, target)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {"project_id": project_id, "deleted_index": index, "type": target.get("type")}
        )

    @tool(server)
    async def duplicate_layer(
        project_id: str, layer: str | int, new_name: str | None = None
    ) -> str:
        """Duplicate a layer; all GUID attributes in the copy are regenerated."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            index, target = session.resolve_layer(layer)
            clone = clone_with_fresh_guids(target)
            if new_name:
                clone.set("desc", sanitize_text(new_name, max_length=128))
            inserted = lay.insert_layer(session.root, clone, index + 1)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {"project_id": project_id, "index": inserted, "layer": lay.layer_summary(clone)}
        )

    @tool(server)
    async def move_layer(
        project_id: str,
        layer: str | int,
        index: int | None = None,
        offset: int | None = None,
        z_depth: float | None = None,
    ) -> str:
        """Move a layer in paint order (index/offset) and/or set its z_depth.

        index is absolute (0 = painted first). offset moves relative to its
        current position (positive = painted later = more visible). If only
        z_depth is given, the paint order is unchanged.
        """
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            cur_index, target = session.resolve_layer(layer)
            new_index = cur_index
            if index is not None:
                new_index = index
            elif offset is not None:
                new_index = cur_index + int(offset)
            if index is not None or offset is not None:
                layers = session.layers()
                new_index = max(0, min(len(layers) - 1, new_index))
                new_index = lay.move_layer(session.root, target, new_index)
            if z_depth is not None:
                lay.set_z_depth(target, float(z_depth))
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {"project_id": project_id, "index": new_index, "layer": lay.layer_summary(target)}
        )

    @tool(server)
    async def rename_layer(project_id: str, layer: str | int, name: str) -> str:
        """Rename a layer (sets the desc attribute shown in Studio)."""
        session = await ctx.registry.get(project_id)
        if not name or not name.strip():
            raise ParameterError("Layer name must not be empty.")
        async with session.lock:
            session.record_history()
            _, target = session.resolve_layer(layer)
            target.set("desc", sanitize_text(name, max_length=128))
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "layer": lay.layer_summary(target)})

    @tool(server)
    async def set_layer_param(
        project_id: str,
        layer: str | int,
        param: str,
        value: Any,
        type: str | None = None,
    ) -> str:
        """Set any parameter on a layer (friendly values accepted).

        Examples: {"color": "#ff8800"}, {"radius": 0.75}, {"center": [0.2, -0.1]},
        {"amount": 0.5}, {"blend_method": "multiply"}, {"bline": {...}}.
        'type' forces the value type (real, integer, angle, time, bool,
        string, color, vector, bline, gradient).
        """
        session = await ctx.registry.get(project_id)
        fps = float(session.root.get("fps", "24") or 24)
        async with session.lock:
            session.record_history()
            _, target = session.resolve_layer(layer)
            vocab = await ctx.layer_vocab(target.get("type") or "")
            el = set_param(
                target,
                param,
                value,
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
                forced_type=type,
                vocab=vocab,
            )
            session.touch()
        await ctx.after_mutation(session)
        decoded = decode_param(
            el, unit_px=ctx.settings.unit_px, unit_system=ctx.settings.unit_system, fps=fps
        )
        return json_dumps({"project_id": project_id, "param": decoded})

    @tool(server)
    async def get_layer_param(project_id: str, layer: str | int, param: str) -> str:
        """Read a parameter from a layer (decoded to friendly JSON)."""
        session = await ctx.registry.get(project_id)
        fps = float(session.root.get("fps", "24") or 24)
        target = lay.get_param(session.resolve_layer(layer)[1], param)
        decoded = decode_param(
            target,
            unit_px=ctx.settings.unit_px,
            unit_system=ctx.settings.unit_system,
            fps=fps,
        )
        return json_dumps({"project_id": project_id, "param": decoded})

    @tool(server)
    async def list_layers(project_id: str, include_params: bool = False) -> str:
        """List layers as a tree (document order; index 0 painted first)."""
        session = await ctx.registry.get(project_id)
        items = lay.list_layers(session.root, include_hidden_params=include_params)
        return json_dumps({"project_id": project_id, "count": len(items), "layers": items})

    @tool(server)
    async def get_layer(project_id: str, layer: str | int, include_params: bool = True) -> str:
        """Get one layer's summary (and params) by index or name."""
        session = await ctx.registry.get(project_id)
        index, target = session.resolve_layer(layer)
        fps = float(session.root.get("fps", "24") or 24)
        data = lay.layer_summary(target)
        data["index"] = index
        if include_params:
            data["params"] = [
                decode_param(
                    p, unit_px=ctx.settings.unit_px, unit_system=ctx.settings.unit_system, fps=fps
                )
                for p in target.findall("param")
            ]
        return json_dumps({"project_id": project_id, "layer": data})

    @tool(server)
    async def enable_layer(project_id: str, layer: str | int) -> str:
        """Enable (show/activate) a layer."""
        return await _set_active(ctx, project_id, layer, True)

    @tool(server)
    async def disable_layer(project_id: str, layer: str | int) -> str:
        """Disable (hide/deactivate) a layer without deleting it."""
        return await _set_active(ctx, project_id, layer, False)

    @tool(server)
    async def set_blend_method(project_id: str, layer: str | int, blend_method: str | int) -> str:
        """Set the blend method (e.g. 'composite', 'multiply', 'add', 'onto')."""
        session = await ctx.registry.get(project_id)
        blend = parse_blend_method(blend_method)
        async with session.lock:
            session.record_history()
            _, target = session.resolve_layer(layer)
            lay.set_or_create_param(target, "blend_method", blend, tag="integer")
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "blend_method": blend,
                "blend_method_name": blend_name(blend),
            }
        )

    @tool(server)
    async def set_amount(project_id: str, layer: str | int, amount: float) -> str:
        """Set layer opacity/amount (0..1)."""
        session = await ctx.registry.get(project_id)
        try:
            amount = float(amount)
        except (TypeError, ValueError) as exc:
            raise ParameterError("amount must be a number between 0 and 1.") from exc
        if not 0.0 <= amount <= 1.0:
            raise ParameterError("amount must be between 0 and 1.")
        async with session.lock:
            session.record_history()
            _, target = session.resolve_layer(layer)
            lay.set_or_create_param(target, "amount", amount, tag="real")
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "amount": amount})

    @tool(server)
    async def set_z_depth(project_id: str, layer: str | int, z_depth: float) -> str:
        """Set a layer's z_depth (rendering depth; higher = further back)."""
        session = await ctx.registry.get(project_id)
        try:
            z_depth = float(z_depth)
        except (TypeError, ValueError) as exc:
            raise ParameterError("z_depth must be a number.") from exc
        async with session.lock:
            session.record_history()
            _, target = session.resolve_layer(layer)
            lay.set_z_depth(target, z_depth)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "z_depth": z_depth})

    @tool(server)
    async def group_layers(project_id: str, layers: list[int], name: str | None = None) -> str:
        """Group top-level layers into a new 'group' layer (moves them into an inline canvas)."""
        if not layers:
            raise ParameterError("layers must be a non-empty list of layer indices.")
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            top = session.layers()
            indices = sorted({int(i) for i in layers})
            for i in indices:
                if i < 0 or i >= len(top):
                    raise ParameterError(f"Layer index {i} out of range (0..{len(top) - 1}).")
            chosen = [top[i] for i in indices]
            group = etree.Element(
                "layer",
                attrib={"type": "group", "active": "true", "version": "0.2"},
            )
            ensure_z_depth(group)
            ensure_amount(group)
            ensure_blend(group)
            lay.set_or_create_param(group, "time_offset", "0f", tag="time")
            if name:
                group.set("desc", sanitize_text(name, max_length=128))
            group_canvas = etree.Element("canvas")
            for layer in chosen:
                session.root.remove(layer)
                group_canvas.append(layer)
            canvas_param = etree.SubElement(group, "param")
            canvas_param.set("name", "canvas")
            canvas_param.append(group_canvas)
            first_index = min(indices)
            lay.insert_layer(session.root, group, first_index)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "group_index": first_index,
                "grouped": indices,
                "group": lay.layer_summary(group),
            }
        )

    @tool(server)
    async def ungroup_layers(project_id: str, layer: str | int) -> str:
        """Ungroup a 'group' layer: move its children back to the parent canvas."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            index, target = session.resolve_layer(layer)
            if target.get("type") != "group":
                raise ParameterError(f"Layer {index} is type {target.get('type')!r}, not a group.")
            canvas_param = lay.get_param_or_none(target, "canvas")
            inner = canvas_param.find("canvas") if canvas_param is not None else None
            if inner is None:
                raise ParameterError("Group layer has no inline canvas to unpack.")
            children = [child for child in inner if child.tag == "layer"]
            insert_at = index
            session.root.remove(target)
            for offset, child in enumerate(children):
                inner.remove(child)
                lay.insert_layer(session.root, child, insert_at + offset)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {"project_id": project_id, "ungrouped": len(children), "from_index": index}
        )

    @tool(server)
    async def lock_layer(project_id: str, layer: str | int, locked: bool = True) -> str:
        """Lock (hit_locked) a layer so it cannot be selected in Studio."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            _, target = session.resolve_layer(layer)
            lay.set_hit_locked(target, bool(locked))
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "locked": bool(locked)})

    @tool(server)
    async def exclude_from_rendering(
        project_id: str, layer: str | int, excluded: bool = True
    ) -> str:
        """Exclude (or re-include) a layer from rendering."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            _, target = session.resolve_layer(layer)
            lay.set_exclude_from_rendering(target, bool(excluded))
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "excluded": bool(excluded)})
