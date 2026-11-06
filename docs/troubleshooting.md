# Troubleshooting Guide

Common issues and resolutions when running or building `synfig-mcp`.

---

## 1. Connection Refused on Bridge Port 19998

- **Cause**: Synfig Studio is not running, or was started without the native bridge patch.
- **Fix**: Run `synfigstudio` from `build_synfig/build_ucrt64/install/bin/synfigstudio.exe`, or configure `backend_mode = "headless"` in `synfig_mcp.config` to use offline processing.

---

## 2. MSYS2 Shell /etc/profile Abort

- **Cause**: On Windows systems without a default printer configured in the registry, `/etc/profile` returns exit code 1 on line `read -r PRINTER`.
- **Fix**: In your shell script, invoke `. /etc/profile || true` before enabling `set -e`.

---

## 3. Stdout Pollution in MCP Clients

- **Cause**: A library or debug print wrote to `sys.stdout`, corrupting JSON-RPC framing in stdio transport mode.
- **Fix**: All logging in `synfig_mcp` must use `structlog` writing strictly to `sys.stderr`.
