# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Shape and content tools: circle/rect/polygon/star/bline/gradients/text/image."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree

from ..document import layers as lay
from ..document.canvas import parse_blend_method
from ..errors import ParameterError
from ..security.limits import Limits
from ..security.paths import IMAGE_EXTENSIONS, resolve_workspace_path, sanitize_text
from .common import AppContext, json_dumps, tool
from .layer_shared import (
    clone_with_fresh_guids,  # noqa: F401  (re-used by batch duplicate flows)
    default_version,
    ensure_amount,
    ensure_blend,
    ensure_z_depth,
    set_param,
)

GRADIENT_LAYER_TYPES = {
    "linear": "linear_gradient",
    "radial": "radial_gradient",
    "conical": "conical_gradient",
    "spiral": "spiral_gradient",
}


async def _create_layer(
    ctx: AppContext,
    project_id: str,
    layer_type: str,
    *,
    name: str | None = None,
    params: dict[str, Any] | None = None,
    index: int | None = None,
    amount: float | None = None,
    blend_method: str | int | None = None,
    active: bool = True,
) -> tuple[dict[str, Any], str]:
    session = await ctx.registry.get(project_id)
    fps = float(session.root.get("fps", "24") or 24)
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
        ensure_amount(layer)
        ensure_blend(layer)
        if name:
            layer.set("desc", sanitize_text(name, max_length=128))
        params = dict(params or {})
        bline_ref = params.pop("__bline_ref__", None)
        for key, value in params.items():
            set_param(
                layer,
                key,
                value,
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
        if bline_ref is not None:
            lay.set_or_create_param(layer, "bline", None, reference=bline_ref)
        if amount is not None:
            lay.set_or_create_param(layer, "amount", float(amount), tag="real")
        if blend_method is not None:
            lay.set_or_create_param(
                layer, "blend_method", parse_blend_method(blend_method), tag="integer"
            )
        index = lay.insert_layer(session.root, layer, index)
        session.touch()
    await ctx.after_mutation(session)
    return lay.layer_summary(layer), json_dumps(
        {
            "project_id": project_id,
            "index": index,
            "layer": lay.layer_summary(layer),
        }
    )


def register(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def add_circle(
        project_id: str,
        center: list[float] | None = None,
        radius: float = 0.5,
        color: str | list[float] | None = None,
        feather: float = 0.0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a circle layer (default grey, radius 0.5 units)."""
        _, js = await _create_layer(
            ctx,
            project_id,
            "circle",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params={
                "origin": center or [0.0, 0.0],
                "radius": float(radius),
                "color": color or "#b3b3b3",
                "feather": float(feather),
            },
        )
        return js

    @tool(server)
    async def add_rectangle(
        project_id: str,
        point1: list[float] | None = None,
        point2: list[float] | None = None,
        color: str | list[float] | None = None,
        expand: float = 0.0,
        bevel: float = 0.0,
        feather_x: float = 0.0,
        feather_y: float = 0.0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a rectangle layer between two corner points (default 1x1 at origin)."""
        _, js = await _create_layer(
            ctx,
            project_id,
            "rectangle",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params={
                "point1": point1 or [-0.5, 0.5],
                "point2": point2 or [0.5, -0.5],
                "color": color or "#b3b3b3",
                "expand": float(expand),
                "bevel": float(bevel),
                "feather_x": float(feather_x),
                "feather_y": float(feather_y),
            },
        )
        return js

    @tool(server)
    async def add_polygon(
        project_id: str,
        vertices: list[list[float]],
        color: str | list[float] | None = None,
        origin: list[float] | None = None,
        feather: float = 0.0,
        winding_style: int = 0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a filled polygon from vertices ([[x, y], ...])."""
        if len(vertices) < 3:
            raise ParameterError("A polygon needs at least 3 vertices.")
        _, js = await _create_layer(
            ctx,
            project_id,
            "polygon",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params={
                "vector_list": {"vertices": [list(v) for v in vertices]},
                "color": color or "#b3b3b3",
                "origin": origin or [0.0, 0.0],
                "feather": float(feather),
                "winding_style": int(winding_style),
            },
        )
        return js

    @tool(server)
    async def add_star(
        project_id: str,
        points: int = 5,
        radius1: float = 0.5,
        radius2: float = 0.2,
        angle: float = 90.0,
        regular_polygon: bool = False,
        color: str | list[float] | None = None,
        origin: list[float] | None = None,
        feather: float = 0.0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a star (or regular polygon when regular_polygon=True)."""
        if int(points) < 3 or int(points) > 64:
            raise ParameterError("points must be between 3 and 64.")
        _, js = await _create_layer(
            ctx,
            project_id,
            "star",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params={
                "points": int(points),
                "radius1": float(radius1),
                "radius2": float(radius2),
                "angle": float(angle),
                "regular_polygon": bool(regular_polygon),
                "color": color or "#b3b3b3",
                "origin": origin or [0.0, 0.0],
                "feather": float(feather),
            },
        )
        return js

    @tool(server)
    async def add_region(
        project_id: str,
        vertices: list[list[float]] | None = None,
        bline_id: str | None = None,
        tangents: list[list[float]] | None = None,
        width: float = 1.0,
        loop: bool = True,
        color: str | list[float] | None = None,
        feather: float = 0.0,
        winding_style: int = 0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a filled region (bline spline area).

        Pass either vertices (inline bline) or bline_id (reference an exported
        bline from defs/add_bline). tangents are per-vertex tangent vectors.
        """
        params = _bline_params(vertices, bline_id, tangents, width, loop)
        params.update(
            {
                "color": color or "#b3b3b3",
                "feather": float(feather),
                "winding_style": int(winding_style),
            }
        )
        _, js = await _create_layer(
            ctx,
            project_id,
            "region",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params=params,
        )
        return js

    @tool(server)
    async def add_outline(
        project_id: str,
        vertices: list[list[float]] | None = None,
        bline_id: str | None = None,
        tangents: list[list[float]] | None = None,
        width: float = 0.05,
        loop: bool = False,
        color: str | list[float] | None = None,
        feather: float = 0.0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add an outline (stroked bline)."""
        params = _bline_params(vertices, bline_id, tangents, 1.0, loop)
        params.update(
            {
                "color": color or "#000000",
                "width": float(width),
                "feather": float(feather),
            }
        )
        _, js = await _create_layer(
            ctx,
            project_id,
            "outline",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params=params,
        )
        return js

    @tool(server)
    async def add_advanced_outline(
        project_id: str,
        vertices: list[list[float]] | None = None,
        bline_id: str | None = None,
        tangents: list[list[float]] | None = None,
        width: float = 0.05,
        loop: bool = False,
        start_tip: int = 0,
        end_tip: int = 0,
        color: str | list[float] | None = None,
        feather: float = 0.0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add an advanced outline (width-profile stroked bline)."""
        params = _bline_params(vertices, bline_id, tangents, 1.0, loop)
        params.update(
            {
                "color": color or "#000000",
                "width": float(width),
                "feather": float(feather),
                "start_tip": int(start_tip),
                "end_tip": int(end_tip),
            }
        )
        _, js = await _create_layer(
            ctx,
            project_id,
            "advanced_outline",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params=params,
        )
        return js

    @tool(server)
    async def add_bline(
        project_id: str,
        id: str,
        vertices: list[list[float]],
        tangents: list[list[float]] | None = None,
        width: float = 1.0,
        loop: bool = True,
    ) -> str:
        """Create an exported (defs) bline with the given id.

        Returns the defs id to reference from region/outline layers via bline_id.
        """
        if len(vertices) < 2:
            raise ParameterError("A bline needs at least 2 vertices.")
        session = await ctx.registry.get(project_id)
        async with session.lock:
            session.record_history()
            defs = session.defs(create=True)
            assert defs is not None
            if _defs_has(defs, id):
                raise ParameterError(f"A defs entry named {id!r} already exists.")
            from ..document.params import encode_bline

            bline = encode_bline(
                {
                    "vertices": [list(v) for v in vertices],
                    "t1": [list(t) for t in tangents] if tangents else [],
                    "width": float(width),
                    "loop": bool(loop),
                },
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
            bline.set("id", _clean_id(id))
            defs.append(bline)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "bline_id": _clean_id(id),
                "vertices": len(vertices),
                "loop": bool(loop),
            }
        )

    @tool(server)
    async def add_text(
        project_id: str,
        text: str,
        origin: list[float] | None = None,
        family: str = "sans-serif",
        size: list[float] | float = 0.6,
        weight: int = 400,
        color: str | list[float] | None = None,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a text layer. Text is sanitized (control chars stripped)."""
        clean_text = sanitize_text(text, max_length=2048)
        if not clean_text.strip():
            raise ParameterError("text must not be empty.")
        size_value: Any = size if isinstance(size, (list, tuple)) else [float(size), float(size)]
        _, js = await _create_layer(
            ctx,
            project_id,
            "text",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params={
                "text": clean_text,
                "orient": [0.5, 0.5],
                "origin": origin or [0.0, 0.0],
                "family": sanitize_text(family, max_length=128),
                "weight": int(weight),
                "size": size_value,
                "color": color or "#000000",
            },
        )
        return js

    @tool(server)
    async def add_gradient(
        project_id: str,
        kind: str = "linear",
        stops: list[dict[str, Any]] | None = None,
        gradient_id: str | None = None,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
        p1: list[float] | None = None,
        p2: list[float] | None = None,
        center: list[float] | None = None,
        radius: float = 1.0,
        angle: float = 0.0,
        loop: bool = False,
        zigzag: bool = False,
    ) -> str:
        """Add a gradient layer (linear, radial, conical or spiral).

        stops: [{"pos": 0..1, "color": "#rrggbb"}, ...] — creates an inline gradient.
        gradient_id: reference an existing defs gradient instead of creating one.
        """
        kind_key = kind.strip().lower()
        layer_type = GRADIENT_LAYER_TYPES.get(kind_key)
        if layer_type is None:
            raise ParameterError(
                f"Unknown gradient kind {kind!r}.",
                hint=f"Use one of: {', '.join(sorted(GRADIENT_LAYER_TYPES))}.",
            )
        if bool(stops) == bool(gradient_id):
            raise ParameterError(
                "Pass exactly one of 'stops' (inline gradient) or 'gradient_id' (reference)."
            )
        params: dict[str, Any] = {}
        gradient_value: Any
        if stops:
            gradient_value = [
                {"pos": float(stop.get("pos", 0.0)), "color": stop.get("color", "#000000")}
                for stop in stops
            ]
            params["gradient"] = gradient_value
        else:
            params["gradient"] = None  # set as reference below
        if layer_type in {"linear_gradient"}:
            params["p1"] = p1 or [1.0, 1.0]
            params["p2"] = p2 or [-1.0, -1.0]
            params["loop"] = bool(loop)
            params["zigzag"] = bool(zigzag)
        elif layer_type in {"radial_gradient", "spiral_gradient", "conical_gradient"}:
            params["center"] = center or [0.0, 0.0]
            if layer_type != "conical_gradient":
                params["radius"] = float(radius)
            if layer_type == "spiral_gradient":
                params["angle"] = float(angle)
                params["clockwise"] = False
            if layer_type == "conical_gradient":
                params["angle"] = float(angle)
                params["symmetric"] = False
            if layer_type == "radial_gradient":
                params["loop"] = bool(loop)
                params["zigzag"] = bool(zigzag)
        session = await ctx.registry.get(project_id)
        fps = float(session.root.get("fps", "24") or 24)
        async with session.lock:
            limits = Limits(session.settings)
            limits.check_layer_count(len(session.layers()) + 1)
            session.record_history()
            layer = etree.Element(
                "layer",
                attrib={
                    "type": layer_type,
                    "active": "true",
                    "version": default_version(layer_type),
                },
            )
            ensure_z_depth(layer)
            ensure_amount(layer)
            ensure_blend(layer)
            if name:
                layer.set("desc", sanitize_text(name, max_length=128))
            for key, value in params.items():
                if key == "gradient":
                    if gradient_id:
                        lay.set_or_create_param(layer, "gradient", None, reference=gradient_id)
                    else:
                        set_param(
                            layer,
                            "gradient",
                            value,
                            fps=fps,
                            unit_px=ctx.settings.unit_px,
                            unit_system=ctx.settings.unit_system,
                        )
                    continue
                set_param(
                    layer,
                    key,
                    value,
                    fps=fps,
                    unit_px=ctx.settings.unit_px,
                    unit_system=ctx.settings.unit_system,
                )
            if amount is not None:
                lay.set_or_create_param(layer, "amount", float(amount), tag="real")
            if blend_method is not None:
                lay.set_or_create_param(
                    layer, "blend_method", parse_blend_method(blend_method), tag="integer"
                )
            index = lay.insert_layer(session.root, layer, index)
            session.touch()
        await ctx.after_mutation(session)
        return json_dumps(
            {
                "project_id": project_id,
                "index": index,
                "gradient_kind": kind_key,
                "layer": lay.layer_summary(layer),
            }
        )

    @tool(server)
    async def add_image(
        project_id: str,
        filename: str,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
        tl: list[float] | None = None,
        br: list[float] | None = None,
    ) -> str:
        """Add an imported-image layer. filename must be inside the workspace."""
        resolved = resolve_workspace_path(
            filename,
            ctx.settings.workspace,
            must_exist=True,
            allowed_extensions=IMAGE_EXTENSIONS,
            purpose="image",
        )
        params: dict[str, Any] = {"filename": str(resolved)}
        if tl is not None:
            params["tl"] = list(tl)
        if br is not None:
            params["br"] = list(br)
        _, js = await _create_layer(
            ctx,
            project_id,
            "import",
            name=name or Path(resolved).name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params=params,
        )
        return js

    @tool(server)
    async def add_solid_color(
        project_id: str,
        color: str | list[float] = "#808080",
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a solid color layer."""
        _, js = await _create_layer(
            ctx,
            project_id,
            "solid_color",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params={"color": color},
        )
        return js

    @tool(server)
    async def add_checkerboard(
        project_id: str,
        color: str | list[float] = "#808080",
        pos: list[float] | None = None,
        size: list[float] | None = None,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a checkerboard pattern layer."""
        _, js = await _create_layer(
            ctx,
            project_id,
            "checker_board",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params={"color": color, "origin": pos or [0.125, 0.125], "size": size or [0.25, 0.25]},
        )
        return js

    @tool(server)
    async def add_noise_gradient(
        project_id: str,
        stops: list[dict[str, Any]] | None = None,
        seed: int = 12345,
        size: list[float] | None = None,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a noise layer (noise-driven gradient fill).

        stops defaults to a black→white two-color gradient.
        """
        gradient = stops or [
            {"pos": 0.0, "color": "#000000"},
            {"pos": 1.0, "color": "#ffffff"},
        ]
        _, js = await _create_layer(
            ctx,
            project_id,
            "noise",
            name=name,
            index=index,
            amount=amount,
            blend_method=blend_method,
            params={
                "gradient": gradient,
                "seed": int(seed),
                "size": size or [0.6, 0.6],
                "smooth": 4,
                "detail": 1,
            },
        )
        return js


def _defs_has(defs: etree._Element, entry_id: str) -> bool:
    return any(isinstance(child.tag, str) and child.get("id") == entry_id for child in defs)


def _clean_id(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned or any(ch in cleaned for ch in " :#@$^&()*\t\n\r"):
        raise ParameterError(f"Invalid id {value!r}. Use letters, digits, '-' and '_'.")
    if cleaned[0].isdigit():
        raise ParameterError("IDs must not start with a digit.")
    return cleaned[:64]


def _bline_params(
    vertices: list[list[float]] | None,
    bline_id: str | None,
    tangents: list[list[float]] | None,
    width: float,
    loop: bool,
) -> dict[str, Any]:
    if bool(vertices) == bool(bline_id):
        raise ParameterError("Pass exactly one of 'vertices' (inline) or 'bline_id' (reference).")
    if bline_id is not None:
        return {"__bline_ref__": _clean_id(bline_id)}
    assert vertices is not None
    if len(vertices) < 2:
        raise ParameterError("A bline needs at least 2 vertices.")
    spec: dict[str, Any] = {
        "vertices": [list(v) for v in vertices],
        "width": float(width),
        "loop": bool(loop),
    }
    if tangents:
        spec["t1"] = [list(t) for t in tangents]
    return {"bline": spec}


# ---------------------------------------------------------------------------
# Filters and effects
# ---------------------------------------------------------------------------


async def _effect(
    ctx: AppContext,
    project_id: str,
    layer_type: str,
    params: dict[str, Any],
    name: str | None,
    index: int | None,
    amount: float | None,
    blend_method: str | int | None,
) -> str:
    session = await ctx.registry.get(project_id)
    fps = float(session.root.get("fps", "24") or 24)
    async with session.lock:
        limits = Limits(session.settings)
        limits.check_layer_count(len(session.layers()) + 1)
        session.record_history()
        layer = etree.Element(
            "layer",
            attrib={"type": layer_type, "active": "true", "version": default_version(layer_type)},
        )
        ensure_z_depth(layer)
        if layer_type != "stretch":  # stretch's `amount` is a vector, not opacity
            ensure_amount(layer)
        ensure_blend(layer)
        if name:
            layer.set("desc", sanitize_text(name, max_length=128))
        for key, value in params.items():
            set_param(
                layer,
                key,
                value,
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
        if amount is not None:
            lay.set_or_create_param(layer, "amount", float(amount), tag="real")
        if blend_method is not None:
            lay.set_or_create_param(
                layer, "blend_method", parse_blend_method(blend_method), tag="integer"
            )
        index = lay.insert_layer(session.root, layer, index)
        session.touch()
    await ctx.after_mutation(session)
    return json_dumps(
        {
            "project_id": project_id,
            "index": index,
            "layer": lay.layer_summary(layer),
        }
    )


def register_filters(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def add_blur(
        project_id: str,
        size: list[float] | None = None,
        type: int = 1,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a blur filter (size in canvas units, type 0/1/2)."""
        return await _effect(
            ctx,
            project_id,
            "blur",
            {"size": size or [0.1, 0.1], "type": int(type)},
            name,
            index,
            amount,
            blend_method,
        )

    @tool(server)
    async def add_motion_blur(
        project_id: str,
        aperture: float = 1.0,
        subsamples_factor: float = 1.0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
    ) -> str:
        """Add a motion blur filter (aperture in frames)."""
        return await _effect(
            ctx,
            project_id,
            "motion_blur",
            {"aperture": float(aperture), "subsamples_factor": float(subsamples_factor)},
            name,
            index,
            amount,
            None,
        )

    @tool(server)
    async def add_color_correct(
        project_id: str,
        hue_adjust: float = 0.0,
        brightness: float = 0.0,
        contrast: float = 0.0,
        exposure: float = 0.0,
        saturation: float = 0.0,
        gamma: float = 1.0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
    ) -> str:
        """Add a color correction filter."""
        return await _effect(
            ctx,
            project_id,
            "colorcorrect",
            {
                "hue_adjust": float(hue_adjust),
                "brightness": float(brightness),
                "contrast": float(contrast),
                "exposure": float(exposure),
                "saturation": float(saturation),
                "gamma": float(gamma),
            },
            name,
            index,
            amount,
            None,
        )

    @tool(server)
    async def add_halftone(
        project_id: str,
        kind: str = "halftone2",
        origin: list[float] | None = None,
        angle: float = 45.0,
        size: list[float] | None = None,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a halftone filter (kind: halftone2 or halftone3)."""
        kind = kind.strip().lower()
        if kind not in {"halftone2", "halftone3"}:
            raise ParameterError("halftone kind must be 'halftone2' or 'halftone3'.")
        return await _effect(
            ctx,
            project_id,
            kind,
            {"origin": origin or [0.0, 0.0], "angle": float(angle), "size": size or [0.1, 0.1]},
            name,
            index,
            amount,
            blend_method,
        )

    @tool(server)
    async def add_clamp(
        project_id: str,
        floor: float = 0.0,
        ceiling: float = 1.0,
        invert_negative: bool = True,
        clamp_ceiling: bool = True,
        name: str | None = None,
        index: int | None = None,
    ) -> str:
        """Add a clamp filter (limits the value range)."""
        return await _effect(
            ctx,
            project_id,
            "clamp",
            {
                "floor": float(floor),
                "ceiling": float(ceiling),
                "invert_negative": bool(invert_negative),
                "clamp_ceiling": bool(clamp_ceiling),
            },
            name,
            index,
            None,
            None,
        )

    @tool(server)
    async def add_stretch(
        project_id: str,
        amount: list[float] | None = None,
        center: list[float] | None = None,
        name: str | None = None,
        index: int | None = None,
    ) -> str:
        """Add a stretch filter. amount = scale per axis (default [1, 1])."""
        return await _effect(
            ctx,
            project_id,
            "stretch",
            {"amount": amount or [1.0, 1.0], "center": center or [0.0, 0.0]},
            name,
            index,
            None,
            None,
        )

    @tool(server)
    async def add_rotate(
        project_id: str,
        angle: float = 0.0,
        origin: list[float] | None = None,
        name: str | None = None,
        index: int | None = None,
    ) -> str:
        """Add a rotate filter (angle in degrees)."""
        return await _effect(
            ctx,
            project_id,
            "rotate",
            {"origin": origin or [0.0, 0.0], "amount": float(angle)},
            name,
            index,
            None,
            None,
        )

    @tool(server)
    async def add_translate(
        project_id: str,
        offset: list[float] | None = None,
        name: str | None = None,
        index: int | None = None,
    ) -> str:
        """Add a translate filter (moves layers by offset in canvas units)."""
        return await _effect(
            ctx, project_id, "translate", {"origin": offset or [0.0, 0.0]}, name, index, None, None
        )

    @tool(server)
    async def add_zoom(
        project_id: str,
        amount: float = 1.0,
        center: list[float] | None = None,
        name: str | None = None,
        index: int | None = None,
    ) -> str:
        """Add a zoom filter (amount=1 is identity)."""
        return await _effect(
            ctx,
            project_id,
            "zoom",
            {"center": center or [0.0, 0.0], "amount": float(amount)},
            name,
            index,
            None,
            None,
        )

    @tool(server)
    async def add_twirl(
        project_id: str,
        center: list[float] | None = None,
        radius: float = 1.0,
        rotations: float = 30.0,
        distort_inside: bool = True,
        distort_outside: bool = True,
        name: str | None = None,
        index: int | None = None,
    ) -> str:
        """Add a twirl (swirl distortion) filter."""
        return await _effect(
            ctx,
            project_id,
            "twirl",
            {
                "center": center or [0.0, 0.0],
                "radius": float(radius),
                "rotations": float(rotations),
                "distort_inside": bool(distort_inside),
                "distort_outside": bool(distort_outside),
            },
            name,
            index,
            None,
            None,
        )

    @tool(server)
    async def add_bevel(
        project_id: str,
        type: int = 0,
        color1: str | list[float] = "#ffffff",
        color2: str | list[float] = "#000000",
        angle: float = 45.0,
        depth: float = 0.1,
        softness: float = 0.0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a bevel filter (fake 3D emboss)."""
        return await _effect(
            ctx,
            project_id,
            "bevel",
            {
                "type": int(type),
                "color1": color1,
                "color2": color2,
                "angle": float(angle),
                "depth": float(depth),
                "softness": float(softness),
            },
            name,
            index,
            amount,
            blend_method,
        )

    @tool(server)
    async def add_shade(
        project_id: str,
        color: str | list[float] = "#000000",
        origin: list[float] | None = None,
        size: list[float] | None = None,
        type: int = 0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a shadow/shade filter."""
        return await _effect(
            ctx,
            project_id,
            "shade",
            {
                "color": color,
                "origin": origin or [0.0, 0.0],
                "size": size or [0.1, 0.1],
                "type": int(type),
            },
            name,
            index,
            amount,
            blend_method,
        )

    @tool(server)
    async def add_radial_blur(
        project_id: str,
        origin: list[float] | None = None,
        size: list[float] | None = None,
        fade_out: bool = False,
        name: str | None = None,
        index: int | None = None,
    ) -> str:
        """Add a radial blur filter."""
        return await _effect(
            ctx,
            project_id,
            "radial_blur",
            {
                "origin": origin or [0.0, 0.0],
                "size": size or [0.1, 0.1],
                "fade_out": bool(fade_out),
            },
            name,
            index,
            None,
            None,
        )

    @tool(server)
    async def add_distortions(
        project_id: str,
        displacement: float = 0.05,
        size: list[float] | None = None,
        seed: int = 12345,
        smooth: int = 4,
        detail: int = 1,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
    ) -> str:
        """Add a noise-based distortion filter."""
        return await _effect(
            ctx,
            project_id,
            "noise_distort",
            {
                "displacement": float(displacement),
                "size": size or [0.6, 0.6],
                "seed": int(seed),
                "smooth": int(smooth),
                "detail": int(detail),
            },
            name,
            index,
            amount,
            None,
        )

    @tool(server)
    async def add_duplicate(
        project_id: str,
        index_source: int = 0,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Add a duplicate filter (re-renders a layer chosen by index)."""
        return await _effect(
            ctx,
            project_id,
            "duplicate",
            {"index": int(index_source)},
            name,
            index,
            amount,
            blend_method,
        )
