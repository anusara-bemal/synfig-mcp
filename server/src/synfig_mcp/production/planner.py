"""
The production planner.

The planner turns a :class:`~synfig_mcp.production.models.ProductionBrief`
into a task graph.  Every task declares what it depends on, so the
orchestrator can execute the graph in dependency order, resume it after an
interruption and report on it.

The graph mirrors how a shot is actually produced:

#. the document is created with the right format,
#. the reusable assets (backgrounds, characters, props) are built once,
#. every shot is laid out, animated, given a camera move and its effects,
#. every shot is validated and previewed,
#. the final renders are produced and the manifests are written.
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.production.models import ProductionBrief, ProductionPlan, ProductionTask


def _task(
    task_id: str,
    kind: str,
    title: str,
    depends_on: list[str] | None = None,
    params: dict[str, Any] | None = None,
    checkpoint: str | None = None,
    critical: bool = False,
) -> ProductionTask:
    """Create one task of the plan."""
    return ProductionTask(
        id=task_id,
        kind=kind,
        title=title,
        depends_on=depends_on or [],
        params=params or {},
        checkpoint=checkpoint,
        critical=critical,
    )


def build_plan(brief: ProductionBrief) -> ProductionPlan:
    """Build the task graph of a production.

    The graph is deterministic: the same brief always produces the same
    tasks in the same order.
    """
    tasks: list[ProductionTask] = []
    tasks.append(
        _task(
            "document",
            "create_document",
            "Create the Synfig document",
            params={
                "width": brief.width,
                "height": brief.height,
                "fps": brief.fps,
                "title": brief.title,
            },
            critical=True,
        )
    )

    for character in brief.characters:
        tasks.append(
            _task(
                f"character:{character.id}",
                "build_character",
                f"Build the character '{character.id}'",
                depends_on=["document"],
                params={"character": character.model_dump()},
            )
        )

    for index, background in enumerate(brief.backgrounds):
        name = str(background.get("name") or background.get("id") or f"background_{index}")
        tasks.append(
            _task(
                f"background:{name}",
                "build_background",
                f"Build the background '{name}'",
                depends_on=["document"],
                params={"background": background},
            )
        )

    for index, prop in enumerate(brief.props):
        name = str(prop.get("name") or prop.get("id") or f"prop_{index}")
        tasks.append(
            _task(
                f"prop:{name}",
                "build_prop",
                f"Build the prop '{name}'",
                depends_on=["document"],
                params={"prop": prop},
            )
        )

    for index, rig in enumerate(brief.rigs):
        name = str(rig.get("name") or rig.get("id") or f"rig_{index}")
        tasks.append(
            _task(
                f"rig:{name}",
                "build_rig",
                f"Build the rig '{name}'",
                depends_on=["document"],
                params={"rig": rig},
            )
        )

    for shot in brief.shots:
        shot_id = shot.id
        layout_deps = ["document"]
        layout_deps.extend(f"character:{cid}" for cid in shot.characters)
        if shot.background:
            layout_deps.append(f"background:{shot.background}")
        layout_id = f"shot:{shot_id}:layout"
        tasks.append(
            _task(
                layout_id,
                "layout_shot",
                f"Lay out the shot '{shot_id}'",
                depends_on=layout_deps,
                params={"shot": shot.model_dump()},
                checkpoint="layout",
                critical=True,
            )
        )
        tasks.append(
            _task(
                f"shot:{shot_id}:camera",
                "camera_shot",
                f"Set up the camera of the shot '{shot_id}'",
                depends_on=[layout_id],
                params={"shot": shot_id},
            )
        )
        tasks.append(
            _task(
                f"shot:{shot_id}:animate",
                "animate_shot",
                f"Animate the shot '{shot_id}'",
                depends_on=[layout_id],
                params={"shot": shot_id},
                checkpoint="animation",
            )
        )
        tasks.append(
            _task(
                f"shot:{shot_id}:fx",
                "fx_shot",
                f"Add the effects of the shot '{shot_id}'",
                depends_on=[f"shot:{shot_id}:animate"],
                params={"shot": shot_id},
            )
        )
        tasks.append(
            _task(
                f"shot:{shot_id}:validate",
                "validate_shot",
                f"Validate the shot '{shot_id}'",
                depends_on=[f"shot:{shot_id}:fx", f"shot:{shot_id}:camera"],
                params={"shot": shot_id},
            )
        )
        preview_id = f"shot:{shot_id}:preview"
        tasks.append(
            _task(
                preview_id,
                "render_preview",
                f"Render the preview of the shot '{shot_id}'",
                depends_on=[f"shot:{shot_id}:validate"],
                params={"shot": shot_id},
            )
        )
        if brief.render_final:
            tasks.append(
                _task(
                    f"shot:{shot_id}:final",
                    "render_final",
                    f"Render the final frames of the shot '{shot_id}'",
                    depends_on=[preview_id],
                    params={"shot": shot_id},
                )
            )

    shot_ends = [
        t.id
        for t in tasks
        if t.kind in ("render_preview", "render_final")
    ]
    tasks.append(
        _task(
            "manifest",
            "write_manifest",
            "Write the production manifest",
            depends_on=shot_ends,
        )
    )
    tasks.append(
        _task(
            "report",
            "write_report",
            "Write the production report",
            depends_on=["manifest"],
        )
    )
    return ProductionPlan(project=brief.project_slug, tasks=tasks)


def order_tasks(plan: ProductionPlan) -> list[ProductionTask]:
    """Return the tasks of a plan in dependency order.

    The order is stable and independent of the order the tasks were declared
    in, so a resumed run continues exactly where it stopped.
    """
    ordered: list[ProductionTask] = []
    done: set[str] = set()
    remaining = list(plan.tasks)
    while remaining:
        ready = [t for t in remaining if all(dep in done for dep in t.depends_on)]
        if not ready:
            ordered.extend(remaining)
            break
        for task in ready:
            ordered.append(task)
            done.add(task.id)
            remaining.remove(task)
    return ordered