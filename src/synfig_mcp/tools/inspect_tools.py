# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Inspection tools: project diff, JSON snapshots (export/import)."""

from __future__ import annotations

import base64
import json
from typing import Any

from lxml import etree

from ..document import io
from ..document.canvas import get_canvas_props
from ..document.layers import layer_summary
from ..document.model import ProjectSession
from ..document.params import decode_param
from ..errors import ParameterError
from ..security.paths import PROJECT_EXTENSIONS, resolve_workspace_path
from .common import AppContext, json_dumps, tool


def _decode_all_params(layer: etree._Element, fps: float, ctx: AppContext) -> list[dict[str, Any]]:
    return [
        decode_param(p, unit_px=ctx.settings.unit_px, unit_system=ctx.settings.unit_system, fps=fps)
        for p in layer.findall("param")
    ]


def _layer_key(layer: etree._Element) -> str:
    desc = layer.get("desc") or ""
    ltype = layer.get("type") or "layer"
    return f"{ltype}:{desc}"


def _snapshot_session(session: ProjectSession, ctx: AppContext) -> dict[str, Any]:
    root = session.root
    fps = float(root.get("fps", "24") or 24)
    layers = []
    for index, layer in enumerate(session.layers()):
        summary = layer_summary(layer)
        summary["index"] = index
        summary["params_decoded"] = _decode_all_params(layer, fps, ctx)
        layers.append(summary)
    raw = io.serialize(session.tree)
    return {
        "format": "synfig-mcp-snapshot/1",
        "name": session.name,
        "path": str(session.path) if session.path else None,
        "info": session.info(),
        "canvas": get_canvas_props(root),
        "layers": layers,
        "keyframes": [
            {
                "time": kf.get("time"),
                "label": (kf.text or "").strip(),
                "active": (kf.get("active", "true") or "true").lower() != "false",
            }
            for kf in root.findall("keyframe")
        ],
        "xml_base64": base64.b64encode(raw).decode("ascii"),
    }


async def _resolve_project(
    ctx: AppContext,
    project_id: str | None,
    path: str | None,
) -> ProjectSession | None:
    if project_id:
        return await ctx.registry.get(project_id)
    if path:
        resolved = resolve_workspace_path(
            path,
            ctx.settings.workspace,
            must_exist=True,
            allowed_extensions=PROJECT_EXTENSIONS,
            purpose="project",
        )
        session, _ = await ctx.registry.open(resolved)
        return session
    return None


def register(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def diff_projects(
        a: str | None = None,
        b: str | None = None,
        a_path: str | None = None,
        b_path: str | None = None,
    ) -> str:
        """Diff two open projects (or files) semantically.

        Pass a/b as project_ids, or a_path/b_path as workspace file paths.
        Reports canvas property changes, added/removed/changed layers and
        parameter-level differences (with a cap on reported changes).
        """
        session_a = await _resolve_project(ctx, a, a_path)
        session_b = await _resolve_project(ctx, b, b_path)
        if session_a is None or session_b is None:
            raise ParameterError("diff_projects needs both a/b (project_id) or a_path/b_path.")
        fps_a = float(session_a.root.get("fps", "24") or 24)
        max_changes = 100

        props_a, props_b = get_canvas_props(session_a.root), get_canvas_props(session_b.root)
        props_changed: dict[str, Any] = {}
        for key in sorted(set(props_a) | set(props_b)):
            if props_a.get(key) != props_b.get(key):
                props_changed[key] = {"a": props_a.get(key), "b": props_b.get(key)}

        layers_a = list(session_a.layers())
        layers_b = list(session_b.layers())
        by_key_a: dict[str, list[int]] = {}
        by_key_b: dict[str, list[int]] = {}
        for index, layer in enumerate(layers_a):
            by_key_a.setdefault(_layer_key(layer), []).append(index)
        for index, layer in enumerate(layers_b):
            by_key_b.setdefault(_layer_key(layer), []).append(index)

        added: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        changed: list[dict[str, Any]] = []
        used_b: set[int] = set()
        type_counts_a: dict[str, int] = {}
        type_counts_b: dict[str, int] = {}
        change_budget = max_changes

        for layer in layers_a:
            type_counts_a[layer.get("type") or "?"] = (
                type_counts_a.get(layer.get("type") or "?", 0) + 1
            )
        for layer in layers_b:
            type_counts_b[layer.get("type") or "?"] = (
                type_counts_b.get(layer.get("type") or "?", 0) + 1
            )

        for key, indices_a in by_key_a.items():
            indices_b = by_key_b.get(key, [])
            for position, index_a in enumerate(indices_a):
                if position < len(indices_b):
                    index_b = indices_b[position]
                    used_b.add(index_b)
                    if change_budget <= 0:
                        continue
                    diffs = _diff_layer(layers_a[index_a], layers_b[index_b], fps_a, ctx)
                    if diffs:
                        changed.append(
                            {"key": key, "a_index": index_a, "b_index": index_b, "changes": diffs}
                        )
                        change_budget -= len(diffs)
                else:
                    removed.append(
                        {"index": index_a, "key": key, "layer": layer_summary(layers_a[index_a])}
                    )
        for index, layer in enumerate(layers_b):
            if index not in used_b:
                added.append(
                    {"index": index, "key": _layer_key(layer), "layer": layer_summary(layer)}
                )

        return json_dumps(
            {
                "a": {
                    "project_id": session_a.project_id,
                    "path": str(session_a.path) if session_a.path else None,
                },
                "b": {
                    "project_id": session_b.project_id,
                    "path": str(session_b.path) if session_b.path else None,
                },
                "props_changed": props_changed,
                "layers_added": added,
                "layers_removed": removed,
                "layers_changed": changed,
                "type_counts": {"a": type_counts_a, "b": type_counts_b},
                "summary": {
                    "added": len(added),
                    "removed": len(removed),
                    "changed": len(changed),
                    "props_changed": len(props_changed),
                },
            }
        )

    @tool(server)
    async def export_json_snapshot(project_id: str) -> str:
        """Export a full project snapshot as JSON (includes an opaque base64 restore blob)."""
        session = await ctx.registry.get(project_id)
        snapshot = _snapshot_session(session, ctx)
        return json_dumps({"project_id": project_id, "snapshot": snapshot})

    @tool(server)
    async def import_json_snapshot(
        snapshot: str | dict[str, Any],
        new_name: str | None = None,
        path: str | None = None,
    ) -> str:
        """Create a project from an export_json_snapshot payload.

        snapshot: the JSON string (or object) produced by export_json_snapshot.
        The embedded base64 XML is restored verbatim (lossless round trip).
        path: optional workspace file to save the restored project to.
        """
        if isinstance(snapshot, str):
            try:
                payload = json.loads(snapshot)
            except json.JSONDecodeError as exc:
                raise ParameterError(f"snapshot is not valid JSON: {exc}") from exc
        else:
            payload = snapshot
        blob = payload.get("xml_base64") or (payload.get("snapshot") or {}).get("xml_base64")
        if not blob:
            raise ParameterError(
                "snapshot does not contain xml_base64.",
                hint="Pass the exact JSON object returned by export_json_snapshot (it nests under 'snapshot').",
            )
        try:
            xml_bytes = base64.b64decode(blob, validate=True)
        except Exception as exc:
            raise ParameterError(f"snapshot xml_base64 is not valid base64: {exc}") from exc
        tree = io.parse_sif(xml_bytes, source="<snapshot>")
        if new_name:
            name_el = tree.getroot().find("name")
            if name_el is not None:
                name_el.text = new_name
        session = await ctx.registry.create(
            tree, path=None, name=new_name or payload.get("name") or "restored"
        )
        saved = None
        if path:
            from ..security.paths import PROJECT_EXTENSIONS, ensure_output_path

            target = ensure_output_path(
                path,
                ctx.settings.workspace,
                default_name=f"{new_name or 'restored'}.sif",
                allowed_extensions=PROJECT_EXTENSIONS,
                purpose="project path",
            )
            io.write_project(tree, target, backup=True)
            session.path = target
            saved = str(target)
        return json_dumps(
            {
                "project_id": session.project_id,
                "saved": saved,
                "info": session.info(),
            }
        )


def _diff_layer(
    a: etree._Element,
    b: etree._Element,
    fps: float,
    ctx: AppContext,
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    for key, value_a, value_b in (
        ("active", a.get("active"), b.get("active")),
        (
            "exclude_from_rendering",
            a.get("exclude_from_rendering"),
            b.get("exclude_from_rendering"),
        ),
        ("hit_locked", a.get("hit_locked"), b.get("hit_locked")),
        ("desc", a.get("desc"), b.get("desc")),
        ("group", a.get("group"), b.get("group")),
    ):
        if (value_a or "") != (value_b or ""):
            diffs.append({"field": key, "a": value_a, "b": value_b})
    params_a = {p.get("name"): p for p in a.findall("param") if p.get("name")}
    params_b = {p.get("name"): p for p in b.findall("param") if p.get("name")}
    for name in sorted(set(params_a) | set(params_b)):
        pa, pb = params_a.get(name), params_b.get(name)
        if pa is None:
            diffs.append({"field": f"param:{name}", "a": None, "b": "present"})
            continue
        if pb is None:
            diffs.append({"field": f"param:{name}", "a": "present", "b": None})
            continue
        try:
            da = decode_param(
                pa, unit_px=ctx.settings.unit_px, unit_system=ctx.settings.unit_system, fps=fps
            )
            db = decode_param(
                pb, unit_px=ctx.settings.unit_px, unit_system=ctx.settings.unit_system, fps=fps
            )
        except Exception:
            da, db = {"raw": (pa.text or "")}, {"raw": (pb.text or "")}
        if json_dumps(da) != json_dumps(db):
            diffs.append({"field": f"param:{name}", "a": da, "b": db})
    return diffs
