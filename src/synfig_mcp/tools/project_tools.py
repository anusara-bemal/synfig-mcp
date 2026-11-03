# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Project lifecycle tools: create/open/save/close/info/duplicate/validate."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..document import io
from ..document.canvas import get_canvas_props, set_canvas_props
from ..document.registry import guess_project_path
from ..document.timeutil import format_time, parse_time
from ..document.validators import validate_document
from ..errors import ParameterError
from ..security.paths import (
    PROJECT_EXTENSIONS,
    check_file_size,
    ensure_output_path,
    resolve_workspace_path,
)
from .common import AppContext, json_dumps, tool


def register(server: FastMCP, ctx: AppContext) -> None:
    @tool(server)
    async def create_project(
        name: str,
        width: int = 512,
        height: int = 512,
        fps: float = 24.0,
        begin_time: str = "0f",
        end_time: str = "5s 0f",
        background: str | None = None,
        x_res: float = 2834.645910,
        y_res: float = 2834.645910,
        view_box: list[float] | None = None,
        gamma: list[float] | float | None = None,
        antialias: int = 1,
        path: str | None = None,
        save: bool = True,
    ) -> str:
        """Create a new empty Synfig project.

        background: '#rrggbb[aa]' or 'r g b a' (0..1). view_box: [minx, maxy,
        maxx, miny] in canvas units. gamma: single value or [r, g, b]. If
        save=True the project is written to the workspace immediately.
        Returns JSON with project_id and the saved path.
        """
        workspace = ctx.settings.workspace
        limits = ctx.registry.limits
        limits.check_resolution(int(width), int(height))
        clean_name = _clean_name(name)
        begin_s = parse_time(begin_time, fps=float(fps))
        end_s = parse_time(end_time, fps=float(fps))
        if end_s < begin_s:
            raise ParameterError("end_time must be >= begin_time.")
        bg = _parse_bgcolor(background)
        view = tuple(float(v) for v in view_box) if view_box else None
        if view is not None and len(view) != 4:
            raise ParameterError("view_box must have exactly 4 numbers: [minx, maxy, maxx, miny].")
        gamma_tuple = _parse_gamma(gamma)
        tree = io.new_project_xml(
            width=int(width),
            height=int(height),
            fps=float(fps),
            begin_time=format_time(begin_s, fps=float(fps)),
            end_time=format_time(end_s, fps=float(fps)),
            name=clean_name,
            bgcolor=bg,
            antialias=int(antialias),
            xres=float(x_res),
            yres=float(y_res),
            view_box=view,
            gamma=gamma_tuple,
        )
        saved_path: Path | None = None
        if save:
            target = (
                ensure_output_path(
                    path,
                    workspace,
                    default_name=clean_name + ".sif",
                    allowed_extensions=PROJECT_EXTENSIONS,
                    purpose="project path",
                )
                if path
                else guess_project_path(workspace, clean_name)
            )
            if target.exists():
                check_file_size(target, ctx.settings.max_file_bytes, "project")
            io.write_project(tree, target, backup=True)
            saved_path = target
        session = await ctx.registry.create(tree, path=saved_path, name=clean_name)
        return json_dumps(
            {
                "project_id": session.project_id,
                "name": clean_name,
                "saved": str(saved_path) if saved_path else None,
                "info": session.info(),
            }
        )

    @tool(server)
    async def open_project(path: str) -> str:
        """Open an existing .sif/.sifz/.sfg project from the workspace.

        If the same file is already open, returns the existing project_id.
        """
        resolved = resolve_workspace_path(
            path,
            ctx.settings.workspace,
            must_exist=True,
            allowed_extensions=PROJECT_EXTENSIONS,
            purpose="project",
        )
        session, created = await ctx.registry.open(resolved)
        return json_dumps(
            {
                "project_id": session.project_id,
                "already_open": not created,
                "info": session.info(),
            }
        )

    @tool(server)
    async def save_project(project_id: str, path: str | None = None, backup: bool = True) -> str:
        """Save a project back to disk (.sif, .sifz or .sfg).

        If path is omitted, saves to the file the project was opened from
        (a newly created, unsaved project is written to the workspace under
        its name). Backup creates a .bak copy before overwriting.
        """
        session = await ctx.registry.get(project_id)
        async with session.lock:
            target = (
                resolve_workspace_path(
                    path,
                    ctx.settings.workspace,
                    allowed_extensions=PROJECT_EXTENSIONS,
                    purpose="project path",
                )
                if path
                else session.path
                or guess_project_path(ctx.settings.workspace, session.name or session.project_id)
            )
            io.write_project(session.tree, target, backup=backup)
            session.path = target
            session.dirty = False
            if target.resolve().is_file():
                ctx.registry._by_path[str(target.resolve())] = session.project_id
        return json_dumps(
            {
                "project_id": project_id,
                "saved": str(target),
                "format": target.suffix.lower().lstrip("."),
                "backup": backup,
            }
        )

    @tool(server)
    async def save_project_as(project_id: str, path: str, backup: bool = True) -> str:
        """Save a project to a new path (.sif, .sifz or .sfg)."""
        return await save_project(project_id, path=path, backup=backup)

    @tool(server)
    async def close_project(project_id: str, save: bool = False) -> str:
        """Close an open project. If save=True the project is saved first.

        Unsaved changes are reported as discarded when save=False.
        """
        session = await ctx.registry.get(project_id)
        discarded = session.dirty
        if save:
            await save_project(project_id)
        await ctx.registry.close(project_id)
        return json_dumps(
            {
                "project_id": project_id,
                "closed": True,
                "saved": save,
                "discarded_unsaved_changes": discarded and not save,
            }
        )

    @tool(server)
    async def list_open_projects() -> str:
        """List all projects open in this session."""
        return json_dumps({"projects": await ctx.registry.list()})

    @tool(server)
    async def get_project_info(project_id: str) -> str:
        """Return detailed info about an open project."""
        session = await ctx.registry.get(project_id)
        info = session.info()
        info["canvas"] = get_canvas_props(session.root)
        return json_dumps(info)

    @tool(server)
    async def set_canvas_properties(
        project_id: str,
        width: int | None = None,
        height: int | None = None,
        x_res: float | None = None,
        y_res: float | None = None,
        view_box: list[float] | None = None,
        antialias: int | None = None,
        background: str | None = None,
        gamma: list[float] | float | None = None,
    ) -> str:
        """Update canvas properties (size, resolution, view-box, AA, background, gamma)."""
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            updates: dict[str, Any] = {
                "width": width,
                "height": height,
                "xres": x_res,
                "yres": y_res,
                "antialias": antialias,
            }
            if view_box is not None:
                if len(view_box) != 4:
                    raise ParameterError("view_box must be [minx, maxy, maxx, miny].")
                updates["view_box"] = list(view_box)
            if background is not None:
                updates["background"] = _parse_bgcolor(background)
            if gamma is not None:
                updates["gamma"] = list(gamma) if isinstance(gamma, (list, tuple)) else float(gamma)
            applied = set_canvas_props(
                session.root, updates, max_resolution=ctx.settings.max_resolution
            )
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {"project_id": project_id, "applied": applied, "canvas": get_canvas_props(session.root)}
        )

    @tool(server)
    async def set_time_range(project_id: str, begin_time: str, end_time: str) -> str:
        """Set the animation time range (e.g. '0f' → '5s 0f')."""
        session = await ctx.registry.get(project_id)
        fps = float(session.root.get("fps", "24") or 24)
        begin_s = parse_time(begin_time, fps=fps)
        end_s = parse_time(end_time, fps=fps)
        if end_s < begin_s:
            raise ParameterError("end_time must be >= begin_time.")
        async with session.lock:
            session.record_history()
            session.root.set("begin-time", format_time(begin_s, fps=fps))
            session.root.set("end-time", format_time(end_s, fps=fps))
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "begin_time": session.root.get("begin-time"),
                "end_time": session.root.get("end-time"),
            }
        )

    @tool(server)
    async def set_fps(project_id: str, fps: float) -> str:
        """Set the canvas frame rate (frames per second)."""
        try:
            fps = float(fps)
        except (TypeError, ValueError) as exc:
            raise ParameterError("fps must be a number.") from exc
        if not 1.0 <= fps <= 240.0:
            raise ParameterError("fps must be between 1 and 240.")
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            session.root.set("fps", f"{fps:.3f}")
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "fps": fps})

    @tool(server)
    async def set_image_span(project_id: str, span: float) -> str:
        """Set the render span (diagonal size of the image window).

        Stored as canvas meta 'image_span'; render tools also accept span
        directly as a parameter (passed to synfig as --span).
        """
        try:
            span = float(span)
        except (TypeError, ValueError) as exc:
            raise ParameterError("span must be a number.") from exc
        if span <= 0:
            raise ParameterError("span must be positive.")
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            root = session.root
            meta = None
            for child in root.findall("meta"):
                if child.get("name") == "image_span":
                    meta = child
                    break
            if meta is None:
                meta = root.makeelement("meta", {"name": "image_span", "content": f"{span:.6f}"})
                # meta goes after <name>/<desc>, before keyframes/bones/defs/layers
                anchor = None
                for child in root:
                    if child.tag in {"keyframe", "bones", "defs", "layer"}:
                        anchor = child
                        break
                if anchor is not None:
                    anchor.addprevious(meta)
                else:
                    root.append(meta)
            meta.set("content", f"{span:.6f}")
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "image_span": span})

    @tool(server)
    async def duplicate_project(
        project_id: str,
        path: str | None = None,
        new_name: str | None = None,
        backup: bool = True,
    ) -> str:
        """Duplicate a project to a new file (and open the copy)."""
        session = await ctx.registry.get(project_id)
        base_name = new_name or f"{session.name}-copy"
        clean_name = _clean_name(base_name)
        target = (
            resolve_workspace_path(
                path,
                ctx.settings.workspace,
                allowed_extensions=PROJECT_EXTENSIONS,
                purpose="project path",
            )
            if path
            else guess_project_path(ctx.settings.workspace, clean_name)
        )
        snapshot = io.serialize(session.tree)
        dup_tree = io.parse_sif(snapshot, source="<duplicate>")
        if new_name:
            name_el = dup_tree.getroot().find("name")
            if name_el is not None:
                name_el.text = new_name
        io.write_project(dup_tree, target, backup=backup)
        dup = await ctx.registry.create(dup_tree, path=target, name=new_name or target.stem)
        return json_dumps(
            {
                "project_id": dup.project_id,
                "source_project_id": project_id,
                "path": str(target),
                "info": dup.info(),
            }
        )

    @tool(server)
    async def validate_project(project_id: str | None = None, path: str | None = None) -> str:
        """Validate an open project (or a file) structurally.

        Returns errors/warnings with codes and hints; 'valid' is true when
        there are no errors.
        """
        if project_id is None and path is None:
            raise ParameterError("Pass either project_id or path.")
        if path is not None:
            resolved = resolve_workspace_path(
                path,
                ctx.settings.workspace,
                must_exist=True,
                allowed_extensions=PROJECT_EXTENSIONS,
                purpose="project",
            )
            check_file_size(resolved, ctx.settings.max_file_bytes, "project")
            tree = io.read_project(resolved, ctx.registry.limits)
            report = validate_document(
                tree.getroot(),
                max_resolution=ctx.settings.max_resolution,
                max_layers=ctx.settings.max_layers,
            )
            report["path"] = str(resolved)
            return json_dumps(report)
        session = await ctx.registry.get(project_id or "")
        async with session.lock:
            report = validate_document(
                session.root,
                max_resolution=ctx.settings.max_resolution,
                max_layers=ctx.settings.max_layers,
            )
        report["path"] = str(session.path) if session.path else None
        return json_dumps(report)


_NAME_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _clean_name(name: str) -> str:
    if not name or not name.strip():
        raise ParameterError("Project name must not be empty.")
    cleaned = _NAME_BAD_CHARS.sub("_", name.strip())
    return cleaned[:120]


def _parse_bgcolor(background: str | list[float] | None) -> tuple[float, float, float, float]:
    if background is None:
        return (0.5, 0.5, 0.5, 1.0)
    if isinstance(background, (list, tuple)) and len(background) in (3, 4):
        channels = [max(0.0, min(1.0, float(v))) for v in background]
        if len(channels) == 3:
            channels.append(1.0)
        return (channels[0], channels[1], channels[2], channels[3])
    if isinstance(background, str):
        text = background.strip()
        if text.startswith("#"):
            from ..document.params import parse_color_text

            return parse_color_text(text)
        parts = text.split()
        try:
            channels = [float(p) for p in parts]
        except ValueError as exc:
            raise ParameterError("background must be 'r g b a' (floats) or '#rrggbb[aa]'.") from exc
        if len(channels) == 3:
            channels.append(1.0)
        if len(channels) != 4:
            raise ParameterError("background must have 3 or 4 components.")
        return (channels[0], channels[1], channels[2], channels[3])
    raise ParameterError("background must be a string or [r, g, b, (a)].")


def _parse_gamma(gamma: list[float] | float | None) -> tuple[float, float, float] | None:
    if gamma is None:
        return None
    if isinstance(gamma, (int, float)):
        value = float(gamma)
        return (value, value, value)
    if isinstance(gamma, (list, tuple)) and len(gamma) == 3:
        return (float(gamma[0]), float(gamma[1]), float(gamma[2]))
    raise ParameterError("gamma must be a single number or [r, g, b].")
