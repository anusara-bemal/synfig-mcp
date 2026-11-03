# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""MCP prompts: guided workflows for common Synfig tasks."""

from __future__ import annotations


def register(server, ctx) -> None:  # type: ignore[no-untyped-def]
    @server.prompt(title="Create a logo animation")
    def create_logo_animation(logo_description: str = "a simple geometric mark") -> str:
        return f"""You are an animation director working in Synfig Studio via the synfig-mcp tools.
Create a logo animation for: {logo_description}

Plan before acting, then use the tools:
1. create_project(width=512, height=512, fps=24, end_time="3s 0f", name="logo-reveal")
2. Build the logo from primitives (add_circle / add_rectangle / add_star / add_polygon / add_outline / add_advanced_outline / add_region).
   Keep each part on its own layer and give them meaningful names (rename_layer).
3. Animate with animate_param (prefer TCB/clamped interpolation for smooth moves; constant for snaps).
   Typical beats: fade/scale in (0-12f), hold with subtle drift, accent pulse, settle.
4. Add a background (add_solid_color) and optional text (add_text) with the brand name.
5. Add keyframes with add_keyframe for: intro, reveal, hold, outro.
6. validate_project, then render_frame at 0f/12f/72f to check, then render_animation target=gif.
7. If anything fails, fix it with the error's hint (never edit XML by hand unless asked).
Keep colors to a 2-3 color palette, motion ease-out everywhere, and total length under 3 seconds."""

    @server.prompt(title="Create an explainer scene")
    def create_explainer_scene(topic: str = "how photosynthesis works") -> str:
        return f"""You are setting up an explainer-style 2D scene in Synfig Studio via synfig-mcp.
Topic: {topic}

1. create_project(width=1280, height=720, fps=24, end_time="12s 0f", name="explainer").
2. Storyboard the scene into 3 acts; create one background per act (solid colors or gradients via add_gradient).
3. Use simple characters built from primitives: circle heads, region bodies, outline limbs — grouped with group_layers, named via rename_layer.
4. Animate reveals with animate_param (position, radius, opacity); use staggered waypoint timing.
5. Add captions with add_text; keep sentences short (max 8 words per caption).
6. Add keyframes at act boundaries with add_keyframe; use list_keyframes to review pacing.
7. validate_project → render_frame at the act boundaries → fix issues → render_animation(target=gif or ffmpeg).
Rules: no more than 12 layers per act; everything must validate; prefer subtle motion over spectacle."""

    @server.prompt(title="Rig a character (skeleton)")
    def rig_character(character_description: str = "a simple stick figure") -> str:
        return f"""You are rigging a 2D character in Synfig Studio via synfig-mcp.
Character: {character_description}

1. Open/create the project; identify the character's outline/region layers (list_layers).
2. Create bones with create_bone for each major joint chain (spine, upper/lower arm, upper/lower leg);
   parent child bones to parents with set_bone_param(param="parent").
3. Bind vertices to bones with bind_skeleton (pass the layer and the param, e.g. origin, and the bone list with weights).
4. Add bone influence by editing weights via set_bone_param if needed.
5. Document the rig: list_bones to verify names/hierarchy; set_bone_param to adjust origin/angle/length.
6. Animate test poses: use animate_param on bone origin/angle params to prove the rig deforms.
7. validate_project and render_frame to verify visually.
Note: Synfig cannot round-trip a skeleton layer's bones parameter in .sif — bones are stored as exported
value nodes; keep names simple and Studio will re-save the rig correctly."""

    @server.prompt(title="Create a looping GIF")
    def loop_gif(subject: str = "a spinning gear") -> str:
        return f"""You are creating a seamlessly looping GIF in Synfig Studio via synfig-mcp.
Subject: {subject}

1. create_project(width=512, height=512, fps=24, end_time="2s 0f", name="loop").
2. Design the loop so frame N matches frame 0 exactly (position, angle, scale, color).
3. Animate with animate_param using linear or clamped interpolation; verify with list_keyframes that motion returns to the start value.
4. Use constant interpolation for mechanical steps; TCB for organic motion.
5. Add motion blur sparingly (add_motion_blur) — GIFs band easily.
6. validate_project → render_frame at 0f and 47f; they must look identical.
7. render_animation(target=gif, width=512, height=512) and check the file size;
   if too large, reduce colors/width or shorten to 24 frames.
Rules: loop point must be exact; no gradients that drift; test at 0f vs last frame."""

    @server.prompt(title="Fix a broken project")
    def fix_broken_project(path: str = "project.sif") -> str:
        return f"""You are a Synfig repair specialist working via synfig-mcp.
File to fix: {path}

1. synfig_doctor — confirm the binary and workspace are OK.
2. open_project(path) — if it fails, read the error: it names the layer/element and line when possible.
3. validate_project(path=...) — list every error/warning with codes and hints.
4. Fix common failures in order:
   - malformed XML → identify the tag/attribute from the message; use save_project_as to write a repaired copy
   - unknown layer types → check list_layer_types; either the build lacks the module or the type is mistyped (hint included)
   - dangling references (use=":Missing") → unlink_params or re-create the missing defs entry, or delete the broken layer
   - oversize canvas/frame counts → reduce via set_canvas_properties or render fewer frames
5. After each fix, re-run validate_project; only stop when valid=true or the remaining issues are warnings.
6. save_project_as with backup=true; never overwrite the original until the repaired copy validates.
Never guess at Synfig internals; verify every fix with validate_project and a test render_frame."""
