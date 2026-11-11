"""
Unit tests for SchemaRegistry, SchemaCache, and probe_synfig_cli.

The registry is the source of truth the LLM uses to discover layer types and
parameters, so it must reflect the *real* Synfig build - no stale or invented
entries.
"""

import tempfile
from pathlib import Path

import pytest

from synfig_mcp.cli.runner import CliRunner
from synfig_mcp.schema.cache import SchemaCache
from synfig_mcp.schema.param_types import load_param_types
from synfig_mcp.schema.probe import (
    REGISTRY_CACHE_KEY,
    get_synfig_registry,
    probe_synfig_cli,
    seed_builtin_schemas,
)
from synfig_mcp.schema.registry import LayerParamInfo, LayerTypeInfo, SchemaRegistry


@pytest.fixture
def runner() -> CliRunner:
    r = CliRunner()
    if not r.is_available:
        pytest.skip("Synfig CLI not available in current environment")
    return r


def test_schema_registry_crud() -> None:
    registry = SchemaRegistry()
    assert len(registry.list_layers()) == 0

    param = LayerParamInfo(name="radius", type="real", description="Radius")
    layer = LayerTypeInfo(
        name="my_circle",
        localized_name="My Circle",
        category="Geometry",
        description="Test circle",
        params={"radius": param},
    )
    registry.register_layer(layer)

    assert registry.list_layers() == ["my_circle"]
    fetched = registry.get_layer("my_circle")
    assert fetched is not None
    assert fetched.localized_name == "My Circle"
    assert "radius" in fetched.params
    assert fetched.params["radius"].type == "real"
    assert fetched.params["radius"].editable is True

    # Targets, renderers, valuenodes
    registry.register_targets(["png", "jpeg"])
    assert registry.list_targets() == ["jpeg", "png"]

    registry.register_renderers(["software"])
    assert registry.list_renderers() == ["software"]

    registry.register_valuenodes(["composite", "add"])
    assert registry.list_valuenodes() == ["add", "composite"]


def test_schema_registry_export_import() -> None:
    reg1 = SchemaRegistry()
    seed_builtin_schemas(reg1)

    data = reg1.export_dict()
    assert "layers" in data
    assert "circle" in data["layers"]

    reg2 = SchemaRegistry()
    reg2.import_dict(data)
    assert "circle" in reg2.list_layers()
    assert "rectangle" in reg2.list_layers()
    assert "png" in reg2.list_targets()


def test_schema_cache() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache_dir = Path(tmp_dir)
        cache = SchemaCache(cache_dir=cache_dir)

        assert cache.load("missing_key") is None

        payload = {"layers": {"test": {"name": "test"}}}
        cache.save("my_key", payload)

        loaded = cache.load("my_key")
        assert loaded == payload


def test_schema_cache_freshness() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = SchemaCache(cache_dir=Path(tmp_dir))
        assert cache.is_fresh("my_key") is False
        cache.save("my_key", {"a": 1})
        assert cache.is_fresh("my_key") is True
        assert cache.is_fresh("my_key", max_age_seconds=-1) is False


@pytest.mark.asyncio
async def test_probe_synfig_cli_with_cache() -> None:
    runner = CliRunner()
    if not runner.is_available:
        pytest.skip("synfig binary not available on this system")

    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = SchemaCache(cache_dir=Path(tmp_dir))
        registry = SchemaRegistry()

        await probe_synfig_cli(runner, registry, cache=cache, use_cache=True)

        assert len(registry.list_layers()) >= 6
        assert "circle" in registry.list_layers()
        assert "rectangle" in registry.list_layers()

        # Check cache was created on disk
        cached_data = cache.load(REGISTRY_CACHE_KEY)
        assert cached_data is not None
        assert "circle" in cached_data["layers"]


@pytest.mark.asyncio
async def test_registry_reports_every_layer_type(runner: CliRunner) -> None:
    registry = await get_synfig_registry(runner=runner)
    live_layers = set(await runner.get_layers())
    reported = set(registry.list_layers())

    missing = live_layers - reported
    assert not missing, f"Layer types missing from the registry: {sorted(missing)}"


@pytest.mark.asyncio
async def test_registry_reports_every_target_and_renderer(runner: CliRunner) -> None:
    registry = await get_synfig_registry(runner=runner)

    live_targets = set(await runner.get_targets())
    assert live_targets <= set(registry.list_targets())

    live_renderers = set(await runner.get_renderers())
    assert live_renderers == set(registry.list_renderers())

    live_valuenodes = set(await runner.get_valuenodes())
    assert live_valuenodes <= set(registry.list_valuenodes())


@pytest.mark.asyncio
async def test_registry_reports_real_parameters(runner: CliRunner) -> None:
    registry = await get_synfig_registry(runner=runner)

    for layer_name in ("circle", "rectangle", "outline", "text", "star"):
        info = await runner.get_layer_info(layer_name)
        assert info is not None
        reported = registry.get_layer(layer_name)
        assert reported is not None, f"{layer_name} missing from the registry"
        assert set(reported.params) == set(info.params), (
            f"Parameter mismatch for {layer_name}: "
            f"missing={sorted(set(info.params) - set(reported.params))} "
            f"extra={sorted(set(reported.params) - set(info.params))}"
        )


@pytest.mark.asyncio
async def test_registry_reports_real_parameter_types(runner: CliRunner) -> None:
    """Every parameter of a known layer must carry its introspected value type."""
    registry = await get_synfig_registry(runner=runner)
    param_types = load_param_types()
    assert param_types, "the introspected parameter type table is empty"

    checked = 0
    for layer_name, params in param_types.items():
        reported = registry.get_layer(layer_name)
        if reported is None:
            continue
        for param_name, value_type in params.items():
            param = reported.params.get(param_name)
            if param is None:
                continue
            assert param.type == value_type, (
                f"{layer_name}.{param_name} reported as '{param.type}', expected '{value_type}'"
            )
            checked += 1
    assert checked > 100, f"only {checked} parameter types were verified"


@pytest.mark.asyncio
async def test_complex_parameters_are_marked_non_editable(runner: CliRunner) -> None:
    registry = await get_synfig_registry(runner=runner)

    outline = registry.get_layer("outline")
    assert outline is not None
    assert outline.params["bline"].type == "list"
    # ``bline`` is written as a <bline> element and is therefore editable.
    assert outline.params["bline"].editable is True

    skeleton = registry.get_layer("skeleton")
    assert skeleton is not None
    assert skeleton.params["bones"].editable is False


def test_seeded_registry_is_a_usable_fallback() -> None:
    """The offline fallback must still expose the core layer types."""
    registry = SchemaRegistry()
    seed_builtin_schemas(registry)
    assert "circle" in registry.list_layers()
    assert "PasteCanvas" in registry.list_layers()
    assert registry.get_layer("circle") is not None
