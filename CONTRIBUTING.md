# Contributing to Synfig MCP

Thank you for your interest in contributing to `synfig-mcp`!

## Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AnusaraBemal/synfig-mcp.git
   cd synfig-mcp
   ```

2. **Create a virtual environment (Python >= 3.10)**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   # Or install dependencies manually:
   pip install pytest pytest-asyncio pytest-cov ruff mypy pre-commit
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## Running Tests and Linting

- **Run all unit tests**:
  ```bash
  pytest
  ```

- **Run tests with coverage**:
  ```bash
  pytest --cov=src/synfig_mcp --cov-report=term-missing
  ```

- **Run integration tests (requires real synfig binary)**:
  ```bash
  pytest -m synfig
  ```

- **Run Ruff linter and formatter**:
  ```bash
  ruff check .
  ruff format --check .
  ```

- **Run Mypy strict type checking**:
  ```bash
  mypy
  ```

## Making Changes

1. Create a feature branch: `git checkout -b feature/my-new-feature`.
2. Ensure every new source file includes the SPDX header:
   ```python
   # SPDX-License-Identifier: MIT
   # Copyright (c) 2026 Anusara Bemal (ABM)
   ```
3. Add unit tests for any new functionality or bug fixes.
4. Verify that `ruff`, `mypy`, and `pytest` all pass cleanly.
5. If modifying tools, regenerate documentation via:
   ```bash
   python scripts/gen_docs.py
   ```
6. Submit a Pull Request.
