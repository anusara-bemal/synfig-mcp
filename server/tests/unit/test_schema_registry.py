"""
Unit tests for SchemaRegistry, SchemaCache, and probe_synfig_cli.
"""

import tempfile
from pathlib import Path

import pytest

from synfig_mcp.cli.runner import CliRunner
from synfig_mcp.schema.cache import SchemaCache
from synfig_mcp.schema.probe import probe_synfig_cli, seed_builtin_schemas
from synfig_mcp.schema.registry import LayerParamInfo, LayerTypeInfo, SchemaRegistry


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


@pytest.mark.asyncio
async def test_probe_synfig_cli_with_cache() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = SchemaCache(cache_dir=Path(tmp_dir))
        runner = CliRunner()
        registry = SchemaRegistry()

        await probe_synfig_cli(runner, registry, cache=cache, use_cache=True)

        assert len(registry.list_layers()) >= 6
        assert "circle" in registry.list_layers()
        assert "rectangle" in registry.list_layers()

        # Check cache was created on disk
        cached_data = cache.load("synfig_cli_registry")
        assert cached_data is not None
        assert "circle" in cached_data["layers"]
