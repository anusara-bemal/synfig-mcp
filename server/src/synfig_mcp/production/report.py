"""
The production report.

The report is the human readable summary of a production run: what was
planned, what was built, what was validated and what is still open.  It is
written next to the manifest of the production so it can be archived with
it.
"""

from __future__ import annotations

from typing import Any

from synfig_mcp.production.models import (
    ProductionBrief,
    ProductionManifest,
    ProductionPlan,
    TaskStatus,
)
from synfig_mcp.production.workspace import ProductionWorkspace


def build_report(
    brief: ProductionBrief,
    plan: ProductionPlan,
    manifest: ProductionManifest,
    workspace: ProductionWorkspace,
) -> tuple[str, dict[str, Any]]:
    """Build the production report.

    Returns the Markdown text and the machine readable data of the report.
    """
    tasks = [
        {
            "id": t.id,
            "kind": t.kind,
            "title": t.title,
            "status": t.status.value,
            "attempts": t.attempts,
            "error": t.error,
            "depends_on": list(t.depends_on),
        }
        for t in plan.tasks
    ]
    task_counts: dict[str, int] = {}
    for task in tasks:
        task_counts[task["status"]] = task_counts.get(task["status"], 0) + 1

    shots = [
        {
            "id": shot.id,
            "duration": shot.duration,
            "file": str(workspace.shot_file(shot.id)),
        }
        for shot in brief.shots
    ]
    failures = [t for t in plan.tasks if t.status == TaskStatus.FAILED]
    open_tasks = [
        t for t in plan.tasks if t.status in (TaskStatus.PENDING, TaskStatus.AWAITING_APPROVAL)
    ]

    data: dict[str, Any] = {
        "status": manifest.status,
        "project": brief.project_slug,
        "title": brief.title,
        "logline": brief.logline,
        "format": {"width": brief.width, "height": brief.height, "fps": brief.fps},
        "tasks": tasks,
        "task_counts": task_counts,
        "shots": shots,
        "assets": [a.model_dump(mode="json") for a in manifest.assets],
        "characters": manifest.characters,
        "backgrounds": manifest.backgrounds,
        "versions": [v.model_dump(mode="json") for v in manifest.versions],
        "failures": [{"id": t.id, "error": t.error} for t in failures],
        "open_tasks": [t.id for t in open_tasks],
        "manifest": str(workspace.manifest_path),
        "shots_directory": str(workspace.shots_dir),
        "renders_directory": str(workspace.renders_dir),
    }

    lines: list[str] = [
        f"# Production report - {brief.title}",
        "",
        f"* **Project**: `{brief.project_slug}`",
        f"* **Status**: {manifest.status}",
        f"* **Format**: {brief.width}x{brief.height} @ {brief.fps} fps",
    ]
    if brief.logline:
        lines.append(f"* **Logline**: {brief.logline}")
    lines.extend(["", "## Tasks", "", "| Task | Kind | Status | Attempts | Error |", "| --- | --- | --- | --- | --- |"])
    for task in tasks:
        lines.append(
            f"| `{task['id']}` | {task['kind']} | {task['status']} | {task['attempts']} | "
            f"{task['error'] or '-'} |"
        )

    lines.extend(["", "## Shots", "", "| Shot | Duration | File |", "| --- | --- | --- |"])
    for shot in shots:
        lines.append(f"| `{shot['id']}` | {shot['duration']}s | `{shot['file']}` |")

    if manifest.assets:
        lines.extend(["", "## Assets", ""])
        for asset in manifest.assets:
            lines.append(f"* `{asset.id}`: {asset.title or asset.kind} ({asset.license_code})")

    if failures:
        lines.extend(["", "## Failures", ""])
        for task in failures:
            lines.append(f"* `{task.id}`: {task.error}")

    if manifest.versions:
        lines.extend(
            ["", "## Versions", "", "| Label | Recorded | SHA-256 | File |", "| --- | --- | --- | --- |"]
        )
        for version in manifest.versions:
            lines.append(
                f"| {version.label} | {version.recorded_at} | `{version.sha256[:16]}` | "
                f"`{version.path}` |"
            )

    return "\n".join(lines) + "\n", data