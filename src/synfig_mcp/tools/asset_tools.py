# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Asset tools: import/copy assets, embed images, canvas inlining, SVG import."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from lxml import etree

from ..document import layers as lay
from ..errors import ParameterError
from ..security.limits import Limits
from ..security.paths import (
    IMAGE_EXTENSIONS,
    check_file_size,
    resolve_workspace_path,
    sanitize_text,
)
from .common import AppContext, json_dumps, tool
from .layer_shared import (
    default_version,
    ensure_amount,
    ensure_blend,
    ensure_z_depth,
    set_param,
)

ASSET_SUBDIR = "assets"


def _assets_dir(ctx: AppContext) -> Path:
    directory = ctx.settings.workspace / ASSET_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _unique_target(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem, suffix = Path(filename).stem, Path(filename).suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def register(server, ctx: AppContext) -> None:  # type: ignore[no-untyped-def]
    @tool(server)
    async def import_asset(
        path: str,
        name: str | None = None,
    ) -> str:
        """Copy an asset (image/sound/etc.) into the workspace assets directory.

        The source must be inside the configured workspace. Returns the new
        path; use add_image/embed_image to place it in a project. If the file
        is already inside the assets directory it is returned as-is.
        """
        resolved = resolve_workspace_path(
            path,
            ctx.settings.workspace,
            must_exist=True,
            allowed_extensions=IMAGE_EXTENSIONS | {".ogg", ".wav", ".mp3", ".flac", ".ttf", ".otf"},
            purpose="asset",
        )
        check_file_size(resolved, ctx.settings.max_file_bytes, "asset")
        assets_dir = _assets_dir(ctx)
        if resolved.parent == assets_dir:
            return json_dumps(
                {"path": str(resolved), "copied": False, "size_bytes": resolved.stat().st_size}
            )
        filename = sanitize_text(name or resolved.name, max_length=128) or resolved.name
        target = _unique_target(assets_dir, Path(filename).name)
        shutil.copy2(resolved, target)
        return json_dumps(
            {
                "path": str(target),
                "copied": True,
                "source": str(resolved),
                "size_bytes": target.stat().st_size,
            }
        )

    @tool(server)
    async def list_assets() -> str:
        """List files in the workspace assets directory."""
        assets_dir = _assets_dir(ctx)
        items: list[dict[str, Any]] = []
        for item in sorted(assets_dir.iterdir()):
            if item.is_file():
                try:
                    stat = item.stat()
                    items.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "size_bytes": stat.st_size,
                            "suffix": item.suffix.lower(),
                        }
                    )
                except OSError:
                    continue
        return json_dumps({"assets_dir": str(assets_dir), "count": len(items), "assets": items})

    @tool(server)
    async def embed_image(
        project_id: str,
        image_path: str,
        name: str | None = None,
        copy_to_assets: bool = True,
        tl: list[float] | None = None,
        br: list[float] | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Embed an image into the project as an import layer.

        Copies the image into the workspace assets directory (unless already
        there) and adds an 'import' layer referencing the copy. tl/br set the
        top-left/bottom-right corners in canvas units (default square at origin).
        """
        resolved = resolve_workspace_path(
            image_path,
            ctx.settings.workspace,
            must_exist=True,
            allowed_extensions=IMAGE_EXTENSIONS,
            purpose="image",
        )
        check_file_size(resolved, ctx.settings.max_file_bytes, "image")
        if copy_to_assets:
            assets_dir = _assets_dir(ctx)
            if resolved.parent == assets_dir:
                embedded = resolved
            else:
                embedded = _unique_target(assets_dir, resolved.name)
                shutil.copy2(resolved, embedded)
        else:
            embedded = resolved
        params: dict[str, Any] = {"filename": str(embedded)}
        params["tl"] = tl if tl is not None else [-0.5, 0.5]
        params["br"] = br if br is not None else [0.5, -0.5]
        session = await ctx.registry.get(project_id)
        fps = float(session.root.get("fps", "24") or 24)
        async with session.lock:
            limits = Limits(session.settings)
            limits.check_layer_count(len(session.layers()) + 1)
            session.record_history()
            layer = etree.Element(
                "layer",
                attrib={"type": "import", "active": "true", "version": default_version("import")},
            )
            ensure_z_depth(layer)
            ensure_amount(layer)
            ensure_blend(layer)
            layer.set("desc", sanitize_text(name or embedded.name, max_length=128))
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
                from ..document.canvas import parse_blend_method

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
                "embedded": str(embedded),
                "layer": lay.layer_summary(layer),
            }
        )

    @tool(server)
    async def set_canvas_inline(project_id: str, canvas_id: str) -> str:
        """Inline all references to a defs canvas (use=":id") into the layers.

        Every ``<param name="canvas" use="canvas_id"/>`` is replaced with a
        deep copy of the defs canvas inline. The defs entry is kept (it may
        still be referenced elsewhere); remove it manually with a text edit if
        nothing references it afterwards.
        """
        session = await ctx.registry.get(project_id)
        root = session.root
        defs = root.find("defs")
        target = None
        if defs is not None:
            for child in defs:
                if (
                    isinstance(child.tag, str)
                    and child.tag == "canvas"
                    and child.get("id") == canvas_id
                ):
                    target = child
                    break
        if target is None:
            raise ParameterError(f"No defs canvas named {canvas_id!r}.")
        import copy

        replaced = 0
        async with session.lock:
            session.record_history()
            for param in root.iter("param"):
                if param.get("name") == "canvas" and param.get("use") == canvas_id:
                    for child in list(param):
                        param.remove(child)
                    if "use" in param.attrib:
                        del param.attrib["use"]
                    clone = copy.deepcopy(target)
                    if "id" in clone.attrib:
                        del clone.attrib["id"]
                    param.append(clone)
                    replaced += 1
            if replaced:
                session.touch()
        await ctx.after_mutation(session)
        return json_dumps({"project_id": project_id, "canvas_id": canvas_id, "inlined": replaced})

    @tool(server)
    async def import_svg(
        project_id: str,
        svg_path: str,
        name: str | None = None,
        index: int | None = None,
        amount: float | None = None,
        blend_method: str | int | None = None,
    ) -> str:
        """Import an SVG as a renderable vector image layer.

        The SVG is referenced (not inlined) by an 'import' layer using
        Synfig's built-in SVG importer; it renders at full vector quality
        but is not editable as Synfig layers. Convert to editable layers in
        Studio if you need that.
        """
        resolved = resolve_workspace_path(
            svg_path,
            ctx.settings.workspace,
            must_exist=True,
            allowed_extensions={".svg"},
            purpose="svg",
        )
        check_file_size(resolved, ctx.settings.max_file_bytes, "svg")
        session = await ctx.registry.get(project_id)
        fps = float(session.root.get("fps", "24") or 24)
        async with session.lock:
            limits = Limits(session.settings)
            limits.check_layer_count(len(session.layers()) + 1)
            session.record_history()
            layer = etree.Element(
                "layer",
                attrib={"type": "import", "active": "true", "version": default_version("import")},
            )
            ensure_z_depth(layer)
            ensure_amount(layer)
            ensure_blend(layer)
            layer.set("desc", sanitize_text(name or resolved.name, max_length=128))
            set_param(
                layer,
                "filename",
                str(resolved),
                fps=fps,
                unit_px=ctx.settings.unit_px,
                unit_system=ctx.settings.unit_system,
            )
            if amount is not None:
                lay.set_or_create_param(layer, "amount", float(amount), tag="real")
            if blend_method is not None:
                from ..document.canvas import parse_blend_method

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
                "svg": str(resolved),
                "layer": lay.layer_summary(layer),
            }
        )
