"""
CLI introspection probe for discovering layer types, parameters, valuenodes, and targets.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from synfig_mcp.schema.cache import SchemaCache
from synfig_mcp.schema.registry import LayerParamInfo, LayerTypeInfo, SchemaRegistry

if TYPE_CHECKING:
    from synfig_mcp.cli.runner import CliRunner


def seed_builtin_schemas(registry: SchemaRegistry) -> None:
    """Seed comprehensive fallback schema definitions for core Synfig layers and types."""
    common_params = {
        "z_depth": LayerParamInfo(name="z_depth", type="real", description="Stack depth"),
        "amount": LayerParamInfo(name="amount", type="real", description="Opacity (0.0 to 1.0)"),
        "blend_method": LayerParamInfo(name="blend_method", type="integer", hint="enum"),
    }

    # Circle
    circle_params = dict(common_params)
    circle_params.update(
        {
            "color": LayerParamInfo(name="color", type="color", description="Circle color"),
            "radius": LayerParamInfo(name="radius", type="real", description="Circle radius"),
            "origin": LayerParamInfo(name="origin", type="vector", description="Center point"),
            "feather": LayerParamInfo(name="feather", type="real", description="Edge feathering"),
            "invert": LayerParamInfo(name="invert", type="bool", description="Invert mask"),
        }
    )
    registry.register_layer(
        LayerTypeInfo(
            name="circle",
            localized_name="Circle",
            category="Geometry",
            description="Draws a vector circle",
            params=circle_params,
        )
    )

    # Rectangle
    rect_params = dict(common_params)
    rect_params.update(
        {
            "color": LayerParamInfo(name="color", type="color", description="Fill color"),
            "point1": LayerParamInfo(name="point1", type="vector", description="Top-left corner"),
            "point2": LayerParamInfo(
                name="point2", type="vector", description="Bottom-right corner"
            ),
            "feather": LayerParamInfo(name="feather", type="real", description="Edge feathering"),
            "invert": LayerParamInfo(name="invert", type="bool", description="Invert"),
        }
    )
    registry.register_layer(
        LayerTypeInfo(
            name="rectangle",
            localized_name="Rectangle",
            category="Geometry",
            description="Draws an axis-aligned rectangle",
            params=rect_params,
        )
    )

    # Star
    star_params = dict(common_params)
    star_params.update(
        {
            "color": LayerParamInfo(name="color", type="color", description="Star color"),
            "radius1": LayerParamInfo(name="radius1", type="real", description="Outer radius"),
            "radius2": LayerParamInfo(name="radius2", type="real", description="Inner radius"),
            "points": LayerParamInfo(name="points", type="integer", description="Number of points"),
            "origin": LayerParamInfo(name="origin", type="vector", description="Center point"),
            "angle": LayerParamInfo(name="angle", type="angle", description="Rotation angle"),
        }
    )
    registry.register_layer(
        LayerTypeInfo(
            name="star",
            localized_name="Star",
            category="Geometry",
            description="Draws a regular star polygon",
            params=star_params,
        )
    )

    # Solid Color
    solid_params = dict(common_params)
    solid_params.update(
        {
            "color": LayerParamInfo(name="color", type="color", description="Color"),
        }
    )
    registry.register_layer(
        LayerTypeInfo(
            name="solid_color",
            localized_name="Solid Color",
            category="Geometry",
            description="Fills the canvas with a solid color",
            params=solid_params,
        )
    )

    # Text
    text_params = dict(common_params)
    text_params.update(
        {
            "text": LayerParamInfo(name="text", type="string", description="Rendered text"),
            "color": LayerParamInfo(name="color", type="color", description="Text fill color"),
            "origin": LayerParamInfo(name="origin", type="vector", description="Base position"),
            "size": LayerParamInfo(name="size", type="vector", description="Font dimensions"),
            "family": LayerParamInfo(name="family", type="string", description="Font family"),
        }
    )
    registry.register_layer(
        LayerTypeInfo(
            name="text",
            localized_name="Text",
            category="Typography",
            description="Vector text rendering",
            params=text_params,
        )
    )

    # PasteCanvas (Group)
    paste_params = dict(common_params)
    paste_params.update(
        {
            "origin": LayerParamInfo(
                name="origin", type="vector", description="Group offset origin"
            ),
            "canvas": LayerParamInfo(name="canvas", type="canvas", description="Child subcanvas"),
            "zoom": LayerParamInfo(name="zoom", type="real", description="Subcanvas zoom"),
            "time_offset": LayerParamInfo(
                name="time_offset", type="time", description="Subcanvas time offset"
            ),
        }
    )
    registry.register_layer(
        LayerTypeInfo(
            name="PasteCanvas",
            localized_name="Group",
            category="Composite",
            description="Encapsulates layers inside a subcanvas",
            params=paste_params,
        )
    )

    # Targets & Renderers & Valuenodes defaults
    registry.register_targets(["png", "jpeg", "bmp", "gif", "ppm", "ffmpeg", "null"])
    registry.register_renderers(["software", "software-draft", "safe"])
    registry.register_valuenodes(
        [
            "composite",
            "radial_composite",
            "add",
            "subtract",
            "scale",
            "linear",
            "random",
            "sine",
            "cos",
            "dynamic_list",
            "static_list",
            "bline",
            "wplist",
            "dilist",
        ]
    )


async def probe_synfig_cli(
    runner: CliRunner,
    registry: SchemaRegistry,
    cache: SchemaCache | None = None,
    use_cache: bool = True,
    deep_probe_layers: bool = False,
) -> None:
    """Introspect Synfig CLI binary to populate SchemaRegistry, with caching and fallback."""
    cache_key = "synfig_cli_registry"

    # Attempt cache load
    if use_cache and cache:
        cached_data = cache.load(cache_key)
        if cached_data:
            registry.import_dict(cached_data)
            return

    # Seed core schemas first
    seed_builtin_schemas(registry)

    if not runner.is_available:
        return

    # Introspect layers
    layers = await runner.get_layers()
    for layer_name in layers:
        if deep_probe_layers:
            info = await runner.get_layer_info(layer_name)
            if info:
                registry.register_layer(info)
            else:
                registry.register_layer(LayerTypeInfo(name=layer_name))
        elif not registry.get_layer(layer_name):
            registry.register_layer(LayerTypeInfo(name=layer_name))

    # Introspect targets, renderers, valuenodes
    targets = await runner.get_targets()
    if targets:
        registry.register_targets(targets)

    renderers = await runner.get_renderers()
    if renderers:
        registry.register_renderers(renderers)

    valuenodes = await runner.get_valuenodes()
    if valuenodes:
        registry.register_valuenodes(valuenodes)

    # Save to disk cache
    if cache:
        with contextlib.suppress(Exception):
            cache.save(cache_key, registry.export_dict())
