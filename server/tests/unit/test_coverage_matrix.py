"""
CI Regression Gate: Validates feature coverage matrix against binary introspection.
Fails if coverage regresses below the Phase A0 baseline.
"""

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs"
COVERAGE_JSON = DOCS_DIR / "coverage.json"
COVERAGE_MD = DOCS_DIR / "COVERAGE.md"

# Phase A0 Baselines
BASELINE_TOTAL_LAYERS = 55
BASELINE_SUPPORTED_LAYERS = 50
BASELINE_TOTAL_VALUENODES = 69
BASELINE_TOTAL_TARGETS = 13
BASELINE_SUPPORTED_PARAMS = 440


def test_coverage_artifacts_exist() -> None:
    """Docs/coverage.json and docs/COVERAGE.md must exist and be non-empty."""
    assert COVERAGE_JSON.exists(), "docs/coverage.json is missing"
    assert COVERAGE_MD.exists(), "docs/COVERAGE.md is missing"
    assert COVERAGE_JSON.stat().st_size > 1000, "docs/coverage.json appears truncated"
    assert COVERAGE_MD.stat().st_size > 1000, "docs/COVERAGE.md appears truncated"


def test_coverage_json_schema_and_baselines() -> None:
    """Validate coverage.json schema integrity and regression thresholds."""
    with open(COVERAGE_JSON, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    assert "summary" in data
    assert "layers" in data
    assert "valuenodes" in data
    assert "targets" in data

    summary = data["summary"]
    layers_summary = summary["layers"]
    params_summary = summary["params"]
    valuenodes_summary = summary["valuenodes"]
    targets_summary = summary["targets"]

    # Regression asserts
    assert layers_summary["total"] >= BASELINE_TOTAL_LAYERS, (
        f"Layer count regressed: {layers_summary['total']} < {BASELINE_TOTAL_LAYERS}"
    )
    assert layers_summary["supported"] >= BASELINE_SUPPORTED_LAYERS, (
        f"Supported layer count regressed: {layers_summary['supported']} < {BASELINE_SUPPORTED_LAYERS}"
    )
    assert valuenodes_summary["total"] >= BASELINE_TOTAL_VALUENODES, (
        f"ValueNode count regressed: {valuenodes_summary['total']} < {BASELINE_TOTAL_VALUENODES}"
    )
    assert targets_summary["total"] >= BASELINE_TOTAL_TARGETS, (
        f"Target count regressed: {targets_summary['total']} < {BASELINE_TOTAL_TARGETS}"
    )
    assert params_summary["supported"] >= BASELINE_SUPPORTED_PARAMS, (
        f"Supported params regressed: {params_summary['supported']} < {BASELINE_SUPPORTED_PARAMS}"
    )

    # Validate individual layer entries have required fields
    for layer_name, layer_info in data["layers"].items():
        assert "name" in layer_info
        assert "read" in layer_info
        assert "write" in layer_info
        assert "status" in layer_info
        assert "params" in layer_info
        assert layer_info["name"] == layer_name


@pytest.mark.asyncio
async def test_live_binary_introspection_consistency() -> None:
    """If synfig binary is installed, ensure coverage matrix matches live CLI output."""
    from synfig_mcp.cli.runner import CliRunner

    runner = CliRunner()
    if not runner.is_available:
        pytest.skip("Synfig CLI not available in current environment")

    with open(COVERAGE_JSON, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    live_layers = set(await runner.get_layers())
    matrix_layers = set(data["layers"].keys())

    assert live_layers == matrix_layers, (
        f"Mismatch between binary layers and coverage matrix! "
        f"Missing: {live_layers - matrix_layers}, Extra: {matrix_layers - live_layers}"
    )
