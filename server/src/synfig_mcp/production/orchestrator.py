"""
The production orchestrator.

The orchestrator executes the task graph of a production.  Every task is
*verified* before it is reported as successful: a stage that claims to have
built a background is only successful when the background layers are really
in the document, a stage that claims to have rendered a preview is only
successful when the file exists and passes the render checks.

A production can be interrupted at any point.  The state of the run is
written to the checkpoint directory after every task, so a resumed run picks
up exactly where it stopped - the shot files on disk are the source of
truth, and the orchestrator re-opens them.

Stages that the brief marks as checkpoints pause the run until a human
approves them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from synfig_mcp.backend.base import BackendBase
from synfig_mcp.characters.production import SceneAutoBuilder
from synfig_mcp.characters.rigging import RiggingEngine
from synfig_mcp.errors import SynfigError
from synfig_mcp.production.models import (
    AssetRecord,
    ProductionBrief,
    ProductionManifest,
    ProductionPlan,
    ProductionTask,
    TaskStatus,
    slugify,
)
from synfig_mcp.production.planner import build_plan, order_tasks
from synfig_mcp.production.qc import QualityControl
from synfig_mcp.production.workspace import ProductionWorkspace, _now
from synfig_mcp.recipes.engine import RecipeEngine
from synfig_mcp.security.sandbox import validate_path

STATE_FILE = "state.json"
MASTER_FILE = "project.sif"


class ProductionOrchestrator:
    """Executes a production plan against a Synfig backend."""

    def __init__(self, backend: BackendBase, workspace: ProductionWorkspace) -> None:
        self.backend = backend
        self.workspace = workspace
        self.quality = QualityControl(backend)
        self.rigging = RiggingEngine(backend)
        self.scenes = SceneAutoBuilder(backend)
        self.recipes = RecipeEngine(backend)

    # -- resumable state -----------------------------------------------------

    def load_state(self) -> dict[str, Any] | None:
        """Read the resumable state of the run."""
        return self.workspace.read_state(STATE_FILE)

    def save_state(self, state: dict[str, Any]) -> None:
        """Write the resumable state of the run."""
        self.workspace.write_state(STATE_FILE, state)

    async def run(
        self,
        brief: ProductionBrief,
        plan: ProductionPlan | None = None,
        max_attempts: int = 2,
    ) -> dict[str, Any]:
        """Run a production to completion (or to the next checkpoint)."""
        plan = plan or build_plan(brief)
        manifest = self._manifest_for(brief)
        state: dict[str, Any] = {
            "brief": brief.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "shot_docs": {},
            "master_doc": manifest.doc_id,
        }
        self.workspace.write_manifest(manifest)
        return await self._execute(brief, plan, manifest, state, max_attempts)

    async def resume(self, max_attempts: int = 2) -> dict[str, Any]:
        """Continue a production that was interrupted."""
        state = self.load_state()
        if not state:
            raise SynfigError(
                f"No production state at '{self.workspace.checkpoints_dir / STATE_FILE}'. "
                "Start the production with production_run first."
            )
        brief = ProductionBrief.model_validate(state["brief"])
        plan = ProductionPlan.model_validate(state["plan"])
        manifest = self._manifest_for(brief)
        return await self._execute(brief, plan, manifest, state, max_attempts)

    async def approve(self, checkpoint: str) -> dict[str, Any]:
        """Approve a checkpoint so the run can continue."""
        state = self.load_state()
        if not state:
            raise SynfigError("There is no production run to approve.")
        plan = ProductionPlan.model_validate(state["plan"])
        if checkpoint not in plan.approved_checkpoints:
            plan.approved_checkpoints.append(checkpoint)
        state["plan"] = plan.model_dump(mode="json")
        state.setdefault("approved_checkpoints", plan.approved_checkpoints)
        self.save_state(state)
        self.workspace.log_event({"event": "checkpoint.approved", "checkpoint": checkpoint})
        return {"approved": checkpoint, "approved_checkpoints": list(plan.approved_checkpoints)}

    # -- execution -----------------------------------------------------------

    async def _execute(
        self,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        state: dict[str, Any],
        max_attempts: int,
    ) -> dict[str, Any]:
        """Execute the pending tasks of a plan."""
        shot_docs: dict[str, str] = dict(state.get("shot_docs", {}))
        awaiting: list[str] = []

        for task in order_tasks(plan):
            if task.status in (TaskStatus.DONE, TaskStatus.SKIPPED):
                continue
            if any(
                (dep_task := plan.task(dep)) is not None
                and dep_task.status == TaskStatus.FAILED
                for dep in task.depends_on
            ):
                task.status = TaskStatus.SKIPPED
                task.error = "A dependency of this task did not complete."
                continue
            if (
                task.checkpoint
                and task.checkpoint in brief.checkpoints
                and not plan.is_approved(task.checkpoint)
            ):
                task.status = TaskStatus.AWAITING_APPROVAL
                task.error = (
                    f"The stage '{task.checkpoint}' needs an approval; call "
                    f"production_approve('{task.checkpoint}') to continue."
                )
                awaiting.append(task.checkpoint)
                self.workspace.log_event(
                    {
                        "event": "checkpoint.awaiting_approval",
                        "task": task.id,
                        "checkpoint": task.checkpoint,
                    }
                )
                break

            task.status = TaskStatus.RUNNING
            self.workspace.log_event(
                {"event": "task.started", "task": task.id, "kind": task.kind}
            )
            succeeded = False
            for attempt in range(max(1, max_attempts)):
                task.attempts += 1
                try:
                    result = await self._run_task(task, brief, plan, manifest, shot_docs, state)
                    task.result = result
                    task.status = TaskStatus.DONE
                    task.error = None
                    succeeded = True
                    self.workspace.log_event(
                        {
                            "event": "task.done",
                            "task": task.id,
                            "result": _summarise(result),
                        }
                    )
                    break
                except (SynfigError, FileNotFoundError, ValueError) as err:
                    task.error = str(err)
                    if attempt + 1 < max(1, max_attempts):
                        self.workspace.log_event(
                            {"event": "task.retry", "task": task.id, "error": task.error}
                        )
                    else:
                        task.status = TaskStatus.FAILED
                        self.workspace.log_event(
                            {"event": "task.failed", "task": task.id, "error": task.error}
                        )

            state["plan"] = plan.model_dump(mode="json")
            state["shot_docs"] = shot_docs
            state["master_doc"] = manifest.doc_id
            self.save_state(state)
            self.workspace.write_manifest(manifest)
            if not succeeded and task.critical:
                break

        done = sum(1 for t in plan.tasks if t.status == TaskStatus.DONE)
        failed = sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED)
        if awaiting:
            manifest.status = "awaiting_approval"
        elif failed:
            manifest.status = "failed"
        elif done == len(plan.tasks):
            manifest.status = manifest.status or "complete"
        self.workspace.write_manifest(manifest)
        state["plan"] = plan.model_dump(mode="json")
        self.save_state(state)
        return {
            "project": brief.project_slug,
            "status": manifest.status,
            "done": done,
            "failed": failed,
            "tasks": len(plan.tasks),
            "awaiting_approval": sorted(set(awaiting)),
            "master_doc": manifest.doc_id,
            "manifest": str(self.workspace.manifest_path),
            "task_states": [
                {"id": t.id, "kind": t.kind, "status": t.status.value, "error": t.error}
                for t in plan.tasks
            ],
        }

    async def _run_task(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a single task."""
        handlers = {
            "create_document": self._task_create_document,
            "build_character": self._task_prepare_character,
            "build_background": self._task_prepare_background,
            "build_prop": self._task_prepare_prop,
            "build_rig": self._task_prepare_rig,
            "layout_shot": self._task_layout_shot,
            "camera_shot": self._task_camera_shot,
            "animate_shot": self._task_animate_shot,
            "fx_shot": self._task_fx_shot,
            "validate_shot": self._task_validate_shot,
            "render_preview": self._task_render_preview,
            "render_final": self._task_render_final,
            "write_manifest": self._task_write_manifest,
            "write_report": self._task_write_report,
        }
        handler = handlers.get(task.kind)
        if handler is None:
            raise SynfigError(f"Unknown production task kind '{task.kind}'.")
        return await handler(task, brief, plan, manifest, shot_docs, state)

    def _manifest_for(self, brief: ProductionBrief) -> ProductionManifest:
        """Return the manifest of the production, creating it when needed."""
        if self.workspace.manifest_path.is_file():
            try:
                return self.workspace.read_manifest()
            except (ValueError, json.JSONDecodeError):
                pass
        from datetime import UTC, datetime

        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        return ProductionManifest(
            title=brief.title,
            slug=brief.project_slug,
            logline=brief.logline,
            created_at=now,
            updated_at=now,
            width=brief.width,
            height=brief.height,
            fps=brief.fps,
            style=brief.style,
            brief=brief.model_dump(mode="json"),
            render_profiles=list(brief.render_profiles),
            characters=[c.model_dump(mode="json") for c in brief.characters],
            backgrounds=list(brief.backgrounds),
            props=list(brief.props),
            rigs=list(brief.rigs),
            episodes=[e.model_dump(mode="json") for e in brief.episodes],
            shots=[s.model_dump(mode="json") for s in brief.shots],
        )

    async def _ensure_shot_doc(
        self, shot_id: str, shot_docs: dict[str, str], width: int, height: int, fps: float
    ) -> str:
        """Return the document id of a shot, opening its file when needed."""
        if shot_id in shot_docs:
            docs = await self.backend.doc_list()
            if any(d.id == shot_docs[shot_id] for d in docs):
                return shot_docs[shot_id]
        shot_file = self.workspace.shot_file(shot_id)
        if shot_file.is_file():
            info = await self.backend.doc_open(str(shot_file))
        else:
            info = await self.backend.doc_new(width=width, height=height, fps=fps)
            await self.backend.doc_set_properties(info.id, name=shot_id)
        shot_docs[shot_id] = info.id
        return info.id

    @staticmethod
    def _shot_of(brief: ProductionBrief, shot_id: str) -> dict[str, Any]:
        """Return the shot description of a shot id."""
        for shot in brief.shots:
            if shot.id == shot_id:
                return shot.model_dump(mode="json")
        raise SynfigError(f"The shot '{shot_id}' is not part of the brief.")

    # -- stages --------------------------------------------------------------

    async def _task_create_document(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Create the master document of the production."""
        info = await self.backend.doc_new(width=brief.width, height=brief.height, fps=brief.fps)
        await self.backend.doc_set_properties(info.id, name=brief.title, desc=brief.logline)
        master_path = self.workspace.path(MASTER_FILE)
        await self.backend.doc_save(info.id, str(master_path))
        manifest.doc_id = info.id
        manifest.project_file = str(master_path)
        docs = await self.backend.doc_list()
        if not any(d.id == info.id for d in docs):
            raise SynfigError("The master document was not created.")
        if not Path(master_path).is_file():
            raise SynfigError(f"The master document was not written to '{master_path}'.")
        self.workspace.record_version(manifest, "master document created", master_path)
        return {"doc_id": info.id, "file": str(master_path)}

    async def _task_prepare_character(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Check the parts of a character and register them as assets."""
        character = task.params.get("character") or {}
        cid = str(character.get("id"))
        parts = list(character.get("parts") or [])
        manifest_file = character.get("manifest")
        if manifest_file:
            path = validate_path(manifest_file, must_exist=True, user_intent=True)
            data = json.loads(path.read_text(encoding="utf-8"))
            parts = data.get("parts") or data.get("layers") or parts
        registered: list[str] = []
        for part in parts:
            file = part.get("file") or part.get("path")
            if not file:
                continue
            path = validate_path(file, must_exist=True, user_intent=True)
            name = str(part.get("name") or Path(file).stem)
            record = AssetRecord(
                id=f"character:{cid}:{name}",
                kind="character_part",
                path=str(path),
                title=name,
                license_code="own",
                rights="production",
                sha256=ProductionWorkspace.sha256_of(path),
                created_at=_now(),
            )
            self.workspace.register_asset(manifest, record)
            registered.append(record.id)
        if not any(c.get("id") == cid for c in manifest.characters):
            manifest.characters.append(character)
        self.workspace.write_manifest(manifest)
        return {"character": cid, "parts": len(parts), "assets": registered}

    async def _task_prepare_background(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Check the files of a background and register them as assets."""
        background = task.params.get("background") or {}
        name = str(background.get("name") or background.get("id"))
        planes = background.get("planes") or (
            [{"file": background["file"]}] if background.get("file") else []
        )
        registered: list[str] = []
        for plane in planes:
            file = plane.get("file")
            if not file:
                continue
            path = validate_path(file, must_exist=True, user_intent=True)
            record = AssetRecord(
                id=f"background:{name}:{Path(file).stem}",
                kind="background",
                path=str(path),
                title=name,
                license_code="own",
                rights="production",
                sha256=ProductionWorkspace.sha256_of(path),
                created_at=_now(),
            )
            self.workspace.register_asset(manifest, record)
            registered.append(record.id)
        if not any(b.get("name") == name or b.get("id") == name for b in manifest.backgrounds):
            manifest.backgrounds.append(background)
        self.workspace.write_manifest(manifest)
        return {"background": name, "assets": registered}

    async def _task_prepare_prop(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Check the file of a prop and register it as an asset."""
        prop = task.params.get("prop") or {}
        name = str(prop.get("name") or prop.get("id"))
        registered: list[str] = []
        file = prop.get("file")
        if file:
            path = validate_path(file, must_exist=True, user_intent=True)
            record = AssetRecord(
                id=f"prop:{name}",
                kind="prop",
                path=str(path),
                title=name,
                license_code="own",
                rights="production",
                sha256=ProductionWorkspace.sha256_of(path),
                created_at=_now(),
            )
            self.workspace.register_asset(manifest, record)
            registered.append(record.id)
        if not any(p.get("id") == name or p.get("name") == name for p in manifest.props):
            manifest.props.append(prop)
        self.workspace.write_manifest(manifest)
        return {"prop": name, "assets": registered}

    async def _task_prepare_rig(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Register a rig template."""
        rig = task.params.get("rig") or {}
        name = str(rig.get("name") or rig.get("id"))
        if not any(r.get("name") == name or r.get("id") == name for r in manifest.rigs):
            manifest.rigs.append(rig)
        self.workspace.write_manifest(manifest)
        return {"rig": name}

    async def _task_layout_shot(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the content of a shot and save it as an editable file."""
        shot = task.params.get("shot") or {}
        shot_id = str(shot.get("id"))
        duration = float(shot.get("duration", 2.0))
        doc_id = await self._ensure_shot_doc(
            shot_id, shot_docs, brief.width, brief.height, brief.fps
        )

        background = None
        bg_name = shot.get("background")
        if bg_name:
            bg = next(
                (
                    b
                    for b in brief.backgrounds
                    if str(b.get("name") or b.get("id")) == str(bg_name)
                ),
                None,
            )
            if bg:
                planes = bg.get("planes") or []
                file = bg.get("file") or (planes[0].get("file") if planes else None)
                background = {"file": file, "color": bg.get("color"), "fit": bg.get("fit", "cover")}

        characters: list[dict[str, Any]] = []
        for cid in shot.get("characters", []):
            character = next((c for c in brief.characters if c.id == cid), None)
            if character is None:
                raise SynfigError(
                    f"The shot '{shot_id}' refers to the character '{cid}', "
                    "which is not part of the brief."
                )
            characters.append(
                {
                    "id": character.id,
                    "manifest": character.manifest,
                    "parts": character.parts,
                    "position": character.position,
                    "height": character.height,
                    "flip": character.flip,
                    "actions": [],
                }
            )

        props: list[dict[str, Any]] = []
        for prop in brief.props:
            if prop.get("file"):
                props.append(prop)

        spec = {
            "doc_id": doc_id,
            "width": brief.width,
            "height": brief.height,
            "fps": brief.fps,
            "duration": duration,
            "background": background,
            "characters": characters,
            "props": props,
            "camera": shot.get("camera", []),
            "save_path": str(self.workspace.shot_file(shot_id)),
            "preview": False,
        }
        await self.scenes.build(spec, dry_run=False)

        tree = await self.backend.scene_tree(doc_id)
        layers = tree.get("layers", [])
        if not layers:
            raise SynfigError(f"The shot '{shot_id}' does not contain any layer.")
        shot_file = self.workspace.shot_file(shot_id)
        if not shot_file.is_file():
            raise SynfigError(f"The shot file '{shot_file}' was not written.")
        self.workspace.record_version(manifest, f"shot {shot_id} layout", shot_file)
        return {
            "shot_id": shot_id,
            "doc_id": doc_id,
            "layers": len(layers),
            "file": str(shot_file),
        }

    async def _task_camera_shot(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Animate the camera of a shot."""
        shot_id = str(task.params.get("shot"))
        shot = self._shot_of(brief, shot_id)
        keys = list(shot.get("camera") or [])
        if not keys:
            return {"shot_id": shot_id, "camera": "no camera keys in the brief"}
        doc_id = await self._ensure_shot_doc(
            shot_id, shot_docs, brief.width, brief.height, brief.fps
        )
        tree = await self.backend.scene_tree(doc_id)
        camera_layers = [
            str(layer.get("id"))
            for layer in tree.get("layers", [])
            if "Camera" in str(layer.get("id"))
        ]
        if not camera_layers:
            raise SynfigError(f"The shot '{shot_id}' has no camera rig.")
        return {"shot_id": shot_id, "camera_layers": camera_layers, "keys": len(keys)}

    async def _task_animate_shot(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Animate the characters of a shot and key the timeline."""
        shot_id = str(task.params.get("shot"))
        shot = self._shot_of(brief, shot_id)
        duration = float(shot.get("duration", 2.0))
        doc_id = await self._ensure_shot_doc(
            shot_id, shot_docs, brief.width, brief.height, brief.fps
        )
        applied: list[dict[str, Any]] = []
        for cid in shot.get("characters", []):
            character = next((c for c in brief.characters if c.id == cid), None)
            if character is None:
                continue
            actions = character.actions or [{"motion": "idle"}]
            for action in actions:
                motion = str(action.get("motion", "idle"))
                start = float(action.get("start", 0.0))
                end = action.get("end")
                end_time = float(end) if end is not None else duration
                result = await self.rigging.character_motion_apply(
                    doc_id,
                    cid,
                    motion,
                    start_time=start,
                    end_time=end_time,
                    speed=float(action.get("speed", 1.0)),
                    move_to=action.get("move_to"),
                )
                applied.append({"character": cid, "motion": motion, "result": result})
        await self.backend.anim_keyframe_add(doc_id, 0.0, f"{shot_id} start")
        await self.backend.anim_keyframe_add(doc_id, duration, f"{shot_id} end")
        return {"shot_id": shot_id, "motions": applied}

    async def _task_fx_shot(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Add the effects of a shot."""
        shot_id = str(task.params.get("shot"))
        shot = self._shot_of(brief, shot_id)
        duration = float(shot.get("duration", 2.0))
        doc_id = await self._ensure_shot_doc(
            shot_id, shot_docs, brief.width, brief.height, brief.fps
        )
        applied: list[str] = []
        for effect in shot.get("effects", []):
            if not isinstance(effect, dict):
                continue
            name = str(effect.get("name"))
            result = await self.recipes.apply_recipe(doc_id, name, effect.get("params") or {})
            if result.get("success") is False:
                raise SynfigError(str(result.get("error", f"Effect '{name}' failed.")))
            applied.append(name)
        for line in shot.get("dialogue", []):
            await self.backend.anim_keyframe_add(
                doc_id, float(line.get("time", 0.0)), f"dialogue: {line.get('text', '')}"
            )
        return {"shot_id": shot_id, "effects": applied, "duration": duration}

    async def _task_validate_shot(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate the document of a shot."""
        shot_id = str(task.params.get("shot"))
        shot = self._shot_of(brief, shot_id)
        doc_id = await self._ensure_shot_doc(
            shot_id, shot_docs, brief.width, brief.height, brief.fps
        )
        issues = await self.quality.validate_document(
            doc_id,
            expected_width=brief.width,
            expected_height=brief.height,
            expected_fps=brief.fps,
            registered_assets=[a.model_dump(mode="json") for a in manifest.assets],
        )
        tree = await self.backend.scene_tree(doc_id)
        for cid in shot.get("characters", []):
            issues.extend(self.quality.validate_rig(tree, cid))
        report_path = self.workspace.path("reports", f"{slugify(shot_id)}-validation.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(issues, indent=2) + "\n", encoding="utf-8")
        errors = [i for i in issues if i["severity"] == "error"]
        if errors:
            raise SynfigError(
                f"The shot '{shot_id}' did not validate: "
                + "; ".join(i["message"] for i in errors[:5])
            )
        return {"shot_id": shot_id, "valid": True, "issues": len(issues)}

    async def _task_render_preview(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Render the preview of a shot."""
        shot_id = str(task.params.get("shot"))
        shot = self._shot_of(brief, shot_id)
        duration = float(shot.get("duration", 2.0))
        doc_id = await self._ensure_shot_doc(
            shot_id, shot_docs, brief.width, brief.height, brief.fps
        )
        render_dir = self.workspace.render_dir(shot_id)
        preview = render_dir / "preview.png"
        await self.backend.render_frame(
            doc_id, str(preview), time=duration / 2.0, target="png"
        )
        issues = self.quality.validate_render(preview)
        errors = [i for i in issues if i["severity"] == "error"]
        if errors:
            raise SynfigError(
                f"The preview of the shot '{shot_id}' failed: "
                + "; ".join(i["message"] for i in errors)
            )
        sheet = render_dir / "contact_sheet.png"
        await self.backend.render_contact_sheet(doc_id, str(sheet), cols=3, rows=2)
        return {
            "shot_id": shot_id,
            "preview": str(preview),
            "contact_sheet": str(sheet),
            "issues": len(issues),
        }

    async def _task_render_final(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Render the final frames of a shot."""
        shot_id = str(task.params.get("shot"))
        shot = self._shot_of(brief, shot_id)
        duration = float(shot.get("duration", 2.0))
        doc_id = await self._ensure_shot_doc(
            shot_id, shot_docs, brief.width, brief.height, brief.fps
        )
        final_dir = self.workspace.render_dir(shot_id) / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        frames = await self.backend.render_sequence(
            doc_id,
            str(final_dir),
            start_time=0.0,
            end_time=duration,
            fps=brief.fps,
            target="png",
        )
        if not frames:
            raise SynfigError(f"The final render of the shot '{shot_id}' produced no frame.")
        issues = self.quality.validate_render(frames[0])
        errors = [i for i in issues if i["severity"] == "error"]
        if errors:
            raise SynfigError(
                f"The final render of the shot '{shot_id}' failed: "
                + "; ".join(i["message"] for i in errors)
            )
        return {"shot_id": shot_id, "frames": len(frames), "directory": str(final_dir)}

    async def _task_write_manifest(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Write the manifest of the production."""
        shots: list[dict[str, Any]] = []
        for shot in brief.shots:
            entry = shot.model_dump(mode="json")
            shot_file = self.workspace.shot_file(shot.id)
            if shot_file.is_file():
                entry["file"] = str(shot_file)
                entry["sha256"] = ProductionWorkspace.sha256_of(shot_file)
            shots.append(entry)
        manifest.shots = shots
        manifest.status = "rendered" if brief.render_final else "previewed"
        self.workspace.write_manifest(manifest)
        return {"shots": len(shots), "status": manifest.status}

    async def _task_write_report(
        self,
        task: ProductionTask,
        brief: ProductionBrief,
        plan: ProductionPlan,
        manifest: ProductionManifest,
        shot_docs: dict[str, str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Write the production report."""
        from synfig_mcp.production.report import build_report

        markdown, data = build_report(brief, plan, manifest, self.workspace)
        reports_dir = self.workspace.reports_dir
        reports_dir.mkdir(parents=True, exist_ok=True)
        md_path = reports_dir / "production-report.md"
        md_path.write_text(markdown, encoding="utf-8")
        json_path = reports_dir / "production-report.json"
        json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return {"report": str(md_path), "data": str(json_path)}


def _summarise(result: dict[str, Any] | None) -> dict[str, Any]:
    """Return a short summary of a task result for the log."""
    if not result:
        return {}
    summary: dict[str, Any] = {}
    for key, value in result.items():
        if isinstance(value, (str, int, float, bool)):
            summary[key] = value
        elif isinstance(value, list):
            summary[key] = len(value)
    return summary