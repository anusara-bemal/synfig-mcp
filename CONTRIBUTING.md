# Contributing to synfig-mcp

Thank you for your interest in contributing to `synfig-mcp`!

## Code Quality Standards

Before submitting a pull request, ensure all checks pass:

```bash
cd server
poe check
```

We adhere strictly to:
- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- Clean static typing with `mypy --strict`
- Formatting and linting with `ruff`
- Full test coverage with `pytest`
