"""
One-call scene assembly: background, rigged characters, props, camera, audio.

``SceneAutoBuilder`` turns a compact scene description into a single
``scene_build`` spec.  Everything is validated before the document is touched,
so a bad file path or a misspelled motion costs no undo step, and the whole
scene arrives in one round trip to the backend.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from PIL import Image
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.characters.cutout import (
    IMAGE_EXTENSIONS,
    CanvasFrame,
    CompiledRig,
    CutoutCharacter,
    CutoutPart,
    MotionAction,
    attach_waypoints,
    compile_character,
    plan_actions,
    vector,
)
from synfig_mcp.characters.rigging import RiggingEngine, remember_rig
from synfig_mcp.errors import SynfigError
from synfig_mcp.errors import ValidationError as SpecError
from synfig_mcp.security.sandbox import validate_path

AUDIO_EXTENSIONS = {".wav", ".ogg", ".mp3", ".flac", ".au"}
DOCUMENT_EXTENSIONS = {".sif", ".sifz", ".sfg"}


class BackgroundSpec(BaseModel):
    """Backdrop of the scene: an image, a colour, or both."""

    file: str | None = Field(default=None, description="Background image.")
    color: str | None = Field(default=None, description="Fill colour as #rrggbb.")
    fit: Literal["cover", "contain", "stretch"] = Field(default="cover")


class PropSpec(BaseModel):
    """A single image placed in the scene; it can move like a character."""

    id: str
    file: str
    position: dict[str, float] | None = None
    height: float | None = Field(default=None, description="Height on canvas.")
    scale: float | None = Field(default=None, description="Canvas pixels per image pixel.")
    rotation: float = Field(default=0.0, description="Static rotation in degrees.")
    flip: bool = False
    z: float = 0.0
    actions: list[MotionAction] = Field(default_factory=list)


class CameraKey(BaseModel):
    """Camera state at a point in time."""

    time: float = 0.0
    zoom: float = Field(default=1.0, gt=0.0, description="1 = whole canvas, 2 = twice as close.")
    center: dict[str, float] | None = Field(
        default=None, description="Scene position at the middle of the frame."
    )


class AudioSpec(BaseModel):
    file: str
    delay: float = Field(default=0.0, description="Start offset in seconds.")
    volume: float = Field(default=1.0, ge=0.0)


class SceneAutoSpec(BaseModel):
    """Compact description of a whole shot."""

    doc_id: str | None = Field(default=None, description="Existing document; omit for a new one.")
    width: int = Field(default=1920, ge=16, le=8192)
    height: int = Field(default=1080, ge=16, le=8192)
    fps: float = Field(default=24.0, gt=0.0, le=240.0)
    duration: float = Field(default=5.0, gt=0.0, le=3600.0)
    coords: Literal["pixels", "units"] = Field(
        default="pixels",
        description="'pixels': x right / y down from the top-left corner. 'units': Synfig units.",
    )
    background: BackgroundSpec | None = None
    characters: list[CutoutCharacter] = Field(default_factory=list)
    props: list[PropSpec] = Field(default_factory=list)
    camera: list[CameraKey] = Field(default_factory=list)
    audio: AudioSpec | None = None
    save_path: str | None = Field(default=None, description="Write the document here (.sif/.sifz).")
    preview: bool = Field(default=True, description="Render a contact sheet of the result.")
    preview_frames: int = Field(default=4, ge=1, le=9)


def parse_color(text: str) -> dict[str, Any]:
    """Parse ``#rgb`` / ``#rrggbb`` / ``#rrggbbaa`` into a linear Synfig colour."""
    raw = text.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) not in (6, 8):
        raise SpecError(f"Colour '{text}' must look like #rrggbb.")
    try:
        channels = [int(raw[i : i + 2], 16) / 255.0 for i in range(0, len(raw), 2)]
    except ValueError as err:
        raise SpecError(f"Colour '{text}' must look like #rrggbb.") from err
    alpha = channels[3] if len(channels) == 4 else 1.0
    # Synfig stores colours linear; artwork colours are given in sRGB.
    red, green, blue = (round(math.pow(c, 2.2), 6) for c in channels[:3])
    return {"type": "color", "r": red, "g": green, "b": blue, "a": round(alpha, 6)}


class SceneAutoBuilder:
    """Compile and build a scene from a ``SceneAutoSpec``."""

    def __init__(self, backend: BackendBase) -> None:
        self.backend = backend
        self.rigging = RiggingEngine(backend)

    # -- compile -----------------------------------------------------------

    def _background_layers(self, bg: BackgroundSpec, frame: CanvasFrame) -> list[dict[str, Any]]:
        layers: list[dict[str, Any]] = []
        if bg.color:
            layers.append(
                {
                    "id": "Background_color",
                    "type": "solid_color",
                    "params": {"color": parse_color(bg.color)},
                }
            )
        if bg.file:
            path = validate_path(
                bg.file, allowed_extensions=IMAGE_EXTENSIONS, must_exist=True, user_intent=True
            )
            try:
                with Image.open(path) as img:
                    img_w, img_h = img.width, img.height
            except Exception as err:
                raise SpecError(f"Cannot read background image '{bg.file}': {err}") from err
            span_w, span_h = frame.right - frame.left, frame.top - frame.bottom
            if bg.fit == "stretch":
                half_w, half_h = span_w / 2, span_h / 2
            else:
                ratio_x, ratio_y = abs(span_w) / img_w, abs(span_h) / img_h
                ratio = max(ratio_x, ratio_y) if bg.fit == "cover" else min(ratio_x, ratio_y)
                half_w = math.copysign(img_w * ratio / 2, span_w)
                half_h = math.copysign(img_h * ratio / 2, span_h)
            mid_x, mid_y = (frame.left + frame.right) / 2, (frame.top + frame.bottom) / 2
            layers.append(
                {
                    "id": "Background",
                    "type": "import",
                    "params": {
                        "filename": {"type": "string", "value": str(path)},
                        "tl": vector(mid_x - half_w, mid_y + half_h),
                        "br": vector(mid_x + half_w, mid_y - half_h),
                    },
                }
            )
        return layers

    def _camera_layers(
        self, keys: list[CameraKey], frame: CanvasFrame
    ) -> tuple[list[dict[str, Any]], bool]:
        """Camera = a translate (pan) under a zoom, both above everything else."""
        if not keys:
            return [], False
        ordered = sorted(keys, key=lambda k: k.time)
        mid = ((frame.left + frame.right) / 2, (frame.top + frame.bottom) / 2)

        def pan(key: CameraKey) -> tuple[float, float]:
            if key.center is None:
                return (0.0, 0.0)
            x, y = frame.point(float(key.center.get("x", 0)), float(key.center.get("y", 0)))
            return (mid[0] - x, mid[1] - y)

        first = ordered[0]
        pan_layer: dict[str, Any] = {
            "id": "Camera_pan",
            "type": "translate",
            "params": {"origin": vector(*pan(first))},
        }
        zoom_layer: dict[str, Any] = {
            "id": "Camera_zoom",
            "type": "zoom",
            "params": {
                "amount": {"type": "real", "value": round(math.log(first.zoom), 6)},
                "center": vector(*mid),
            },
        }
        animated = len(ordered) > 1
        if animated:
            pan_layer["waypoints"] = [
                {
                    "param": "origin",
                    "time": k.time,
                    "value": vector(*pan(k)),
                    "interpolation": "clamped",
                }
                for k in ordered
            ]
            zoom_layer["waypoints"] = [
                {
                    "param": "amount",
                    "time": k.time,
                    "value": {"type": "real", "value": round(math.log(k.zoom), 6)},
                    "interpolation": "clamped",
                }
                for k in ordered
            ]
        return [pan_layer, zoom_layer], animated

    def compile(
        self, spec: SceneAutoSpec, frame: CanvasFrame
    ) -> tuple[dict[str, Any], list[CompiledRig], dict[str, Any]]:
        """Compile the scene into a scene_build spec, the rigs and a report."""
        layers: list[dict[str, Any]] = []
        groups: list[dict[str, Any]] = []
        warnings: list[str] = []
        report: dict[str, Any] = {"characters": [], "props": [], "warnings": warnings}

        if spec.background is not None:
            layers += self._background_layers(spec.background, frame)

        # Characters without a position are spread across the floor.
        unplaced = [c for c in spec.characters if c.position is None]
        actors: list[tuple[float, int, CutoutCharacter, bool]] = []
        for order, character in enumerate(spec.characters):
            if character.position is None and frame.coords == "pixels":
                slot = unplaced.index(character) + 1
                character = character.model_copy(
                    update={
                        "position": {
                            "x": frame.width * slot / (len(unplaced) + 1),
                            "y": frame.height * 0.88,
                        }
                    }
                )
            actors.append((character.z, order, character, False))
        for order, prop in enumerate(spec.props, start=len(spec.characters)):
            actors.append(
                (
                    prop.z,
                    order,
                    CutoutCharacter(
                        id=prop.id,
                        parts=[
                            CutoutPart(
                                name="art",
                                file=prop.file,
                                pivot={"fx": 0.5, "fy": 0.5},
                                rest_angle=prop.rotation,
                            )
                        ],
                        position=prop.position
                        or (
                            {"x": frame.width / 2, "y": frame.height / 2}
                            if frame.coords == "pixels"
                            else {"x": 0.0, "y": 0.0}
                        ),
                        anchor="center",
                        height=prop.height,
                        scale=prop.scale,
                        flip=prop.flip,
                        z=prop.z,
                        actions=prop.actions,
                    ),
                    True,
                )
            )

        ids = [actor[2].id for actor in actors]
        repeated = sorted({i for i in ids if ids.count(i) > 1})
        if repeated:
            raise SpecError(f"Character and prop ids must be unique, repeated: {repeated}.")

        rigs: list[CompiledRig] = []
        last_key = 0.0
        for _z, _order, character, is_prop in sorted(actors, key=lambda a: (a[0], a[1])):
            rig = compile_character(character, frame)
            plan = plan_actions(rig, character.actions, frame, spec.duration)
            attach_waypoints(rig, plan)
            last_key = max(last_key, plan.end_time)
            layers += rig.layers
            groups += rig.groups
            rigs.append(rig)
            entry = {
                "id": rig.character_id,
                "root_group": rig.root_group,
                "parts": len(rig.parts),
                "waypoints": plan.count(),
                "motions": plan.applied,
            }
            if not is_prop:
                entry["roles"] = sorted(rig.by_role())
                if plan.skipped_roles:
                    entry["skipped_roles"] = plan.skipped_roles
                    warnings.append(
                        f"'{rig.character_id}' has no part for {plan.skipped_roles}; those joints "
                        "of the motion were left out."
                    )
            warnings += [f"{rig.character_id}: {note}" for note in rig.notes]
            report["props" if is_prop else "characters"].append(entry)

        if spec.audio is not None:
            audio = validate_path(
                spec.audio.file,
                allowed_extensions=AUDIO_EXTENSIONS,
                must_exist=True,
                user_intent=True,
            )
            layers.append(
                {
                    "id": "Audio",
                    "type": "sound",
                    "params": {
                        "filename": {"type": "string", "value": str(audio)},
                        "delay": {"type": "time", "seconds": spec.audio.delay},
                        "volume": {"type": "real", "value": spec.audio.volume},
                    },
                }
            )

        camera_layers, camera_animated = self._camera_layers(spec.camera, frame)
        layers += camera_layers
        if spec.camera:
            last_key = max(last_key, max(k.time for k in spec.camera))
        report["camera"] = {"keys": len(spec.camera), "animated": camera_animated}

        if last_key > spec.duration + 1e-6:
            warnings.append(
                f"Animation runs until {last_key:.2f}s but the scene lasts {spec.duration:.2f}s; "
                "raise 'duration' to see all of it."
            )
        if not layers:
            raise SpecError("The scene is empty: give a background, characters or props.")

        ids = [layer["id"] for layer in layers] + [group["id"] for group in groups]
        clash = sorted({i for i in ids if ids.count(i) > 1})
        if clash:
            raise SpecError(f"Layer ids collide: {clash}. Rename the characters or props.")

        build = {"layers": layers, "groups": groups}
        report["layers"] = len(layers)
        report["groups"] = len(groups)
        return build, rigs, report

    # -- build -------------------------------------------------------------

    async def build(self, spec_data: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
        """Validate, compile and build the scene; optionally save and preview it."""
        try:
            spec = SceneAutoSpec.model_validate(spec_data)
        except PydanticValidationError as err:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in err.errors()[:8]
            )
            raise SpecError(f"Invalid scene spec - {problems}") from err

        save_path = None
        if spec.save_path:
            save_path = validate_path(
                spec.save_path, allowed_extensions=DOCUMENT_EXTENSIONS, user_intent=True
            )

        created_doc = False
        if spec.doc_id is not None:
            doc_id = spec.doc_id
            frame = await self.rigging.canvas_frame(doc_id, coords=spec.coords)
        elif dry_run:
            # Nothing may be created on a dry run: use the frame a new document would get.
            doc_id = "(new document)"
            aspect = spec.width / spec.height
            frame = CanvasFrame(
                spec.width, spec.height, -4.0 * aspect, 4.0, 4.0 * aspect, -4.0, spec.coords
            )
        else:
            docs = await self.backend.doc_list()
            if docs:
                doc_id = docs[0].id
                frame = await self.rigging.canvas_frame(doc_id, coords=spec.coords)
            else:
                info = await self.backend.doc_new(
                    width=spec.width, height=spec.height, fps=spec.fps
                )
                doc_id = info.id
                created_doc = True
                frame = await self.rigging.canvas_frame(doc_id, coords=spec.coords)

        try:
            build, rigs, report = self.compile(spec, frame)
        except Exception:
            if created_doc:
                await self.backend.doc_close(doc_id, force=True)
            raise

        result: dict[str, Any] = {
            "success": True,
            "doc_id": doc_id,
            "dry_run": dry_run,
            "canvas": {"width": frame.width, "height": frame.height, "fps": spec.fps},
            "duration": spec.duration,
            **report,
        }
        if dry_run:
            result["plan"] = {
                "layers": [f"{layer['type']}:{layer['id']}" for layer in build["layers"]],
                "groups": [group["id"] for group in build["groups"]],
            }
            return result

        build["doc_id"] = doc_id
        try:
            built = await self.backend.scene_build(spec=build, dry_run=False)
            if built.get("success") is False:
                raise SynfigError(str(built.get("error", "scene_build rejected the scene.")))
        except Exception:
            if created_doc:
                await self.backend.doc_close(doc_id, force=True)
            raise
        for rig in rigs:
            remember_rig(doc_id, rig)
        await self.backend.doc_set_time_range(doc_id=doc_id, start_time=0.0, end_time=spec.duration)
        result["diff"] = built.get("diff", {})

        if save_path is not None:
            result["saved_to"] = await self.backend.doc_save(
                doc_id=doc_id, file_path=str(save_path)
            )

        if spec.preview:
            from synfig_mcp.review.service import ReviewService

            try:
                review = await ReviewService(backend=self.backend).review_sequence(
                    doc_id=doc_id,
                    start_time=0.0,
                    end_time=spec.duration,
                    frame_count=spec.preview_frames,
                    width=320,
                    height=max(16, round(320 * frame.height / frame.width)),
                )
                result["preview"] = review
            except Exception as err:  # the scene is built; a missing renderer must not undo it
                result["preview_error"] = (
                    f"The scene was built, but no preview could be rendered: {err}"
                )

        result["next_steps"] = [
            "review_sequence / review_frame to inspect the animation",
            "character_motion_apply or character_pose_apply to refine a character",
            "render_video to export the shot",
        ]
        return result
