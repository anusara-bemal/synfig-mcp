# Upstream Rebase & Maintenance Guide

This document describes how to maintain, update, and rebase the `synfig-mcp` C++ bridge patches against newer Synfig Studio releases or upstream `master` commits.

---

## 1. Architecture of the C++ Bridge Patches

The C++ bridge is injected into Synfig Studio via clean, non-intrusive patches against the official Synfig source tree:

1. **`bridge/patches/0001-mcp-bridge.patch`**:
   - Hooks into `synfig-studio/src/gui/app.cpp` (application lifecycle: initialize bridge on startup, tear down on exit).
   - Injects the `mcp_bridge` subsystem into `synfig-studio/src/gui/mcp_bridge/`:
     * `server.h` / `server.cpp`: TCP listening socket (`127.0.0.1:19998`), session token generation and authorization, JSON-RPC 2.0 framing.
     * `dispatcher.h` / `dispatcher.cpp`: Thread synchronization using `Glib::Dispatcher` to marshal requests from the bridge TCP thread safely onto the GTKmm main thread.
     * `handlers.h` / `handlers.cpp`: Method dispatch table mapping RPC methods (`doc.*`, `layer.*`, `param.*`, `anim.*`, `canvas.*`) to `synfigapp::Action` executions wrapped in `synfigapp::Action::PassiveGrouper`.
   - Modifies `synfig-studio/src/gui/CMakeLists.txt` to include `mcp_bridge` sources, headers, and dependencies (`nlohmann/json`).

---

## 2. Rebase Workflow

When rebasing onto a new Synfig commit or release tag (e.g. `v1.5.2` -> `v1.6.0`):

### Step 1: Update the Pinned Commit
In `bridge/scripts/fetch_synfig.sh`:
```bash
# Update PINNED_COMMIT to the new target commit or release tag
PINNED_COMMIT="<new_git_sha_or_tag>"
```

### Step 2: Fetch Upstream Tree
```bash
bash bridge/scripts/fetch_synfig.sh build_synfig/synfig_src
cd build_synfig/synfig_src
```

### Step 3: Apply and Inspect Existing Patches
```bash
git checkout -b rebase-mcp
git am ../../bridge/patches/*.patch
```

If conflicts occur:
1. Run `git status` to identify conflicting files (typically `synfig-studio/src/gui/app.cpp` or `CMakeLists.txt`).
2. Resolve conflicts manually in your editor:
   - Check if `App::init()` or `App::quit()` signatures changed in `app.cpp`.
   - Check if `CMakeLists.txt` variable names changed for Studio GUI sources.
3. Verify `synfigapp::Action` API changes:
   - In `handlers.cpp`, methods rely on standard actions (`LayerParamSet`, `LayerAdd`, `LayerRemove`, `WaypointSet`, `WaypointRemove`, `KeyframeAdd`).
   - If any `synfigapp::Action` parameters changed, check `synfig-studio/src/synfigapp/actions/` in the new upstream tree.
4. Stage and continue:
   ```bash
   git add -u
   git am --continue
   ```

### Step 4: Regenerate Clean Patches
Export the rebased commits back into `bridge/patches/`:
```bash
git format-patch -1 HEAD -o ../../bridge/patches/
```

---

## 3. synfigapp API Compatibility Checklist

When rebasing across major Synfig releases:

| Action / API | Target Upstream File | Expected Behavior |
| :--- | :--- | :--- |
| `PassiveGrouper` | `synfigapp/action.h` | Groups sub-actions into a single undo step. Must be instantiated before action dispatch. |
| `LayerParamSet` | `synfigapp/actions/layerparamset.h` | Modifies layer value. Must take `ValueDesc(layer, param_name)` and `ValueBase`. |
| `WaypointSet` | `synfigapp/actions/waypointset.h` | Inserts or updates waypoint on an animated ValueNode. |
| `WaypointRemove` | `synfigapp/actions/waypointremove.h` | Removes waypoint at specified `synfig::Time`. |
| `KeyframeAdd` | `synfigapp/actions/keyframeadd.h` | Locks values across all active layers at keyframe time. |
| `Glib::Dispatcher` | `glibmm/dispatcher.h` | Thread-safe inter-thread signal invocation. Must connect to a member slot. |

---

## 4. Verification

After rebasing:
1. Compile using `bash bridge/scripts/build_windows_msys2.sh` (or `build_linux.sh`).
2. Run unit and contract tests: `poe check`
3. Run the live E2E regression suite against the newly compiled binary:
   ```bash
   poe live
   ```
   All 13 `real_studio` tests must pass without regressions, asserting both document mutation and atomic undo restoration.
