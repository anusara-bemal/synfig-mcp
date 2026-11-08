# Troubleshooting Guide

Common issues, root causes, and verified resolutions encountered when building, running, and testing `synfig-mcp` on Windows and Linux.

---

## 1. Connection Refused on Bridge Port 19991

- **Cause**: Synfig Studio is not running, or was started without the native bridge patch compiled into the binary.
- **Fix**:
  1. Launch the patched `synfigstudio.exe` (found in `build_synfig/build_ucrt64/install/bin/synfigstudio.exe` or pre-built releases).
  2. Run `synfig-mcp doctor` to verify TCP socket connectivity and configuration.
  3. Alternatively, if no GUI is needed, set `SYNFIG_MCP_BACKEND=headless` to operate via pure-Python SIF DOM manipulation with standalone CLI rendering.

---

## 2. MSYS2 Shell `/etc/profile` Abort (Exit Code 1)

- **Cause**: On Windows systems without a default printer configured in the registry, `/etc/profile` returns exit code 1 when attempting to read the printer configuration.
- **Fix**: In MSYS2 build scripts, invoke `. /etc/profile || true` before enabling `set -e`:
  ```bash
  export MSYSTEM=UCRT64
  . /etc/profile || true
  set -e
  ```

---

## 3. Stdout Pollution in MCP Clients (JSON-RPC Protocol Parse Errors)

- **Cause**: A Python library or `print()` statement wrote unformatted text to standard output, corrupting JSON-RPC framing when running under `stdio` transport.
- **Fix**:
  - All logging in `synfig_mcp` uses `structlog` directing strictly to `sys.stderr`.
  - When writing MCP server tools or scripts, never call `print()` without redirecting to `file=sys.stderr`.

---

## 4. Keyframe Interference with Waypoint Interpolation

- **Cause**: When a keyframe exists on the Synfig timeline (e.g. at 1.5s), Synfig's Keyframe engine automatically locks the value at that point to its current static value (e.g., `(0, 0)`), preventing linear interpolation between waypoints placed before and after that keyframe.
- **Fix**:
  - Clear unnecessary keyframes via `keyframe.remove` or `anim.keyframe_delete` before calculating interpolated waypoint motions across a time span.
  - Reset the timeline cursor to `0.0s` after testing keyframe additions.

---

## 5. `ValueDescConvert` Action Readiness Failure ("Missing time")

- **Cause**: Calling `synfigapp::Action::create("ValueDescConvert")` requires setting the `time` parameter (`action->set_param("time", cur_time)`). Without it, `action->is_ready()` returns `false` and Synfig logs `error: Missing time`, resulting in a request timeout.
- **Fix**: Ensure `action->set_param("time", cur_time)` is always passed when converting a ValueNode on an active canvas.

---

## 6. Windows NTFS File Permissions (`icacls` vs `chmod`)

- **Cause**: POSIX `chmod 600` on Windows Python does not modify NTFS Access Control Lists (ACLs), leaving inherited parent folder permissions active and allowing other local accounts access.
- **Fix**:
  - The C++ bridge uses native Win32 security APIs (`SetNamedSecurityInfoW`) with an explicit DACL containing only the owner SID (`GENERIC_ALL`) and `PROTECTED_DACL_SECURITY_INFORMATION` to strip inheritance.
  - Verify file permissions using `icacls %USERPROFILE%\.synfig\mcp_token`: it must show `:(F)` with no `(I)` inheritance flag.

---

## 7. Modal GTK Dialog Hang on `doc.close`

- **Cause**: Calling GTK/Synfig document close on a dirty document triggers an interactive modal dialog asking "Save changes before closing?", blocking the main GTK loop indefinitely in headless or remote MCP operation.
- **Fix**: The MCP bridge checks `doc->is_dirty()` before closing. If dirty, it immediately returns error code `1004` (`"Cannot close document with unsaved changes. Call doc.save first or specify force=true."`) without spawning a GTK modal dialog.

---

## 8. MSYS2 `ninja` or `cmake` Not Found in PATH

- **Cause**: Windows PowerShell or standard Command Prompt cannot resolve MSYS2 binaries unless the MSYS2 UCRT64 bin directory is added to the system PATH.
- **Fix**: Add `C:\msys64\ucrt64\bin` and `C:\msys64\usr\bin` to `PATH`, or invoke Ninja directly using `C:\msys64\ucrt64\bin\ninja.exe`.
