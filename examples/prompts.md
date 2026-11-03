# Sample Natural Language Prompts for Synfig MCP

Here are sample prompts you can give to an LLM assistant (such as Claude Desktop, Cursor, or Claude Code) connected to `synfig-mcp`.

---

### 1. Diagnosing Setup
> "Check my Synfig Studio installation using `synfig_doctor` and tell me what render targets are available."

---

### 2. Basic Scene Setup
> "Create a 1920x1080 animation project at 30 fps called 'sunset_scene' lasting 4 seconds. Add a linear gradient background from orange to deep purple, and add a solid ground polygon at the bottom."

---

### 3. Vector Shape Construction
> "Open project 'sunset_scene' and add a bright yellow glowing circle in the upper middle area to represent the sun. Add a blur filter with a blur size of 0.25 units."

---

### 4. Keyframe & Waypoint Animation
> "Animate the sun layer's 'origin' parameter: start at `[0, 2]` at time `0f`, set a waypoint at `2s` descending to `[0, 0]`, and another at `4s` sinking below the horizon at `[0, -1.5]`. Use 'clamped' interpolation for smooth deceleration."

---

### 5. Skeleton Rigging
> "Create a simple two-bone arm skeleton in project 'character'. Create the parent bone 'UpperArm' starting at `[0, 0]` with length `2.0` and angle `90`, then create a child bone 'ForeArm' attached to it. Bind the arm shape layers to the skeleton."

---

### 6. Exporting and Linking Parameters
> "Export the color parameter of the 'LogoText' layer with name 'BrandColor'. Then link the border outline's color parameter to this exported value so changing one updates both."

---

### 7. Frame & Animation Rendering
> "Render a preview frame at time `2s` to check how the lighting looks, then render the entire 4-second animation to a looping GIF file named 'sunset.gif'."

---

### 8. Batch Atomic Updates & Rollbacks
> "Use `batch_operations` to atomically add a vignette layer, a color correction layer boosting saturation by 1.2, and adjust canvas end-time to 6 seconds. If any step fails, roll back."
