# Synfig MCP Repository Audit & Cleanup Plan

> **Phase A0 Baseline Audit** (Target: v0.8.0-rc1)
> Systematically analyzes code bloat, files over 400 lines, stale documentation, naming inconsistencies, git topology, and dead code.
> Establishes the actionable refactoring roadmap for **Phase A7 (Repo & UX Polish)**.

---

## 1. Files Over 400 Lines (Refactoring Targets)

Analysis performed across source, bridge, documentation, and test suites:

| File Path | Line Count | Current Responsibility | Proposed Phase A7 Split / Action |
|---|---|---|---|
| `bridge/src/mcp_bridge/handlers.cpp` | **3,275** | Monolithic JSON-RPC dispatcher for doc, layer, param, anim, history, render, and selection | Split by domain into `handlers_doc.cpp`, `handlers_layer.cpp`, `handlers_param.cpp`, `handlers_anim.cpp`, `handlers_render.cpp` with a central router |
| `server/tests/e2e/test_live_mutate.py` | **1,874** | All live E2E mutation tests against real Synfig Studio | Split into focused suites: `test_live_layers.py`, `test_live_params.py`, `test_live_anim.py`, `test_live_security.py` |
| `server/src/synfig_mcp/tools/register.py` | **1,890** | Monolithic MCP tool registration functions (all 89 tools in one file) | Split into domain modules under `synfig_mcp/tools/`: `doc.py`, `layer.py`, `param.py`, `anim.py`, `render.py`, `scene.py` |
| `docs/tools.md` | **1,902** | Auto-generated Markdown tool reference | Keep generated, but update `scripts/generate_tool_docs.py` to group by profile and link to topic guides |
| `server/src/synfig_mcp/sif/parser.py` | **2,213** | XML DOM parser, SIF document abstraction, layer models, waypoints | Separate into `ast.py`, `layers.py`, `values.py`, and `serializer.py` |
| `server/src/synfig_mcp/backend/headless.py` | **1,401** | Complete headless SIF engine + CLI fallback | Modularize backend delegate classes for canvas manipulation, parameters, and render jobs |
| `server/tests/contract/test_mcp_tools.py` | **737** | Parametrized contract tests for all tools | Split into per-domain contract test modules |
| `server/src/synfig_mcp/protocol/fake_bridge.py` | **1,146** | In-memory mock TCP bridge server | Split mock document storage from protocol handshake logic |
| `server/src/synfig_mcp/backend/live.py` | **1,056** | Live bridge backend adapter | Keep coherent, delegate complex render polling to render pipeline |
| `server/src/synfig_mcp/backend/base.py` | **543** | BaseBackend abstract class | Clean abstract interface; acceptable size |

---

## 2. Duplicate and Stale Documentation Audit

1. **`server/README.md` vs Root `README.md`**:
   - `server/README.md` is now a short, server-specific package README (install/use for the PyPI package), distinct from the root README.
   - *Resolution*: Resolved; keep the package README focused on the Python server.
2. **`docs/ROADMAP.md`**:
   - Stale milestones referencing completed alpha targets (v0.6.0, v0.7.0) and Phase P0–P7.
   - *Resolution*: Reconcile `ROADMAP.md` to reflect the v0.8.0-rc1 Studio-grade upgrade phases (A0 through A8).
3. **`scripts/generate_tool_docs.py`**:
   - The generator introspects the live registry, so it always documents all 89 tools.

---

## 3. Naming and API Inconsistencies

1. **Tool Naming (`verb_noun` consistency)**:
   - Current names: `layer_remove` vs `layer_delete`, `layer_reorder` vs `layer_move`, `scene_tree` (noun phrase) vs `canvas_list`, `import_asset` vs `asset_import`.
   - C++ Bridge methods: Accepts both `layer.remove` and `layer.delete`, `layer.move` and `layer.reorder`.
   - *Resolution*: Standardize Python MCP tool names strictly on `noun_verb` or `verb_noun` convention in Phase A1 / A7.
2. **Parameter Conventions**:
   - Some layer tools accept `canvas_path: str = ""` while others require explicit canvas resolution.
   - *Resolution*: Unify canvas targeting across all tools.
3. **Version Number Single Source of Truth**:
   - `server/pyproject.toml` defines `0.7.0rc3`.
   - `bridge/src/mcp_bridge/handlers.cpp` hardcodes `0.7.0-rc3`.
   - *Resolution*: Centralize version in a single file (e.g. `VERSION` or root metadata) injected into C++ build via CMake and read dynamically by Python packaging.

---

## 4. Git References and Branch Topology Audit

1. **Branch `v1.0.0`**:
   - Currently checked out branch is named `v1.0.0`, while `origin/HEAD` points to `origin/main`.
   - A branch named after a future major version creates confusion with release tags.
   - *Resolution*: Never delete tags. Align work on `main` or a dedicated release branch `release/v0.8.0-rc1`.
2. **Preservation of Existing Tags**:
   - Verified existing tags: `v0.6.0`, `v0.7.0-rc1`, `v0.7.0-rc2`, `v0.7.0-rc3`.
   - **Hard Rule**: No existing tags will be deleted or moved. Code changes will ship strictly under the new tag `v0.8.0-rc1`.

---

## 5. Dead Code and Workspace Cleanup

1. **`scratch/` Directory**:
   - Contains 15 ad-hoc debugging scripts from previous CI troubleshooting (`check_all_jobs.py`, `check_ci.py`, `fetch_pkg_info.py`, `pkgs_info.json`, `test_win32_fs.cpp`).
   - *Resolution*: Move or archive these ad-hoc scripts to keep the root repository clean.
2. **`dist/` Directory**:
   - Contains historical release archives from previous builds.
   - *Resolution*: Retain `.gitignore` tracking so build artifacts are excluded from git.
