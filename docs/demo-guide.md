# Demo & Claude Desktop Integration Guide

This guide details how to configure Claude Desktop (or Cursor / Claude Code) with `synfig-mcp` and provides a step-by-step prompt sequence to record a demo GIF showing live animation and undo.

---

## 1. Claude Desktop Configuration

Add `synfig-mcp` to your Claude Desktop configuration file:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Stdio Transport Configuration (Recommended)

```json
{
  "mcpServers": {
    "synfig": {
      "command": "python",
      "args": [
        "-m",
        "synfig_mcp.cli",
        "serve",
        "--mode",
        "auto"
      ],
      "env": {
        "SYNFIG_WORKSPACE_ROOTS": "D:/Projects/Animations;C:/Users/User/Videos"
      }
    }
  }
}
```

### Streamable HTTP Transport Configuration (Remote or Containerized)

If hosting `synfig-mcp` in a headless rendering server or Docker container:

```json
{
  "mcpServers": {
    "synfig-http": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_SECURE_AUTH_TOKEN"
      }
    }
  }
}
```

---

## 2. Interactive Demo Walkthrough (For Recording Demo GIF)

To record a compelling 30-to-60 second demo GIF showing AI co-piloting Synfig Studio:

### Step 1: Launch Synfig Studio
Launch the patched Synfig Studio. The MCP bridge will start automatically on `127.0.0.1:19998` and write the session token to disk.

### Step 2: Prompt Sequence for Claude Desktop

#### Prompt 1: Initial Health Check & Scene Setup
> *"Check if Synfig Studio is connected. Then create a new 1920x1080 animation project at 24 fps with a 3-second duration."*

**What happens**: Claude calls `health_check` (verifies LiveBackend is active), then calls `doc_new` and `doc_set_time_range(start_time=0.0, end_time=3.0, fps=24.0)`. Synfig Studio visually creates a new document tab.

#### Prompt 2: Vector Art Creation
> *"Draw a red bouncing ball in the center with a radius of 1.5 units, feathered by 0.1."*

**What happens**: Claude calls `layer_add(layer_type="circle", params={"color": [1.0, 0.0, 0.0, 1.0], "radius": 1.5, "origin": [0.0, 0.0], "feather": 0.1})`. The vector circle instantly appears on the Studio canvas.

#### Prompt 3: Animation with Waypoints
> *"Animate the ball bouncing: start at origin [0, -3] at t=0s, peak at [0, 2] at t=1.5s with clamped interpolation, and land at [0, -3] at t=3.0s."*

**What happens**: Claude calls `anim_animate_param(layer_id="...", param_name="origin", waypoints=[{"time": 0.0, "value": [0, -3]}, {"time": 1.5, "value": [0, 2]}, {"time": 3.0, "value": [0, -3]}])`. In Synfig Studio, waypoints appear on the timeline in a single atomic undo step.

#### Prompt 4: Real-Time Preview
> *"Render preview frames at 0s, 1.5s, and 3.0s and show them to me."*

**What happens**: Claude calls `render_frame` (in-process via the bridge, returning in ~15 ms per frame).

#### Prompt 5: Undo Demonstration
> *"I changed my mind about the trajectory. Undo the bounce animation."*

**What happens**: Claude calls `history_undo()`. Because of `synfigapp::Action::PassiveGrouper`, the entire animation trajectory is undone in one single step! Studio returns to the pre-animated state, completely synchronized with manual `Ctrl+Z`.

---

## 3. Recording Tips

- Use [ScreenToGif](https://www.screentogif.com/) (Windows) or [Gifski](https://gif.ski/) to capture the side-by-side view (Claude Desktop on the left, Synfig Studio viewport and timeline on the right).
- Set canvas preview background to transparent or dark grid for high visual contrast.
- Highlight the instant feedback: notice how in-process preview rendering occurs in ~15ms without UI freezing.
