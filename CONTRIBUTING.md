# Contributing to Synfig MCP

Thanks for helping improve Synfig MCP. This project welcomes bug reports, documentation fixes, new tools, and platform testing.

## Code of conduct

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Development setup

Requirements: Python 3.12+, `uv`, and Git. Building the native Studio bridge additionally needs the platform toolchain described in [docs/build-windows.md](docs/build-windows.md) or [docs/build-linux.md](docs/build-linux.md).

```bash
git clone https://github.com/anusara-bemal/synfig-mcp.git
cd synfig-mcp/server
uv sync --locked --all-extras
```

## Checks

Run the full gate before opening a pull request:

```bash
uv run poe check
```

This runs:

- `ruff format --check src tests`
- `ruff check src tests`
- `mypy --strict src tests`
- `pytest -m "not real_studio"`

Live Studio tests require a patched build:

```bash
uv run poe live
```

Frontend documentation changes should also pass:

```bash
pip install mkdocs-material
mkdocs build --strict
```

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat(scope): ...` — user-visible feature
- `fix(scope): ...` — bug fix
- `docs: ...` — documentation
- `refactor: ...` — internal change without behavior change
- `test: ...` — test-only change
- `chore: ...` — tooling, dependencies, CI

Keep commits focused. Update `CHANGELOG.md` for user-visible changes.

## Pull requests

1. Fork the repository and create a topic branch.
2. Describe the problem, the approach, and the verification performed.
3. Link related issues.
4. Ensure CI is green. Maintainers will not merge failing or flaky changes.
5. For release-affecting changes, confirm both Linux and Windows builds still pass.

## Adding a tool

1. Add the handler in `server/src/synfig_mcp/tools/register.py`.
2. Register it in the correct profile(s) and update `docs/COVERAGE.md` tool counts if applicable.
3. Add contract tests under `server/tests/contract/` and unit tests for logic.
4. Update `docs/api.md` and `docs/tools.md`.
5. Verify the profile token budget with `uv run poe test` (the budget test is a CI gate).

## Releasing

Releases are cut from an immutable tag:

```bash
git tag -a v0.8.0-rc2 -m "synfig-mcp v0.8.0-rc2"
git push origin v0.8.0-rc2
```

The tag pipeline builds Windows and Linux Studio bundles, runs clean-runner smoke tests, builds the Python wheel/sdist and GPL source bundle, writes checksums, publishes a GitHub release, and pushes the container image.

Never move or delete a published tag. Cut a new tag instead.
