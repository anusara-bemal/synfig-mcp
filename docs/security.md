# Security Architecture & Sandbox Model

`synfig-mcp` connects LLMs to local desktop software and filesystem pipelines. Strict security boundaries are enforced.

---

## 1. Local-Only Network Binding

- The C++ native bridge binds strictly to `127.0.0.1`.
- External or remote network interfaces are rejected by socket configuration.
- A per-session authentication token is generated on Studio startup with `0600` permissions (user read-write only) at `~/.synfig/mcp_token`.

---

## 2. No Arbitrary Code Execution

- There is **no arbitrary code execution tool** (no Python `eval`, no C++ `dlopen`, no shell injection).
- All operations map to a finite, typed set of `synfigapp` actions.

---

## 3. Filesystem Sandboxing

- File paths passed to `doc_open`, `doc_save`, or `import_asset` are validated against `workspace_roots`.
- Directory traversal patterns (`../`) and symlink escapes outside the configured roots raise `SecuritySandboxError`.

---

## 4. XML Safety in Headless SIF Processing

- `lxml` is configured with `resolve_entities=False` to prevent XML External Entity (XXE) attacks.
- Decompression bomb guards are enforced when decompressing `.sifz` and `.sfg` files.
