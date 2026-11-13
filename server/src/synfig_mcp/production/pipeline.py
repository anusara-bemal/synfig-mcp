"""
End-to-end production orchestrator (Step 5).

``AnimeProductionPipeline.run`` chains the existing engines into one
reproducible run: it creates the document, lays out the storyboard, expands and
rigs every character (optionally emitting a model sheet), generates or fetches
the assets, applies the style stack, renders the video and contact sheet, and
runs the objective review.  It owns ordering and reporting, not low-level layer
math.

Each stage records a :class:`~synfig_mcp.production.models.StageReport`.  A
stage failure is collected, never fatal, so a partial run still reports exactly
what succeeded and why the rest did not.  ``dry_run`` builds nothing;
``stages`` and ``resume_from`` let a long run be inspected and partially re-run.
"""

from __future__ import annotations

import contextlib
import math
import re
from pathlib import Path
from typing import Any

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.characters.cutout import (
    CanvasFrame,
    CutoutCharacter,
    MotionAction,
    attach_waypoints,
    compile_character,
    plan_actions,
    vector,
)
from synfig_mcp.characters.models import StoryboardShot
from synfig_mcp.characters.rigging import remember_rig
from synfig_mcp.characters.storyboard import StoryboardEngine
from synfig_mcp.errors import SynfigError
from synfig_mcp.production.asset_generator import AssetGenerator
from synfig_mcp.production.character_builder import CharacterBuilder
from synfig_mcp.production.models import (
    AssetRequest,
    CharacterDescriptor,
    ProductionBrief,
    ProductionReport,
    StageReport,
)
from synfig_mcp.production.rig_sheet import RigSheetGenerator
from synfig_mcp.production.state import (
    STATE_FILENAME,
    ProductionState,
    brief_fingerprint,
)
from synfig_mcp.production.story import (
    STORY_FILENAME,
    build_screenplay,
    compile_story,
    validate_story,
)
from synfig_mcp.recipes.engine import RecipeEngine
from synfig_mcp.recipes.styles import get_style_preset
from synfig_mcp.render.pipeline import RenderPipeline
from synfig_mcp.review.service import ReviewService

#: The stages, in execution order.
STAGES: tuple[str, ...] = (
    "document",
    "story",
    "storyboard",
    "characters",
    "assets",
    "style",
    "render",
    "review",
)

_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    cleaned = _SLUG.sub("_", text.strip().lower()).strip("_")
    return cleaned or "production"


class AnimeProductionPipeline:
    """Run a whole production from one brief."""

    def __init__(
        self,
        backend: BackendBase,
        asset_pipeline: Any | None = None,
        output_dir: Path | str | None = None,
    ) -> None:
        self.backend = backend
        self.asset_pipeline = asset_pipeline
        self.output_dir = Path(output_dir) if output_dir else None

    # -- entry point -------------------------------------------------------

    async def run(
        self,
        brief: ProductionBrief | dict[str, Any],
        dry_run: bool = False,
        stages: list[str] | None = None,
        resume_from: str | None = None,
        resume: bool = True,
    ) -> ProductionReport:
        """Execute the pipeline and return the structured report.

        ``resume`` (the default) reuses a matching ``pipeline_state.json`` in the
        output directory: completed stages are restored from disk instead of
        rebuilt, and a partially built document is reopened.  Pass ``resume=False``
        to force a clean run.  ``resume_from`` still works and forces a rebuild
        from that stage onward.
        """
        if isinstance(brief, dict):
            brief = ProductionBrief.model_validate(brief)

        requested = list(stages) if stages else list(STAGES)
        unknown = [s for s in requested if s not in STAGES]
        if unknown:
            raise SynfigError(f"Unknown stages {unknown}. Valid stages: {list(STAGES)}.")
        resume_index = STAGES.index(resume_from) if resume_from in STAGES else 0

        report = ProductionReport(
            success=True,
            title=brief.title,
            style=brief.style,
            dry_run=dry_run,
        )
        preset = get_style_preset(brief.style)
        if preset is None:
            raise SynfigError(f"Unknown style '{brief.style}'. Use style_list to see the presets.")
        generator = AssetGenerator(palette=preset.palette, style=brief.style)
        builder = CharacterBuilder(style_palette=preset.palette)

        slug = _slug(brief.title)
        out_dir = self._resolve_output_dir(brief, slug)
        state_path = out_dir / STATE_FILENAME
        document_path = brief.save_path or str(out_dir / f"{slug}.sif")

        # Resume: reopen a matching previous run instead of rebuilding.  A stage is
        # only restored when the reopened document already contains its effect, so a
        # resumed run never duplicates layers.  ``resume_from`` forces a rebuild.
        state: ProductionState | None = None
        if not dry_run:
            loaded = ProductionState.load(state_path) if (resume and resume_from is None) else None
            if loaded is not None and loaded.matches(brief):
                state = loaded
                report.stages.append(loaded.report())
            else:
                state = ProductionState(
                    title=brief.title,
                    style=brief.style,
                    fingerprint=brief_fingerprint(brief),
                    output_dir=str(out_dir),
                )

        shots = brief.shots or [
            StoryboardShot(
                shot_id="shot_01",
                description=f"{brief.title} - single continuous shot",
                duration_seconds=brief.duration,
            )
        ]
        duration = sum(shot.duration_seconds for shot in shots)

        doc_id: str | None = None
        frame: CanvasFrame | None = None
        # Reopen the document a previous run saved, so downstream stages address it.
        if state is not None and state.document_path:
            try:
                info = await self.backend.doc_open(state.document_path)
                doc_id = info.id
                view_box = await self.backend.doc_view_box(doc_id)
                frame = CanvasFrame.for_document(
                    brief.width, brief.height, view_box, coords="pixels"
                )
                report.doc_id = doc_id
            except Exception:  # noqa: BLE001 - a stale/moved document is not fatal
                state.scene_built = False
                state.saved_through = None
                state.document_path = None

        render_available = True
        if not dry_run:
            try:
                health = await self.backend.health_check()
                render_available = bool(health.details.get("cli_available", True))
            except Exception:  # noqa: BLE001 - an unknown backend is assumed capable
                render_available = True

        def persist() -> None:
            if dry_run or state is None:
                return
            with contextlib.suppress(OSError):
                state.save(state_path)

        def restorable(name: str) -> bool:
            """Whether a completed stage's effect is present in the reopened document.

            Only stages whose effect lives in the saved document are restored; the
            render and review stages always re-run (their outputs are cheap to detect
            and their report carries the artifact paths the caller reads back).
            """
            if state is None or state.completed(name) is None:
                return False
            saved_rank = {"document": 0, "storyboard": 1, "style": 2}
            saved = saved_rank.get(state.saved_through or "", -1)
            if name == "document":
                return saved >= 0
            if name == "story":
                # The bible is a JSON artifact, not a document change: it is
                # restorable only while the file the previous run wrote still exists.
                return state.completed(name) is not None and (out_dir / STORY_FILENAME).is_file()
            if name == "storyboard":
                return saved >= 1
            if name in ("characters", "assets"):
                return state.scene_built
            if name == "style":
                return saved >= 2
            return False

        async def stage(name: str, coro_factory: Any) -> None:
            if name not in requested:
                report.stages.append(
                    StageReport(name=name, status="skipped", detail="not requested")
                )
                return
            if STAGES.index(name) < resume_index:
                report.stages.append(
                    StageReport(name=name, status="skipped", detail=f"resumed from '{resume_from}'")
                )
                return
            if state is not None and restorable(name):
                report.stages.append(state.stages[name].report)
                return
            try:
                result = await coro_factory()
            except SynfigError as exc:
                report.success = False
                report.stages.append(StageReport(name=name, status="failed", detail=exc.message))
                return
            except Exception as exc:  # noqa: BLE001 - report, never abort the run
                report.success = False
                report.stages.append(
                    StageReport(name=name, status="failed", detail=f"{type(exc).__name__}: {exc}")
                )
                return
            report.stages.append(result)
            if state is not None and result.status != "failed":
                state.record(result)
                persist()

        async def save_document(through: str | None) -> None:
            """Save the working document so a later run can resume from it."""
            if dry_run or state is None or doc_id is None:
                return
            try:
                saved = await self.backend.doc_save(doc_id, document_path)
            except Exception:  # noqa: BLE001 - an intermediate save is best-effort
                return
            state.doc_id = doc_id
            state.document_path = saved
            # Never move ``saved_through`` backwards: a resumed run re-saves the
            # reopened document at the early stages without undoing later ones.
            ranks = {"document": 0, "storyboard": 1, "style": 2}
            if through is not None and ranks.get(through, -1) >= ranks.get(
                state.saved_through or "", -1
            ):
                state.saved_through = through
            persist()

        # 1. document ------------------------------------------------------
        async def do_document() -> StageReport:
            nonlocal doc_id, frame
            if dry_run:
                return StageReport(
                    name="document",
                    detail=f"would create {brief.width}x{brief.height} @ {brief.fps}fps, {duration:.2f}s",
                )
            info = await self.backend.doc_new(width=brief.width, height=brief.height, fps=brief.fps)
            doc_id = info.id
            await self.backend.doc_set_time_range(
                doc_id=doc_id, start_time=0.0, end_time=duration, fps=brief.fps
            )
            view_box = await self.backend.doc_view_box(doc_id)
            frame = CanvasFrame.for_document(brief.width, brief.height, view_box, coords="pixels")
            report.doc_id = doc_id
            return StageReport(
                name="document",
                detail=f"created {doc_id} ({brief.width}x{brief.height} @ {brief.fps}fps)",
                metrics={"doc_id": doc_id, "duration": round(duration, 3)},
            )

        await stage("document", do_document)
        await save_document("document")

        # 1b. story --------------------------------------------------------
        if not dry_run:
            # The bible is a file artifact, so its path is known before the stage
            # runs; recording it here keeps a resumed report complete even when the
            # stage itself is restored instead of re-executed.
            report.artifacts["story_bible"] = str(out_dir / STORY_FILENAME)

        async def do_story() -> StageReport:
            bible = compile_story(brief)
            issues = validate_story(brief, bible)
            screenplay = build_screenplay(brief, bible)
            if issues:
                # Do not leave a bible file (or artifact claim) for an inconsistent story.
                report.artifacts.pop("story_bible", None)
                return StageReport(
                    name="story",
                    status="failed",
                    detail="story bible is inconsistent: " + "; ".join(issues),
                    metrics={"issues": issues},
                )
            if not dry_run:
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / STORY_FILENAME).write_text(
                    bible.model_dump_json(indent=2), encoding="utf-8"
                )
            source = "authored" if bible.authored else "derived from the brief"
            return StageReport(
                name="story",
                detail=(
                    f"{source}: {len(bible.characters)} character(s), "
                    f"{len(bible.scenes)} scene(s), {screenplay.shot_count} shot(s)"
                ),
                metrics={
                    "authored": bible.authored,
                    "characters": [c.id for c in bible.characters],
                    "scenes": len(bible.scenes),
                },
            )

        await stage("story", do_story)

        # 2. storyboard ----------------------------------------------------
        async def do_storyboard() -> StageReport:
            manifest = [
                {
                    "index": i + 1,
                    "shot_id": shot.shot_id,
                    "description": shot.description,
                    "duration": shot.duration_seconds,
                    "camera": shot.camera_movement,
                    "characters": shot.characters_present,
                }
                for i, shot in enumerate(shots)
            ]
            if dry_run or doc_id is None:
                return StageReport(
                    name="storyboard",
                    detail=f"would lay out {len(manifest)} shot(s)",
                    metrics={"shots": manifest},
                )
            if brief.shots:
                engine = StoryboardEngine(backend=self.backend)
                res = await engine.storyboard_from_script(
                    spec={
                        "title": brief.title,
                        "doc_id": doc_id,
                        "fps": brief.fps,
                        "shots": [shot.model_dump() for shot in shots],
                    }
                )
                manifest = res.get("shots", manifest)
            report.total_shots = len(manifest)
            report.duration_seconds = round(duration, 3)
            return StageReport(
                name="storyboard",
                detail=f"{len(manifest)} shot(s), {duration:.2f}s",
                metrics={"shots": manifest},
            )

        await stage("storyboard", do_storyboard)
        await save_document("storyboard")

        # 3. characters ----------------------------------------------------
        async def do_characters() -> StageReport:
            characters: list[CutoutCharacter] = []
            unplaced = [c for c in brief.characters if c.position is None]
            for descriptor in brief.characters:
                parts = builder.as_cutout_parts(builder.expand(descriptor))
                position = descriptor.position
                if position is None:
                    slot = unplaced.index(descriptor) + 1
                    position = {
                        "x": brief.width * slot / (len(unplaced) + 1),
                        "y": brief.height * 0.9,
                    }
                actions = [MotionAction.model_validate(a) for a in descriptor.actions]
                if not actions:
                    actions = [MotionAction(motion="idle", start=0.0, end=duration)]
                characters.append(
                    CutoutCharacter(
                        id=descriptor.id,
                        parts=parts,
                        position=position,
                        height=brief.height * descriptor.height,
                        flip=descriptor.facing == "left",
                        z=descriptor.z,
                        actions=actions,
                    )
                )
            report.artifacts["characters"] = str(len(characters))
            if dry_run or doc_id is None or frame is None:
                return StageReport(
                    name="characters",
                    detail=f"would rig {len(characters)} character(s)",
                    metrics={"characters": [c.id for c in characters]},
                )
            # Compile every rig and stash the layers for the main build.
            compiled = []
            for character in characters:
                rig = compile_character(character, frame)
                plan = plan_actions(rig, character.actions, frame, duration)
                attach_waypoints(rig, plan)
                compiled.append((rig, plan))
                remember_rig(doc_id, rig)
            self._pending_rigs = compiled
            return StageReport(
                name="characters",
                detail=f"rigged {len(compiled)} character(s)",
                metrics={
                    "characters": [
                        {
                            "id": rig.character_id,
                            "parts": len(rig.parts),
                            "waypoints": plan.count(),
                            "motions": plan.applied,
                        }
                        for rig, plan in compiled
                    ]
                },
            )

        await stage("characters", do_characters)

        # 4. assets --------------------------------------------------------
        async def do_assets() -> StageReport:
            background_layers: list[dict[str, Any]] = []
            prop_layers: list[dict[str, Any]] = []
            texture_layers: list[dict[str, Any]] = []
            artifacts: list[str] = []
            warnings: list[str] = []

            frame_units = self._frame_units(frame, brief)
            # Convenience background.
            bg = brief.background
            if bg is None:
                bg = {"generator": "landscape"}
            if isinstance(bg, dict) and bg.get("generator"):
                background_layers += generator.background(
                    str(bg["generator"]), frame_units, seed=brief.seed
                )
            elif isinstance(bg, dict) and bg.get("file"):
                background_layers.append(self._import_layer("Background", bg["file"]))

            for index, request in enumerate(brief.assets):
                seed = brief.seed + index + 1
                if request.procedural:
                    spec = dict(request.procedural)
                    kind = spec.pop("generator", request.kind)
                    if request.kind == "background":
                        background_layers += generator.background(kind, frame_units, seed=seed)
                    elif request.kind == "texture":
                        texture_layers += generator.texture(kind, frame_units, seed=seed)
                    else:
                        origin = self._pixel_origin(request.position, brief, frame_units)
                        size = self._prop_size(request.height, brief, frame_units)
                        prop_layers += generator.prop(kind, origin, size, seed=seed)
                elif request.search:
                    fetched = await self._fetch_asset(request)
                    if fetched is None:
                        warnings.append(
                            f"asset '{request.id}' was not fetched (no pipeline/offline)"
                        )
                    else:
                        artifacts.append(str(fetched))
                        prop_layers.append(self._import_layer(f"Asset_{request.id}", str(fetched)))

            self._pending_background = background_layers
            self._pending_props = prop_layers
            self._pending_textures = texture_layers
            return StageReport(
                name="assets",
                detail=(
                    f"{len(background_layers)} background, {len(prop_layers)} prop, "
                    f"{len(texture_layers)} texture layer(s)"
                ),
                artifacts=artifacts,
                metrics={"background": len(background_layers), "props": len(prop_layers)},
                warnings=warnings,
            )

        await stage("assets", do_assets)

        # Main build (characters + assets + camera) as one atomic scene_build.
        if not dry_run and doc_id is not None and frame is not None:
            if state is not None and state.scene_built:
                report.stages.append(
                    StageReport(name="scene_build", detail="restored the assembled scene")
                )
            else:
                try:
                    await self._build_scene(brief, doc_id, frame, duration)
                except SynfigError as exc:
                    report.success = False
                    report.stages.append(
                        StageReport(name="scene_build", status="failed", detail=exc.message)
                    )
                else:
                    report.stages.append(
                        StageReport(name="scene_build", detail="assembled scene in one undo step")
                    )
                    if state is not None:
                        state.scene_built = True
                    await save_document("storyboard")

        # 5. style ---------------------------------------------------------
        async def do_style() -> StageReport:
            if doc_id is None:
                return StageReport(name="style", detail="would apply style stack")
            engine = RecipeEngine(backend=self.backend)
            res = await engine.apply_style(doc_id=doc_id, style_name=brief.style, dry_run=dry_run)
            if res.get("success") is False:
                raise SynfigError(str(res.get("error", "style_apply failed")))
            return StageReport(
                name="style",
                detail=f"applied '{brief.style}' ({len(res.get('applied_recipes', []))} recipes)",
                metrics={"recipes": res.get("applied_recipes", [])},
            )

        await stage("style", do_style)
        if state is not None and state.completed("style") and not restorable("style"):
            await save_document("style")

        # 6. render --------------------------------------------------------
        async def do_render() -> StageReport:
            artifacts: list[str] = []
            warnings: list[str] = []
            if dry_run or doc_id is None:
                return StageReport(name="render", detail="would render video and contact sheet")
            out_dir.mkdir(parents=True, exist_ok=True)
            save_target = brief.save_path or str(out_dir / f"{slug}.sif")
            saved = await self.backend.doc_save(doc_id, save_target)
            report.artifacts["document"] = saved
            artifacts.append(saved)
            if not render_available:
                return StageReport(
                    name="render",
                    detail="saved the document; no Synfig engine on PATH, so video/contact sheet "
                    "were skipped",
                    artifacts=artifacts,
                    warnings=["install Synfig (or set SYNFIG_BIN) to render frames"],
                )

            pipeline = RenderPipeline(self.backend)
            if brief.render.contact_sheet:
                sheet_path = out_dir / f"{slug}_contact_sheet.png"
                try:
                    await pipeline.render_contact_sheet(doc_id=doc_id, output_path=str(sheet_path))
                    report.artifacts["contact_sheet"] = str(sheet_path)
                    artifacts.append(str(sheet_path))
                except SynfigError as exc:
                    warnings.append(f"contact sheet: {exc.message}")
            if brief.render.video:
                ext = "gif" if brief.render.video_format == "gif" else "mp4"
                video_path = out_dir / f"{slug}.{ext}"
                try:
                    await pipeline.render_video(doc_id=doc_id, output_path=str(video_path))
                    report.artifacts["video"] = str(video_path)
                    artifacts.append(str(video_path))
                except SynfigError as exc:
                    warnings.append(f"video: {exc.message}")
            if not artifacts:
                raise SynfigError("; ".join(warnings) or "nothing was rendered")
            return StageReport(
                name="render",
                detail=f"{len(artifacts)} artifact(s)",
                artifacts=artifacts,
                warnings=warnings,
            )

        await stage("render", do_render)

        # 7. review --------------------------------------------------------
        async def do_review() -> StageReport:
            if dry_run or doc_id is None:
                return StageReport(name="review", detail="would run the review loop")
            if not render_available:
                return StageReport(
                    name="review",
                    status="skipped",
                    detail="no Synfig engine on PATH, so the review loop was skipped",
                )
            service = ReviewService(self.backend)
            res = await service.review_sequence(
                doc_id=doc_id,
                start_time=0.0,
                end_time=duration,
                frame_count=brief.render.preview_frames,
                width=min(brief.width, 480),
                height=min(brief.height, 270),
            )
            report.review = {
                "strobe": res.get("strobe_check", {}),
                "motion": res.get("motion_stats", []),
            }
            warnings = list(res.get("warnings", []))
            report.warnings.extend(warnings)
            return StageReport(
                name="review",
                detail=f"reviewed {res.get('frame_count', 0)} frame(s)",
                metrics={"warnings": len(warnings)},
                warnings=warnings,
            )

        await stage("review", do_review)

        if report.success:
            report.success = all(s.status != "failed" for s in report.stages)
        return report

    # -- helpers -----------------------------------------------------------

    def _resolve_output_dir(self, brief: ProductionBrief, slug: str) -> Path:
        """Resolve where artifacts go: explicit dir > brief.output_dir > cwd/<slug>."""
        if self.output_dir:
            return Path(self.output_dir)
        if brief.output_dir:
            return Path(brief.output_dir)
        return Path.cwd() / f"{slug}_production"

    def _frame_units(
        self, frame: CanvasFrame | None, brief: ProductionBrief
    ) -> tuple[float, float, float, float]:
        if frame is not None:
            return (frame.left, frame.top, frame.right, frame.bottom)
        half_w, half_h = brief.width / 120.0, brief.height / 120.0
        return (-half_w, half_h, half_w, -half_h)

    def _pixel_origin(
        self,
        position: dict[str, float] | None,
        brief: ProductionBrief,
        frame: tuple[float, float, float, float],
    ) -> tuple[float, float]:
        left, top, right, bottom = frame
        x_px = float(position["x"]) if position and "x" in position else brief.width / 2
        y_px = float(position["y"]) if position and "y" in position else brief.height * 0.8
        ux = left + (right - left) * (x_px / max(1, brief.width))
        uy = top + (bottom - top) * (y_px / max(1, brief.height))
        return (ux, uy)

    def _prop_size(
        self, height: float | None, brief: ProductionBrief, frame: tuple[float, float, float, float]
    ) -> float:
        left, top, right, bottom = frame
        span_y = abs(top - bottom)
        px = height if height else brief.height * 0.2
        return span_y * (px / max(1, brief.height))

    @staticmethod
    def _import_layer(layer_id: str, file_path: str) -> dict[str, Any]:
        """An ``import`` layer covering the whole canvas with a picture."""
        return {
            "id": layer_id,
            "type": "import",
            "params": {"filename": {"type": "string", "value": str(file_path)}},
        }

    async def _fetch_asset(self, request: AssetRequest) -> str | None:
        """Best-effort opt-in fetch; returns the local path or None."""
        if self.asset_pipeline is None:
            return None
        search = request.search or {}
        query = str(search.get("query", request.id))
        provider = str(search.get("provider", "openverse"))
        try:
            found = await self.asset_pipeline.search(query=query, provider=provider, limit=1)
        except Exception:  # noqa: BLE001 - offline or network failure is not fatal
            return None
        results = found.get("results", []) if isinstance(found, dict) else []
        if not results:
            return None
        asset_id = str(results[0].get("id"))
        downloaded = await self.asset_pipeline.download_asset(asset_id=asset_id, provider=provider)
        if downloaded.get("success") is False:
            return None
        return str(downloaded.get("local_path") or "")

    async def _build_scene(
        self,
        brief: ProductionBrief,
        doc_id: str,
        frame: CanvasFrame,
        duration: float,
    ) -> None:
        """Assemble characters, assets and camera into one scene_build call."""
        layers: list[dict[str, Any]] = []
        groups: list[dict[str, Any]] = []

        background = getattr(self, "_pending_background", [])
        props = getattr(self, "_pending_props", [])
        textures = getattr(self, "_pending_textures", [])
        rigs = getattr(self, "_pending_rigs", [])

        layers += background
        if background:
            groups.append({"id": "Background", "layer_ids": [layer["id"] for layer in background]})

        for rig, _plan in rigs:
            layers += rig.layers
            groups += rig.groups

        layers += props
        layers += textures
        if textures:
            groups.append({"id": "Overlay", "layer_ids": [layer["id"] for layer in textures]})

        camera_layers, camera_group = self._camera_layers(brief, frame, duration)
        layers += camera_layers
        if camera_group:
            groups.append(camera_group)

        result = await self.backend.scene_build(
            spec={
                "doc_id": doc_id,
                "width": brief.width,
                "height": brief.height,
                "fps": brief.fps,
                "start_time": 0.0,
                "end_time": duration,
                "layers": layers,
                "groups": groups,
            }
        )
        if result.get("success") is False:
            raise SynfigError(str(result.get("error", "scene_build rejected the production.")))

    @staticmethod
    def _camera_layers(
        brief: ProductionBrief, frame: CanvasFrame, duration: float
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """A gentle pan/zoom camera unless the brief supplies its own keys."""
        keys = list(brief.camera)
        if not keys and not brief.shots:
            keys = [
                {"time": 0.0, "zoom": 1.0},
                {"time": duration, "zoom": 1.12},
            ]
        if not keys:
            return [], None
        ordered = sorted(keys, key=lambda k: float(k.get("time", 0.0)))
        mid = ((frame.left + frame.right) / 2, (frame.top + frame.bottom) / 2)

        def pan(key: dict[str, Any]) -> tuple[float, float]:
            centre = key.get("center")
            if not centre:
                return (0.0, 0.0)
            x, y = frame.point(float(centre.get("x", 0)), float(centre.get("y", 0)))
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
                "amount": {
                    "type": "real",
                    "value": round(math.log(float(first.get("zoom", 1.0))), 6),
                },
                "center": vector(*mid),
            },
        }
        if len(ordered) > 1:
            pan_layer["waypoints"] = [
                {
                    "param": "origin",
                    "time": float(k.get("time", 0.0)),
                    "value": vector(*pan(k)),
                    "interpolation": "clamped",
                }
                for k in ordered
            ]
            zoom_layer["waypoints"] = [
                {
                    "param": "amount",
                    "time": float(k.get("time", 0.0)),
                    "value": {
                        "type": "real",
                        "value": round(math.log(float(k.get("zoom", 1.0))), 6),
                    },
                    "interpolation": "clamped",
                }
                for k in ordered
            ]
        return [pan_layer, zoom_layer], {"id": "Camera", "layer_ids": ["Camera_pan", "Camera_zoom"]}

    async def model_sheet(
        self,
        descriptor: CharacterDescriptor,
        brief: ProductionBrief,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Build a labeled model sheet for one character in its own document."""
        preset = get_style_preset(brief.style)
        builder = CharacterBuilder(style_palette=preset.palette if preset else None)
        specs = builder.expand(descriptor)
        parts = builder.as_cutout_parts(specs)
        if dry_run:
            return {"success": True, "dry_run": True, "character_id": descriptor.id}
        info = await self.backend.doc_new(width=brief.width, height=brief.height, fps=brief.fps)
        generator = RigSheetGenerator(self.backend)
        result = await generator.generate(
            character_id=descriptor.id,
            parts=parts,
            doc_id=info.id,
            height=brief.height * descriptor.height,
            title=f"{brief.title} - {descriptor.id} model sheet",
        )
        result["sheet_doc_id"] = info.id
        return result
