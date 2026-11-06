# Changelog

All notable changes to `synfig-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-06

### Added
- Phase G0 Feasibility Gate: Verified compilation on Windows (MSYS2 UCRT64) against pinned Synfig `v1.5.5`.
- Throwaway socket hook proving thread-safe cross-thread action dispatch via `Glib::Dispatcher` and `synfigapp::CanvasInterface::add_layer_to`.
- Monorepo scaffold: `server/` Python package with hatchling/uv, `bridge/` C++ patch series and build automation, and `docs/`.
- Dual-backend interface (`LiveBackend` and `HeadlessBackend`) with auto-probing.
- Cross-platform task automation via `poethepoet` (`poe check`).
