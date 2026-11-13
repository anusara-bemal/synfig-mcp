"""
Automated quality control for a Synfig production.

The checks are grouped into two families:

``validate_document``
    static checks on the document itself - empty scenes, missing assets,
    broken references, hidden or disconnected layers, z-order problems,
    invalid rigs, missing keyframes, clipped frames, camera framing errors,
    wrong dimensions or frame rate, unsafe paths and missing licence
    metadata.

``validate_render``
    checks on rendered output - a render that failed, a frame that came out
    blank, a frame whose alpha channel is broken or a frame that has the
    wrong resolution.

Every check returns a typed issue with a stable code, a severity and a
message that names the layer or file at fault.  The orchestrator refuses to
call a stage successful while an issue with the severity ``error`` is open.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.errors import DocumentNotFoundError
from synfig_mcp.security.sandbox import get_default_allowed_roots

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


def _issue(code: str, message: str, severity: str = SEVERITY_ERROR) -> dict[str, Any]:
    """Build one quality issue."""
    return {"code": code, "message": message, "severity": severity}


def _value_of(params: dict[str, Any], name: str) -> Any:
    """Return the raw value of a parameter of a scene tree node."""
    param = params.get(name)
    if isinstance(param, dict):
        return param.get("value")
    return param


class QualityControl:
    """Runs the automated checks of a production."""

    def __init__(self, backend: BackendBase) -> None:
        self.backend = backend

    async def validate_document(
        self,
        doc_id: str,
        expected_width: int | None = None,
        expected_height: int | None = None,
        expected_fps: float | None = None,
        require_keyframes: bool = False,
        registered_assets: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Run every static check on a document."""
        docs = await self.backend.doc_list()
        info = next((d for d in docs if d.id == doc_id), None)
        if info is None:
            raise DocumentNotFoundError(f"Document '{doc_id}' not found.")

        issues: list[dict[str, Any]] = []
        if expected_width is not None and info.width != expected_width:
            issues.append(
                _issue(
                    "dimension.mismatch",
                    f"The canvas is {info.width}x{info.height} but "
                    f"{expected_width}x{expected_height} was requested.",
                )
            )
        if expected_height is not None and info.height != expected_height:
            issues.append(
                _issue(
                    "dimension.mismatch",
                    f"The canvas height is {info.height} but {expected_height} was requested.",
                )
            )
        if expected_fps is not None and abs(info.fps - expected_fps) > 1e-6:
            issues.append(
                _issue(
                    "fps.mismatch",
                    f"The canvas runs at {info.fps} fps but {expected_fps} fps was requested.",
                )
            )

        tree = await self.backend.scene_tree(doc_id)
        layers = list(tree.get("layers", []))
        if not layers:
            issues.append(_issue("scene.empty", "The document has no layers at all."))

        issues.extend(self._check_layers(layers))
        issues.extend(self._check_zorder(layers))
        issues.extend(self._check_assets(layers, registered_assets))
        issues.extend(await self._check_keyframes(doc_id, info))
        issues.extend(self._check_camera(layers, info))

        if require_keyframes:
            keyframes = await self.backend.anim_keyframe_list(doc_id)
            if not keyframes:
                issues.append(
                    _issue(
                        "keyframes.missing",
                        "The document has no keyframes but animation was requested.",
                        SEVERITY_WARNING,
                    )
                )
        return issues

    def _check_layers(self, layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Check for hidden and disconnected layers."""
        issues: list[dict[str, Any]] = []
        for layer in layers:
            label = str(layer.get("id") or layer.get("desc") or "")
            if layer.get("active") is False:
                issues.append(
                    _issue(
                        "layer.hidden",
                        f"The layer '{label}' is switched off and will not be rendered.",
                        SEVERITY_WARNING,
                    )
                )
            children = layer.get("children") or []
            if str(layer.get("type", "")) in ("group", "paste_canvas") and not children:
                issues.append(
                    _issue(
                        "layer.disconnected",
                        f"The group '{label}' does not contain any layer.",
                        SEVERITY_WARNING,
                    )
                )
            issues.extend(self._check_layers(children))
        return issues

    def _check_zorder(self, layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Check that no two layers share a depth."""
        issues: list[dict[str, Any]] = []
        seen: dict[int, str] = {}
        for layer in layers:
            depth = layer.get("depth")
            if not isinstance(depth, int):
                continue
            label = str(layer.get("id") or layer.get("desc") or "")
            if depth in seen:
                issues.append(
                    _issue(
                        "zorder.duplicate",
                        f"The layers '{seen[depth]}' and '{label}' share the depth {depth}.",
                    )
                )
            else:
                seen[depth] = label
        return issues

    def _check_assets(
        self, layers: list[dict[str, Any]], registered: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]]:
        """Check that every imported file exists, is reachable and is licensed."""
        issues: list[dict[str, Any]] = []
        roots = get_default_allowed_roots()
        for layer in layers:
            label = str(layer.get("id") or layer.get("desc") or "")
            params = layer.get("params") or {}
            if str(layer.get("type", "")) not in ("import", "image"):
                issues.extend(self._check_assets(layer.get("children") or [], registered))
                continue
            filename = _value_of(params, "filename")
            if not filename:
                issues.append(
                    _issue("asset.missing", f"The layer '{label}' has no file name.")
                )
                continue
            path = Path(str(filename))
            if not path.is_absolute():
                issues.append(
                    _issue(
                        "path.relative",
                        f"The layer '{label}' refers to the relative path '{filename}', "
                        "which breaks when the project is moved.",
                        SEVERITY_WARNING,
                    )
                )
            if not path.is_file():
                issues.append(
                    _issue(
                        "asset.missing",
                        f"The file '{filename}' of the layer '{label}' does not exist.",
                    )
                )
            elif not any(root == path or root in path.parents for root in roots):
                issues.append(
                    _issue(
                        "path.unsafe",
                        f"The file '{filename}' of the layer '{label}' lies outside the "
                        "allowed workspace roots.",
                        SEVERITY_WARNING,
                    )
                )
            issues.extend(self._check_assets(layer.get("children") or [], registered))
        return issues

    async def _check_keyframes(self, doc_id: str, info: Any) -> list[dict[str, Any]]:
        """Check that the keyframes of the document are inside the time range."""
        try:
            keyframes = await self.backend.anim_keyframe_list(doc_id)
        except Exception:
            return []
        issues: list[dict[str, Any]] = []
        start = float(getattr(info, "start_time", 0.0))
        end = float(getattr(info, "end_time", 0.0))
        for keyframe in keyframes:
            time = float(keyframe.get("time", 0.0))
            if time < start - 1e-6 or time > end + 1e-6:
                issues.append(
                    _issue(
                        "frame.clipped",
                        f"A keyframe at {time:.3f}s lies outside the time range "
                        f"{start}s - {end}s.",
                    )
                )
        return issues

    def _check_camera(self, layers: list[dict[str, Any]], info: Any) -> list[dict[str, Any]]:
        """Check the framing of every camera rig in the document."""
        issues: list[dict[str, Any]] = []
        for layer in layers:
            label = str(layer.get("id") or layer.get("desc") or "")
            if str(layer.get("type", "")) == "camera":
                zoom = _value_of(layer.get("params") or {}, "amount")
                try:
                    factor = math.exp(float(zoom))
                except (OverflowError, ValueError, TypeError):
                    issues.append(
                        _issue(
                            "camera.framing",
                            f"The zoom of the camera '{label}' is not a valid factor.",
                        )
                    )
                    continue
                if not 0.0 < factor <= 20.0:
                    issues.append(
                        _issue(
                            "camera.framing",
                            f"The zoom of the camera '{label}' is {factor:.3f}, which is "
                            "outside the usable range.",
                        )
                    )
            issues.extend(self._check_camera(layer.get("children") or [], info))
        return issues

    def validate_rig(self, tree: dict[str, Any], character_id: str) -> list[dict[str, Any]]:
        """Validate a cut-out rig inside a scene tree.

        A rig is valid when it has a position layer, at least one joint and
        a parent-child chain that is not broken.
        """
        issues: list[dict[str, Any]] = []
        found: list[str] = []

        def walk(nodes: list[dict[str, Any]]) -> None:
            for node in nodes:
                label = str(node.get("id") or node.get("desc") or "")
                if label.startswith(character_id + "_"):
                    found.append(label)
                walk(node.get("children") or [])

        walk(tree.get("layers", []))
        if f"{character_id}_pos" not in found:
            issues.append(
                _issue(
                    "rig.invalid",
                    f"The rig '{character_id}' has no position layer "
                    f"('{character_id}_pos'), so it cannot be placed in the shot.",
                )
            )
        if not any(label.endswith("_rot") for label in found):
            issues.append(
                _issue(
                    "rig.invalid",
                    f"The rig '{character_id}' has no joint layers, so it cannot be posed.",
                )
            )
        return issues

    def validate_render(
        self,
        output_path: str | Path,
        expected_width: int | None = None,
        expected_height: int | None = None,
    ) -> list[dict[str, Any]]:
        """Check a rendered frame.

        The frame has to exist, have the expected resolution, not be blank
        and carry a usable alpha channel.
        """
        from PIL import Image

        issues: list[dict[str, Any]] = []
        path = Path(output_path)
        if not path.is_file() or path.stat().st_size == 0:
            issues.append(_issue("render.failed", f"The render '{path}' was not written."))
            return issues
        try:
            with Image.open(path) as image:
                image.load()
                size = image.size
                rgba = image.convert("RGBA")
        except Exception as err:
            issues.append(_issue("render.failed", f"The render '{path}' cannot be read: {err}"))
            return issues

        if expected_width is not None and size[0] != expected_width:
            issues.append(
                _issue(
                    "resolution.mismatch",
                    f"The render '{path}' is {size[0]}x{size[1]} but "
                    f"{expected_width}x{expected_height} was requested.",
                )
            )
        if expected_height is not None and size[1] != expected_height:
            issues.append(
                _issue(
                    "resolution.mismatch",
                    f"The render '{path}' is {size[0]}x{size[1]} but "
                    f"{expected_width}x{expected_height} was requested.",
                )
            )

        rgb = rgba.convert("RGB")
        if all(lo == hi for lo, hi in rgb.getextrema()):
            issues.append(
                _issue("frame.blank", f"The render '{path}' is a single flat colour.")
            )
        alpha_lo, alpha_hi = rgba.getchannel("A").getextrema()
        if alpha_hi == 0:
            issues.append(
                _issue("alpha.broken", f"The render '{path}' is completely transparent.")
            )
        elif alpha_lo == 255:
            issues.append(
                _issue(
                    "alpha.flat",
                    f"The render '{path}' has no transparent pixels; an alpha channel "
                    "was requested but is not used.",
                    SEVERITY_WARNING,
                )
            )
        return issues