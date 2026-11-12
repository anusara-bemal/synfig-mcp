"""
MCP Resources for synfig-mcp.

Resources are readable documents a client can attach to context without calling
a tool. Each guide topic, scene template and review rubric is exposed both as a
URI template (``synfig://guide/{topic}``) and as its own concrete resource, so
``resources/list`` is populated for clients and automated scanners.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import MCPServer

from synfig_mcp.resources.guides import GUIDE_TOPICS

# Ready-to-use scene_build specifications, one per common starter composition.
TEMPLATES: dict[str, dict[str, Any]] = {
    "bouncing_ball": {
        "name": "Bouncing ball",
        "description": "A ball that arcs across the canvas and squashes on impact.",
        "spec": {
            "doc_id": "doc_0",
            "layers": [
                {
                    "id": "bg",
                    "type": "solid_color",
                    "params": {
                        "color": {"type": "color", "r": 0.06, "g": 0.08, "b": 0.16, "a": 1.0}
                    },
                },
                {
                    "id": "ball",
                    "type": "circle",
                    "params": {
                        "radius": 0.5,
                        "color": {"type": "color", "r": 0.98, "g": 0.72, "b": 0.2, "a": 1.0},
                        "origin": {"type": "vector", "x": -3.5, "y": 2.0},
                    },
                },
            ],
            "waypoints": [
                {
                    "layer": "ball",
                    "param": "origin",
                    "time": "0s",
                    "value": {"type": "vector", "x": -3.5, "y": 2.0},
                },
                {
                    "layer": "ball",
                    "param": "origin",
                    "time": "0.6s",
                    "value": {"type": "vector", "x": -1.5, "y": -1.6},
                },
                {
                    "layer": "ball",
                    "param": "origin",
                    "time": "1.2s",
                    "value": {"type": "vector", "x": 0.5, "y": 1.4},
                },
                {
                    "layer": "ball",
                    "param": "origin",
                    "time": "1.8s",
                    "value": {"type": "vector", "x": 2.5, "y": -1.6},
                },
                {
                    "layer": "ball",
                    "param": "origin",
                    "time": "2.4s",
                    "value": {"type": "vector", "x": 3.5, "y": 2.0},
                },
            ],
        },
    },
    "logo_sting": {
        "name": "Logo sting",
        "description": "A star mark that scales up and fades in over a dark background.",
        "spec": {
            "doc_id": "doc_0",
            "layers": [
                {
                    "id": "bg",
                    "type": "solid_color",
                    "params": {
                        "color": {"type": "color", "r": 0.02, "g": 0.02, "b": 0.05, "a": 1.0}
                    },
                },
                {
                    "id": "mark",
                    "type": "star",
                    "params": {
                        "radius1": 0.4,
                        "radius2": 1.2,
                        "color": {"type": "color", "r": 0.35, "g": 0.85, "b": 0.95, "a": 1.0},
                    },
                },
            ],
            "waypoints": [
                {
                    "layer": "mark",
                    "param": "radius1",
                    "time": "0s",
                    "value": {"type": "real", "value": 0.05},
                },
                {
                    "layer": "mark",
                    "param": "radius1",
                    "time": "1.0s",
                    "value": {"type": "real", "value": 0.4},
                },
                {
                    "layer": "mark",
                    "param": "amount",
                    "time": "0s",
                    "value": {"type": "real", "value": 0.0},
                },
                {
                    "layer": "mark",
                    "param": "amount",
                    "time": "1.0s",
                    "value": {"type": "real", "value": 1.0},
                },
            ],
        },
    },
    "lower_third": {
        "name": "Lower third",
        "description": "A caption bar that slides in over the bottom of the frame.",
        "spec": {
            "doc_id": "doc_0",
            "layers": [
                {
                    "id": "bar",
                    "type": "rectangle",
                    "params": {
                        "color": {"type": "color", "r": 0.1, "g": 0.1, "b": 0.12, "a": 0.85},
                        "point1": {"type": "vector", "x": -4.0, "y": -2.0},
                        "point2": {"type": "vector", "x": 4.0, "y": -2.6},
                    },
                },
                {
                    "id": "accent",
                    "type": "rectangle",
                    "params": {
                        "color": {"type": "color", "r": 0.98, "g": 0.65, "b": 0.15, "a": 1.0},
                        "point1": {"type": "vector", "x": -4.0, "y": -2.0},
                        "point2": {"type": "vector", "x": -3.85, "y": -2.6},
                    },
                },
            ],
            "waypoints": [
                {
                    "layer": "bar",
                    "param": "point1",
                    "time": "0s",
                    "value": {"type": "vector", "x": -4.0, "y": -2.4},
                },
                {
                    "layer": "bar",
                    "param": "point1",
                    "time": "0.5s",
                    "value": {"type": "vector", "x": -4.0, "y": -2.0},
                },
            ],
        },
    },
}


def _index_markdown() -> str:
    """A markdown index of every guide topic, template and rubric."""
    from synfig_mcp.review.rubrics import list_available_rubrics

    lines = ["# Synfig MCP resources", "", "## Guide topics", ""]
    lines += [f"- `synfig://guide/{t}`" for t in sorted(GUIDE_TOPICS)]
    lines += ["", "## Scene templates", ""]
    lines += [
        f"- `synfig://templates/{k}` - {v['description']}" for k, v in sorted(TEMPLATES.items())
    ]
    lines += ["", "## Review rubrics", ""]
    lines += [f"- `synfig://rubrics/{r}`" for r in list_available_rubrics()]
    return "\n".join(lines) + "\n"


def _reader(name: str, value: str) -> Callable[[], str]:
    """Build a named, zero-argument resource reader (static resources take no params)."""

    def read() -> str:
        return value

    read.__name__ = name
    return read


def register_all_resources(mcp: MCPServer) -> None:
    """Register every synfig-mcp resource onto the MCPServer instance."""
    from synfig_mcp.review.rubrics import RUBRICS, get_rubric

    @mcp.resource(
        "synfig://index",
        name="resource_index",
        title="Resource index",
        description="Index of every guide topic, scene template and review rubric.",
        mime_type="text/markdown",
    )
    def resource_index() -> str:
        return _index_markdown()

    @mcp.resource(
        "synfig://guide/{topic}",
        name="guide_topic",
        title="Guide topic",
        description="Guidance on a Synfig concept (overview, declarative_build, characters, ...).",
        mime_type="text/markdown",
    )
    def guide_topic(topic: str) -> str:
        from synfig_mcp.resources.guides import get_guide_content

        return get_guide_content(topic)

    @mcp.resource(
        "synfig://templates/{template}",
        name="scene_template",
        title="Scene template",
        description="A ready-to-use scene_build JSON specification for a starter composition.",
        mime_type="application/json",
    )
    def scene_template(template: str) -> str:
        tpl = TEMPLATES.get(template.lower().strip())
        if tpl is None:
            available = ", ".join(sorted(TEMPLATES))
            return json.dumps(
                {"error": f"Unknown template '{template}'. Available: {available}"}, indent=2
            )
        return json.dumps(tpl["spec"], indent=2)

    @mcp.resource(
        "synfig://rubrics/{style}",
        name="review_rubric",
        title="Review rubric",
        description="Vision critique checklist and rubric for an animation style.",
        mime_type="text/markdown",
    )
    def review_rubric(style: str) -> str:
        return get_rubric(style)

    # Enumerate every guide topic, template and rubric as its own concrete
    # resource so resources/list is populated for clients and scanners.
    for topic in sorted(GUIDE_TOPICS):
        mcp.resource(
            f"synfig://guide/{topic}",
            name=f"guide_{topic}",
            title=f"Guide: {topic}",
            description=f"Synfig MCP guidance on '{topic}'.",
            mime_type="text/markdown",
        )(_reader(f"guide_{topic}", GUIDE_TOPICS[topic]))

    for key, tpl in sorted(TEMPLATES.items()):
        mcp.resource(
            f"synfig://templates/{key}",
            name=f"template_{key}",
            title=f"Template: {tpl['name']}",
            description=tpl["description"],
            mime_type="application/json",
        )(_reader(f"template_{key}", json.dumps(tpl["spec"], indent=2)))

    for style in sorted(RUBRICS):
        mcp.resource(
            f"synfig://rubrics/{style}",
            name=f"rubric_{style}",
            title=f"Rubric: {style}",
            description=f"Vision critique rubric for the '{style}' style.",
            mime_type="text/markdown",
        )(_reader(f"rubric_{style}", RUBRICS[style]))
