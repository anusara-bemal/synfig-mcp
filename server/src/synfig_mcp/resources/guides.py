"""
Resource guides and topic documentation offloaded from tool docstrings.
Accessible via MCP resources (synfig://guide/{topic}) and the synfig_help tool.
"""

GUIDE_TOPICS: dict[str, str] = {
    "overview": """# Synfig MCP Overview & Best Practices

## Current document rule (like Blender's active scene)
- Always work in the **currently open/selected document** by default. Every tool's `doc_id` defaults to `doc_0`, which the bridge resolves to the Studio window you have selected.
- Never call `doc_new` or `doc_open` unless the user explicitly asked for a new file or a specific file to open. Creating a document silently discards the document the user is looking at.
- Before building, confirm the target with `doc_list` and `scene_summary`; pass the returned `doc_id` explicitly on every subsequent call.
- If no document is open (or `doc_list` is empty), tell the user instead of creating one unasked.

## Studio-Grade Workflow
1. Use declarative `scene_build` for assembling layers, parameters, and keyframes in a single atomic call instead of sequential round trips.
2. Verify visual results using `render_frame` (or `review_frame`) at low resolution (320x240) for fast iteration.
3. Switch tool profiles via `SYNFIG_MCP_PROFILE` to keep context token usage minimal.
4. All live edits in Synfig Studio are undoable via standard `Ctrl+Z` (mapped to `history_undo`).
""",
    "profiles": """# Synfig MCP Tool Profiles

Control tool footprint using environment variable `SYNFIG_MCP_PROFILE`:
- `core` (default): Minimal set for document lifecycle, declarative build, inspection, undo (< 3,000 tokens).
- `anim`: Waypoint and keyframe animation tools, time controls, interpolation modes.
- `fx`: Layer filters, composites, parameter conversions, and recipes.
- `rig`: Cut-out character assembly, bone skeletons, valuenode exports.
- `assets`: Search and import openly licensed artwork (Openverse, Wikimedia).
- `review`: Frame critiques, SSIM diff heatmaps, contact sheets, safety metrics.
- `all`: Unrestricted suite containing all 52+ tools.
""",
    "declarative_build": """# Declarative Scene Building (scene_build)

`scene_build` accepts a single structured JSON specification and applies it atomically:
- All layers are created in sequence.
- Parameters and colors are applied.
- Keyframe waypoints are registered.
- Grouping containers are assembled.
- The entire operation executes as **ONE single undo step** in Synfig Studio's history.

## Example Spec:
```json
{
  "doc_id": "doc_0",
  "layers": [
    {
      "id": "Background",
      "type": "solid_color",
      "params": {"color": {"type": "color", "value": {"r": 0.1, "g": 0.1, "b": 0.2, "a": 1.0}}}
    },
    {
      "id": "Orb",
      "type": "circle",
      "params": {
        "radius": {"type": "real", "value": 1.5},
        "color": {"type": "color", "value": {"r": 1.0, "g": 0.7, "b": 0.1, "a": 1.0}},
        "origin": {"type": "vector", "value": {"x": -3.0, "y": 0.0}}
      },
      "waypoints": [
        {"param": "origin", "time": 0.0, "value": {"type": "vector", "value": {"x": -3.0, "y": 0.0}}, "interpolation": "clamped"},
        {"param": "origin", "time": 2.0, "value": {"type": "vector", "value": {"x": 3.0, "y": 0.0}}, "interpolation": "clamped"}
      ]
    }
  ]
}
```
""",
    "animation": """# Synfig MCP Animation System

## Waypoint Interpolation Modes
- `clamped`: Smooth cubic spline avoiding overshoot (recommended default).
- `linear`: Constant rate of change between waypoints.
- `halt`: Ease-in and ease-out with zero velocity at waypoints.
- `constant`: Step function hold until next waypoint.

## Parameter Values
Parameters take typed dictionaries:
- `real`: `{"type": "real", "value": 1.5}`
- `vector`: `{"type": "vector", "value": {"x": 0.0, "y": 1.0}}`
- `color`: `{"type": "color", "value": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}}`
- `angle`: `{"type": "angle", "value": 45.0}`
- `bool`: `{"type": "bool", "value": true}`
- `string`: `{"type": "string", "value": "text"}`
""",
    "review": """# Visual Review Loop & Token Efficiency

## Adaptive Image Preview
- For quick alignment and critique: render at `320x240` (only ~103 Claude tokens / ~258 Gemini tokens).
- For multi-frame animation checks: use `render_contact_sheet` to composite multiple frames into one compact grid.
- Objective metrics flag luminance clipping, safe-area boundary violations, and strobe hazards without consuming vision tokens.
""",
}


def get_guide_content(topic: str) -> str:
    """Retrieve guide content for topic, falling back to overview and list of topics."""
    t = topic.lower().strip()
    if t in GUIDE_TOPICS:
        return GUIDE_TOPICS[t]
    available = ", ".join(sorted(GUIDE_TOPICS.keys()))
    return (
        f"# Topic '{topic}' not found\n\n"
        f"Available guide topics: {available}.\n\n"
        f"Run `synfig_help('overview')` for general guidance."
    )
