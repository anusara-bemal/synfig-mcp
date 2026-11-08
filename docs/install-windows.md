# Windows Installation & Setup Guide

This guide covers installing and configuring `synfig-mcp` on Windows (Windows 10/11 x64), including both pre-built binaries and source compilation.

---

## 1. Prerequisites

- **Python**: 3.12 or 3.14 (64-bit). Verify with `python --version`.
- **FFmpeg**: Required for `render_video` support.
  - Install via Windows Package Manager: `winget install Gyan.FFmpeg`
  - Or via MSYS2: `pacman -S mingw-w64-ucrt-x86_64-ffmpeg`
- **MCP Client**: Claude Desktop, Cursor, or any MCP-compatible environment.

---

## 2. Installing the Python MCP Server

Install `synfig-mcp` into your environment using `pip` or `uv`:

```powershell
pip install synfig-mcp
```

Or install in isolated tool mode with `uv`:

```powershell
uv tool install synfig-mcp
```

Verify the installation:

```powershell
synfig-mcp doctor
```

---

## 3. Synfig Studio Integration

`synfig-mcp` supports two operation modes:
1. **Live UI Control (Recommended)**: Connects to a running Synfig Studio instance via native C++ bridge over local TCP (`127.0.0.1:19991`). Edits appear immediately in the GUI canvas and are recorded on the Studio undo stack.
2. **Headless Engine**: Automatically activated when Synfig Studio is not running. Operates directly on SIF XML files with out-of-process rendering via the standalone `synfig` CLI.

### Option A: Using Pre-built Patched Studio

1. Download the latest `synfigstudio-windows-ucrt64-mcp-*.zip` from GitHub Releases.
2. Extract the archive (e.g. to `C:\SynfigStudio-MCP`).
3. Launch `synfigstudio.exe`. On startup, it writes a secure token to `%USERPROFILE%\.synfig\mcp_token` and listens for local MCP connections on port `19991`.

### Option B: Compiling from Source (MSYS2 UCRT64)

If you wish to compile the native bridge yourself:

1. Install MSYS2 from [msys2.org](https://www.msys2.org/).
2. Open **MSYS2 UCRT64** terminal and run:
   ```bash
   bash bridge/scripts/setup_msys2.sh
   bash bridge/scripts/fetch_synfig.sh
   bash bridge/scripts/apply_patches.sh
   bash bridge/scripts/build_windows_msys2.sh
   ```
   > [!NOTE]
   > `build_windows_msys2.sh` includes an automated fallback for `mingw-w64-ucrt-x86_64-libxml++2.6-2.42.3-5-any.pkg.tar.zst` from the official MSYS2 mirror if omitted by the active repo index, verifying its pinned SHA-256 checksum (`73fbff7c50409c9524fa9cb9a46453d71feea6036195cbb0b810459c5d012175`) before installation to maintain supply-chain integrity.
3. The compiled binary is output to `build_synfig/build_ucrt64/install/bin/synfigstudio.exe`.

---

## 4. Configuring Claude Desktop

Add `synfig-mcp` to your `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synfig": {
      "command": "synfig-mcp",
      "args": []
    }
  }
}
```

If you prefer streamable HTTP transport with token authentication:

```json
{
  "mcpServers": {
    "synfig": {
      "command": "synfig-mcp",
      "args": [
        "--transport", "streamable-http",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--token", "YOUR_SECRET_TOKEN"
      ]
    }
  }
}
```

---

## 5. System Health Check (`synfig-mcp doctor`)

Run `synfig-mcp doctor` at any time to verify system configuration:

```powershell
synfig-mcp doctor
```

Expected output when running:
```text
==================================================
           synfig-mcp System Doctor               
==================================================
[PASS] Synfig Studio Binary: Found on PATH: C:\Program Files\Synfig\bin\synfigstudio.EXE
[PASS] Bridge Connectivity: Bridge TCP socket responding at 127.0.0.1:19991
[PASS] Token File ACL: Owner-only Win32 ACL verified (inheritance disabled): C:\Users\user\.synfig\mcp_token
[PASS] Synfig CLI: Found on PATH: C:\Program Files\Synfig\bin\synfig.EXE
[PASS] FFmpeg: Found on PATH: C:\msys64\ucrt64\bin\ffmpeg.EXE
[PASS] Configuration: Valid (backend=auto, host=127.0.0.1, port=19991)
--------------------------------------------------
Doctor status: OK. synfig-mcp is ready for operation.
```

---

## 7. Install Guide Verification Status

- **Host Environment (Windows 11 AMD64, Python 3.14, MSYS2 UCRT64)**: **VERIFIED**.
  * Native Studio compilation via `bridge/scripts/build_windows_msys2.sh` verified.
  * Live E2E test suite against real `synfigstudio.exe` (`poe live`): 13/13 tests pass.
  * Windows token file ACL restriction (`icacls` / `SetNamedSecurityInfoW` owner-only ACE without inheritance): verified.
- **Clean Windows Profile / Sterile VM without Pre-installed Toolchain**: **UNVERIFIED**.
  * Reason: Standalone sandbox testing was executed on local dev host and GitHub Actions Windows runners (`windows-latest`). An isolated offline Windows VM deployment with zero development prerequisites has not yet been manually audited. Follow Section 3 Option A for standard binary deployment.
