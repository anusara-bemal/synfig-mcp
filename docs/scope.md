# Project Scope & Intellectual Property Policy

`synfig-mcp` is a production-oriented Model Context Protocol (MCP) server that empowers Large Language Models and AI coding assistants to design, rig, animate, composite, review, and render 2D animations using Synfig Studio and headless CLI pipelines.

This document sets out the explicit, honest scope of what `synfig-mcp` achieves, what is intentionally out-of-scope, and our strict intellectual property and licensing commitments.

---

## 1. Achievable and Promised Capabilities

`synfig-mcp` is designed for precision vector animation, motion graphics, compositing, and rigged character workflows:

- **Declarative Scene Construction**: Atomic, single-undo-step construction of complex multi-layer scenes, hierarchies, waypoints, keyframes, and render targets via compact JSON specs (`scene_build`).
- **Effect-Driven Scenes & Motion Graphics**: Composable anime and cinematographic visual effects stacks (speed lines, impact frames, energy auras, radial blur bursts, chromatic aberration, halftones, film grain, whip pans) built entirely from native Synfig layers.
- **Camera Work & Multiplane Parallax**: Multi-depth camera rigs with pan, tilt, zoom, and automated camera shake.
- **Compositing & Color Grading**: Multi-layer blend modes, color correction matrices, cel-shading stacks, rim lighting, and vignette overlays.
- **Rigged Cut-Out Characters**: Cut-out character skeletons with automated bone hierarchies, forward/inverse kinematic bone structures, layered anatomical part bindings (head, torso, limbs), pose presets (`idle`, `walk`, `run`, `punch`, `jump`), and facial swap timing.
- **Storyboards & Animatics**: Multi-shot screenplay-to-animatic pipelines organizing shots as independent canvas groups with configured frame durations and transition markers.
- **Closed Visual Review Loop**: "Render -> Critique -> Fix" visual verification using client-side vision models paired with objective image analytics (safe-area detection, luminance clipping, photosensitivity/strobe warnings, SSIM motion tracking, dominant palette extraction, diff heatmaps).
- **Hardened Licensed Asset Pipeline**: Safe internet asset search and download (Openverse API, Wikimedia Commons) with DNS-resolved SSRF protection, SVG DOM sanitization, raster magic-byte validation, and automated attribution tracking (`ATTRIBUTION.md`).

---

## 2. Explicit Non-Goals & Limitations

To maintain honesty and realistic expectations, the following are explicitly **out of scope** and **not promised**:

- **No Magic Text-to-Hand-Drawn Anime**:
  `synfig-mcp` does **not** generate high-end, hand-drawn frame-by-frame sakuga anime from a single prompt. Output fidelity depends on input art, vector geometry, rigging, and parameter choreography. Hand-drawn 24fps character animation requires raster painting or specialized diffusion tools; `synfig-mcp` operates on vector geometry, parameters, and cut-out hierarchies.
- **No Direct Raster Inpainting / Generative Diffusion**:
  `synfig-mcp` does not host or execute raster diffusion models (e.g., Stable Diffusion) within the server. It orchestrates Synfig's native layer graph and Cairo renderer.
- **No External Vision Model Calls from the Server**:
  The server does not call external vision APIs. Visual critiques are performed by the **client LLM** inspecting returned previews, supported by the server's objective mathematical metrics.

---

## 3. Strict Intellectual Property & Anti-Piracy Policy

`synfig-mcp` enforces a zero-tolerance IP policy across all documentation, code, examples, style presets, and asset search adapters:

### Hard Rules:
1. **No Copyrighted Franchise Characters or Assets**:
   The repository does **not** ship, reproduce, or auto-fetch any copyrighted characters, logos, key art, backgrounds, or animation frames from named franchises (e.g., no Pokémon, Dragon Ball, Naruto, Studio Ghibli, Disney, or Marvel assets).
2. **Generic, Descriptive Style Presets**:
   Visual style presets are defined strictly by neutral aesthetic traits (color palette, contrast curve, film grain, line weight, hold timing, effect stack). All presets use neutral descriptive identifiers:
   - `shonen_action`: High-contrast, dynamic speed lines, saturated accents, punchy keyframe holds on threes.
   - `dark_fantasy`: Desaturated moody palette, rim lighting, atmospheric grain, muted tones.
   - `supernatural_noir`: Monochromatic base, stark black clipping, selective cyan/amber spot lighting, subtle halftones.
   - `cyber_mecha`: Sharp neon accents, chromatic aberration, geometric grid lines, hard digital grain.
   - `retro_anime`: Warm paper tint, softened contrast, subtle chromatic aberration, 24fps on twos timing.
3. **No Web-Scraping of Unsanctioned Sources**:
   The asset pipeline interacts exclusively with public APIs that provide explicit open licensing metadata (Openverse, Wikimedia Commons). It strictly forbids scraping fan-art galleries, anime wikis, or screenshot repositories.
4. **Mandatory Rights Declarations on Local Imports**:
   When importing local assets, callers must explicitly declare rights in `{"own", "licensed", "cc0", "public-domain"}`. These declarations are permanently recorded in `assets/manifest.json`.
5. **License Enforcement**:
   - `cc0` and `pdm` are allowed unconditionally.
   - `by` and `by-sa` require explicit user opt-in and auto-generate attribution in `ATTRIBUTION.md`.
   - `nd` (NoDerivatives) is blocked by default because animation pipelines transform assets.
   - `nc` (NonCommercial) is blocked when projects are marked commercial.
   - Adult/mature-flagged assets are filtered out automatically.
