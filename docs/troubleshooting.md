# Troubleshooting Synfig MCP

## Common Issues and Solutions

### 1. `Synfig binary not found` or `synfig_doctor` reports binary missing

**Cause**: The `synfig` CLI binary is not in your system `PATH` and was not found at standard installation locations.

**Solution**:
1. Verify Synfig Studio is installed on your machine.
2. Find the exact path to `synfig` (or `synfig.exe` on Windows).
   - Windows default: `C:\Program Files\Synfig\bin\synfig.exe`
   - Linux: `/usr/bin/synfig`
   - macOS: `/Applications/SynfigStudio.app/Contents/Resources/bin/synfig`
3. Set the `SYNFIG_BIN` environment variable in your client configuration or `.env`:
   ```bash
   SYNFIG_BIN="C:\Program Files\Synfig\bin\synfig.exe"
   ```

---

### 2. `WorkspaceError: Output path is outside the configured workspace`

**Cause**: `synfig-mcp` enforces a security jail ensuring all document reads and writes occur inside the designated workspace.

**Solution**:
- Provide relative paths or paths residing within `SYNFIG_MCP_WORKSPACE`.
- Configure `SYNFIG_MCP_WORKSPACE` to your intended project directory:
  ```bash
  export SYNFIG_MCP_WORKSPACE="/home/user/animations"
  ```

---

### 3. `UnsupportedTargetError: Render target 'lottie' is not supported by Synfig`

**Cause**: Synfig Studio's CLI natively renders raster formats (`png`, `jpeg`, `bmp`), animations (`gif`), and video streams via `ffmpeg`. It does not support Lottie JSON or direct vector SIF flattening via CLI.

**Solution**:
- To render vector animations for web or preview, render to `gif` or `ffmpeg` (MP4/WebM).
- To produce sprite sequences, use `target="png"` or `target="png-spritesheet"`.

---

### 4. `LimitExceededError: Resolution exceeds limit` or `Frame count exceeds limit`

**Cause**: The requested render dimensions or duration exceed the configured safety bounds.

**Solution**:
Adjust safety limits via environment variables in your server configuration:
- `SYNFIG_MCP_MAX_WIDTH`: Maximum canvas width (default: 8192)
- `SYNFIG_MCP_MAX_HEIGHT`: Maximum canvas height (default: 8192)
- `SYNFIG_MCP_MAX_FRAMES`: Maximum renderable frames per job (default: 10000)
- `SYNFIG_MCP_RENDER_TIMEOUT`: Seconds before terminating a render job (default: 300)

---

### 5. `JSONDecodeError` or MCP Protocol Transport Errors

**Cause**: Other tools or libraries printed debug messages to standard output (`stdout`), corrupting the MCP JSON-RPC protocol stream.

**Solution**:
- `synfig-mcp` strictly routes all logging to standard error (`stderr`).
- Verify custom extensions or wrappers do not write to `sys.stdout`.
- Set `SYNFIG_MCP_LOG_LEVEL=DEBUG` to inspect detailed diagnostic logs on `stderr`.
