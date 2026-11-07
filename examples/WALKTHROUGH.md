# synfig-mcp Walkthrough & Integration Guide

`synfig-mcp` connects Claude Desktop, Claude Code, Cursor, and VS Code to **Synfig Studio live** (or to the headless pure-Python SIF engine when Studio is not running).

---

## 1. Claude Desktop Setup

Add `synfig-mcp` to your Claude Desktop configuration file:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS / Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "synfig": {
      "command": "python",
      "args": ["-m", "synfig_mcp.server"],
      "cwd": "D:\\Projects\\Github\\synfig mcp\\server",
      "env": {
        "BACKEND_MODE": "auto",
        "BRIDGE_HOST": "127.0.0.1",
        "BRIDGE_PORT": "19998"
      }
    }
  }
}
```

> **Note**: In `auto` mode, the server probes `127.0.0.1:19998`. If your patched Synfig Studio is running, it connects instantly to the **LiveBackend**. If Studio is closed, it seamlessly uses the **HeadlessBackend** (pure-Python XML DOM + `synfig.exe` CLI).

---

## 2. Sample Prompt Walkthrough: "Bouncing Ball Live in Studio"

Open your patched Synfig Studio (`synfigstudio.exe`), then paste this prompt into Claude:

```
Create a 3-second 1080p animation at 24fps in Synfig Studio live:
1. Add a dark grey SolidColor background.
2. Add a bright cyan Circle layer at the top of the canvas (radius: 1.5).
3. At time 0.0s, set origin to (0.0, 3.0). Add a keyframe 'Top'.
4. At time 0.75s, set origin to (0.0, -2.5). Add a keyframe 'Bounce'.
5. At time 1.5s, set origin to (0.0, 2.0). Add a keyframe 'Peak 2'.
6. At time 2.25s, set origin to (0.0, -2.5). Add a keyframe 'Bounce 2'.
7. At time 3.0s, set origin to (0.0, -1.0). Add a keyframe 'Rest'.
Render a preview PNG frame of the bounce at time 0.75s.
```

### What happens under the hood:
1. **`health_check()`**: Claude verifies `backend: "live"` and `studio_running: true`.
2. **`doc_new(width=1920, height=1080, fps=24)`**: Creates the document in Studio's document manager.
3. **`layer_add(layer_type="solid_color", ...)`**: Studio's GTK main thread executes `synfigapp::Action::LayerAdd` wrapped in a `PassiveGrouper("mcp: layer.add")`. Redraw occurs instantly in Studio.
4. **`layer_add(layer_type="circle", ...)`**: Adds the cyan circle on top.
5. **`anim_time_set` + `param_set` + `anim_keyframe_add`**: Keys the ball positions across the timeline.
6. **Undo verification**: Press **Ctrl+Z** in Synfig Studio — each MCP tool call is cleanly undone one step at a time! Manual edits and AI edits mix with full history consistency.
7. **`render_frame(time=0.75)`**: Renders a high-resolution snapshot of the bounce moment.
