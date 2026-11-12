"""Build an animated cut-out puppet inside the document that is already open.

This is deliberately *not* a document factory: the caller supplies a document
id (``"active"`` for the selected Synfig Studio window) and every operation is
applied to that canvas in place. Nothing is created, opened or replaced behind
the user's back.

Puppet structure (top of stack first)::

    <character>            group   - animated origin: sway + bob
      head                 group   - animated origin: follows the breath lift
        head_rotate        layer   - animated angle: tilt about the neck pivot
        head part          import
      torso                import  - animated tl/br: chest expands about the hips
      lower                import
      backing              import  - flat white plate behind white clothing
      shadow               import  - contact shadow on the ground

Synfig cannot animate a group's transformation matrix through the bridge, so
scale is expressed by animating the two corners of the import layer, and
rotation by a dedicated ``rotate`` layer whose origin is the neck.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.characters.sheet import (
    CutoutParts,
    load_manifest,
    prepare_background,
    render_shadow,
)

__all__ = ["CutoutIdleSpec", "IdleMotion", "build_cutout_idle"]


class IdleMotion(BaseModel):
    """Tuning for the looping idle cycle."""

    enabled: bool = Field(default=True, description="Animate the idle cycle at all.")
    breath_scale_y: float = Field(default=0.018, description="Chest rise as a fraction.")
    breath_scale_x: float = Field(default=0.006, description="Chest widening as a fraction.")
    sway_px: float = Field(default=3.0, description="Side-to-side drift in output pixels.")
    bob_px: float = Field(default=1.5, description="Vertical bob in output pixels.")
    head_tilt_deg: float = Field(default=2.2, description="Peak head tilt in degrees.")


class CutoutIdleSpec(BaseModel):
    """Everything needed to place and animate a puppet in the open document."""

    manifest_path: str = Field(description="Manifest written by sheet extraction.")
    doc_id: str = Field(
        default="active",
        description="Target document. 'active' means the currently selected Studio window.",
    )
    character_id: str = Field(default="character", description="Name for the puppet group.")
    height_ratio: float = Field(default=0.68, description="Puppet height as a fraction of the canvas.")
    foot_ratio: float = Field(default=0.90, description="Ground contact line as a fraction of height.")
    center_ratio: float = Field(default=0.42, description="Horizontal centre as a fraction of width.")
    pixels_per_unit: float | None = Field(
        default=None,
        description="Canvas units per pixel. Auto-calibrated when omitted.",
    )
    shadow: bool = Field(default=True, description="Include the soft contact shadow.")
    render_preview: bool = Field(default=True, description="Render one preview frame at the end.")
    motion: IdleMotion = Field(default_factory=IdleMotion)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _vec(px: float, py: float, width: int, height: int, ppu: float) -> dict[str, Any]:
    return {
        "type": "vector",
        "x": round((px - width / 2) / ppu, 4),
        "y": round((height / 2 - py) / ppu, 4),
    }


def _angle(degrees: float) -> dict[str, Any]:
    return {"type": "angle", "degrees": round(degrees, 3)}


def _layer_id(res: dict[str, Any]) -> str:
    lid = res.get("layer_id")
    if isinstance(lid, str) and lid:
        return lid
    created = res.get("created") or (res.get("diff") or {}).get("created") or []
    if created:
        return str(created[0])
    raise RuntimeError(f"backend did not return a layer id: {res}")


async def _resolve_doc(backend: BackendBase, doc_id: str) -> str:
    """Map 'active' onto the selected Studio window, or the first doc otherwise."""
    if doc_id not in {"", "active"}:
        return doc_id
    docs = await backend.doc_list()
    if not docs:
        raise ValueError("no document is open; open a project in Synfig Studio first")
    if backend.name == "live":
        return "active"  # the bridge resolves this to Studio's selected instance
    return docs[0].id


async def _calibrate_ppu(backend: BackendBase, doc_id: str, width: int) -> float:
    """Measure the canvas scale by rendering a known-size probe rectangle.

    Synfig's canvas unit scale depends on how the document was created, and the
    bridge exposes no view-box query, so guessing silently mis-scales the rig.
    One cheap render removes the guess.
    """
    probe_w = 320
    tmp = Path(str(Path.home() / ".synfig" / "workspace")) / "_mcp_calib_probe.png"
    layer: dict[str, Any] | None = None
    try:
        layer = await backend.layer_add(
            doc_id=doc_id,
            layer_type="rectangle",
            params={
                "point1": {"type": "vector", "x": -1.0, "y": 1.0},
                "point2": {"type": "vector", "x": 1.0, "y": -1.0},
                "color": {"type": "color", "r": 1.0, "g": 0.0, "b": 1.0, "a": 1.0},
            },
        )
        tmp.parent.mkdir(parents=True, exist_ok=True)
        await backend.render_frame(
            doc_id=doc_id, output_path=str(tmp), time=0.0, width=probe_w, target="png"
        )
        import numpy as np
        from PIL import Image

        arr = np.asarray(Image.open(tmp).convert("RGB")).astype(int)
        mask = (arr[:, :, 0] > 200) & (arr[:, :, 1] < 80) & (arr[:, :, 2] > 200)
        ys, xs = np.where(mask)
        if len(xs) < 8:
            raise ValueError("probe rectangle not visible in the render")
        span_px = float(xs.max() - xs.min() + 1)
        # the probe spanned 2 units; scale from probe width to full canvas width
        return span_px / 2.0 * (width / probe_w)
    except Exception:
        return width / 8.0  # Synfig's 8-unit-wide default canvas
    finally:
        if layer is not None:
            with _suppress():
                await backend.layer_remove(doc_id=doc_id, layer_id=_layer_id(layer))
        tmp.unlink(missing_ok=True)


class _suppress:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> bool:
        return True


async def _set_rect(
    backend: BackendBase, doc_id: str, layer_id: str, rect: tuple[float, float, float, float],
    width: int, height: int, ppu: float,
) -> None:
    x0, y0, x1, y1 = rect
    await backend.param_set(doc_id=doc_id, layer_id=layer_id, param_name="tl",
                            value=_vec(x0, y0, width, height, ppu))
    await backend.param_set(doc_id=doc_id, layer_id=layer_id, param_name="br",
                            value=_vec(x1, y1, width, height, ppu))


async def _waypoints(
    backend: BackendBase, doc_id: str, layer_id: str, param: str,
    points: list[tuple[float, dict[str, Any]]],
) -> None:
    for time, value in points:
        await backend.anim_waypoint_set(
            doc_id=doc_id, layer_id=layer_id, param_name=param, time=time,
            value=value, interpolation_in="clamped", interpolation_out="clamped",
        )


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------
async def build_cutout_idle(backend: BackendBase, spec: CutoutIdleSpec) -> dict[str, Any]:
    """Place and animate a cut-out puppet in an already-open document."""
    parts: CutoutParts = load_manifest(spec.manifest_path)
    doc_id = await _resolve_doc(backend, spec.doc_id)

    info = await backend.doc_info(doc_id)
    if info is None:
        raise ValueError(f"document '{doc_id}' is not open")
    width, height = int(info.width), int(info.height)
    start, end = float(info.start_time), float(info.end_time)
    span = max(1e-3, end - start)

    ppu = float(spec.pixels_per_unit or await _calibrate_ppu(backend, doc_id, width))

    # --- geometry ----------------------------------------------------------
    scale = (spec.height_ratio * height) / parts.figure_h
    fig_w = parts.figure_w * scale
    char_left = spec.center_ratio * width - fig_w / 2
    char_top = spec.foot_ratio * height - parts.figure_h * scale

    def part_rect(p: Any, pad: float = 0.0) -> tuple[float, float, float, float]:
        x = char_left + p.x * scale
        y = char_top + p.y * scale
        return (x - pad, y - pad, x + p.w * scale + pad, y + p.h * scale + pad)

    by_name = {p.name: p for p in parts.parts}
    layers: dict[str, str] = {}
    warnings: list[str] = []
    if "backing" not in by_name:
        warnings.append("manifest has no 'backing' part; white clothing will read as transparent")
    head = by_name.get("head")
    torso = by_name.get("torso")
    lower = by_name.get("lower")
    if head is None or torso is None:
        raise ValueError("manifest needs at least 'head' and 'torso' parts")

    out_dir = Path(parts.manifest_path).expanduser().parent

    # --- background --------------------------------------------------------
    bg_layer: str | None = None
    if parts.background_path:
        bg_path = prepare_background(parts.background_path, out_dir / f"background_{width}x{height}.jpg",
                                     (width, height))
        bg_layer = _layer_id(await backend.import_asset(doc_id=doc_id, file_path=str(bg_path)))
        await _set_rect(backend, doc_id, bg_layer, (0.0, 0.0, float(width), float(height)),
                        width, height, ppu)

    # --- shadow ------------------------------------------------------------
    shadow_layer: str | None = None
    if spec.shadow:
        shadow_px = max(120.0, fig_w * 0.75)
        shadow_path = render_shadow(out_dir / "parts" / "shadow.png",
                                    width=360, height=104)
        shadow_layer = _layer_id(
            await backend.import_asset(doc_id=doc_id, file_path=str(shadow_path))
        )
        cx = spec.center_ratio * width
        cy = spec.foot_ratio * height
        await _set_rect(
            backend, doc_id, shadow_layer,
            (cx - shadow_px / 2, cy - shadow_px * 0.16, cx + shadow_px / 2, cy + shadow_px * 0.16),
            width, height, ppu,
        )

    # --- parts (imported bottom-up so the stack reads top-down) ------------
    if "backing" in by_name:
        lid = _layer_id(await backend.import_asset(doc_id=doc_id, file_path=by_name["backing"].file))
        await _set_rect(backend, doc_id, lid, part_rect(by_name["backing"]), width, height, ppu)
        layers["backing"] = lid

    for name in ("lower", "torso"):
        if name not in by_name:
            continue
        lid = _layer_id(await backend.import_asset(doc_id=doc_id, file_path=by_name[name].file))
        await _set_rect(backend, doc_id, lid, part_rect(by_name[name]), width, height, ppu)
        layers[name] = lid

    if lower is None:
        warnings.append("manifest has no 'lower' part; legs will not be drawn")

    head_layer = _layer_id(await backend.import_asset(doc_id=doc_id, file_path=head.file))
    await _set_rect(backend, doc_id, head_layer, part_rect(head), width, height, ppu)

    # --- head pivot: rotate layer grouped above the head --------------------
    rot = await backend.layer_add(doc_id=doc_id, layer_type="rotate")
    rot_layer = _layer_id(rot)
    neck_px = (char_left + parts.pivots.get("neck", (parts.figure_w // 2, 0))[0] * scale,
               char_top + parts.pivots.get("neck", (0, 0))[1] * scale)
    await backend.param_set(doc_id=doc_id, layer_id=rot_layer, param_name="origin",
                            value=_vec(neck_px[0], neck_px[1], width, height, ppu))

    head_group = _layer_id(
        await backend.layer_group(
            doc_id=doc_id, layer_ids=[rot_layer, head_layer], group_name=f"{spec.character_id}_head"
        )
    )

    # --- character root ----------------------------------------------------
    order = [head_group]
    if "torso" in layers:
        order.append(layers["torso"])
    if "lower" in layers:
        order.append(layers["lower"])
    if "backing" in layers:
        order.append(layers["backing"])
    if shadow_layer:
        order.append(shadow_layer)
    root = _layer_id(
        await backend.layer_group(doc_id=doc_id, layer_ids=order, group_name=spec.character_id)
    )

    # --- animation ---------------------------------------------------------
    timeline: list[float] = []
    if spec.motion.enabled:
        m = spec.motion
        fracs = (0.0, 0.25, 0.5, 0.75, 1.0)
        timeline = [start + f * span for f in fracs]

        hip_px_y = char_top + parts.pivots.get("hip", (0, parts.figure_h // 2))[1] * scale
        torso_rect = part_rect(torso)

        root_pts: list[tuple[float, dict[str, Any]]] = []
        torso_tl: list[tuple[float, dict[str, Any]]] = []
        torso_br: list[tuple[float, dict[str, Any]]] = []
        head_pts: list[tuple[float, dict[str, Any]]] = []
        tilt_pts: list[tuple[float, dict[str, Any]]] = []

        tilt_curve = (0.0, -1.0, 0.25, 0.6, 0.0)  # loops back to zero
        for i, (time, f) in enumerate(zip(timeline, fracs, strict=True)):
            # sway: one full cycle; bob: two, phase-locked to the breath
            sway = m.sway_px * (1.0 if f == 0.25 else -1.0 if f == 0.75 else 0.0)
            bob = -m.bob_px if f in (0.25, 0.75) else 0.0
            root_pts.append((time, {"type": "vector",
                                    "x": round(sway / ppu, 4), "y": round(-bob / ppu, 4)}))

            peak = f in (0.25, 0.75)
            ky = 1.0 + (m.breath_scale_y if peak else 0.0)
            kx = 1.0 + (m.breath_scale_x if peak else 0.0)

            cx = (torso_rect[0] + torso_rect[2]) / 2
            torso_tl.append((time, _vec(cx + (torso_rect[0] - cx) * kx,
                                        hip_px_y + (torso_rect[1] - hip_px_y) * ky,
                                        width, height, ppu)))
            torso_br.append((time, _vec(cx + (torso_rect[2] - cx) * kx,
                                        hip_px_y + (torso_rect[3] - hip_px_y) * ky,
                                        width, height, ppu)))

            lift = (neck_px[1] - hip_px_y) * (ky - 1.0)
            head_pts.append((time, {"type": "vector", "x": 0.0, "y": round(-lift / ppu, 4)}))
            tilt_pts.append((time, _angle(m.head_tilt_deg * tilt_curve[i])))

        await _waypoints(backend, doc_id, root, "origin", root_pts)
        await _waypoints(backend, doc_id, layers["torso"], "tl", torso_tl)
        await _waypoints(backend, doc_id, layers["torso"], "br", torso_br)
        await _waypoints(backend, doc_id, head_group, "origin", head_pts)
        await _waypoints(backend, doc_id, rot_layer, "amount", tilt_pts)

    # --- preview -----------------------------------------------------------
    preview: str | None = None
    if spec.render_preview:
        preview = str(out_dir / "preview.png")
        mid = start + span * 0.25
        await backend.render_frame(doc_id=doc_id, output_path=preview, time=mid, target="png")

    return {
        "doc_id": doc_id,
        "character": spec.character_id,
        "figure": {"width": parts.figure_w, "height": parts.figure_h, "scale": round(scale, 4)},
        "canvas": {"width": width, "height": height, "fps": info.fps,
                   "start_time": start, "end_time": end},
        "pixels_per_unit": round(ppu, 4),
        "layers": {"root": root, "head_group": head_group, "head_rotate": rot_layer,
                   **{f"{k}_layer": v for k, v in layers.items()},
                   "shadow": shadow_layer, "background": bg_layer},
        "animated": bool(timeline),
        "keyframe_times": [round(t, 4) for t in timeline],
        "preview": preview,
        "warnings": warnings,
    }
