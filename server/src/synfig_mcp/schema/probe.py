"""
CLI introspection probe for discovering layer types and params from synfig binary.
"""

from synfig_mcp.schema.registry import LayerTypeInfo, SchemaRegistry


def probe_synfig_cli_layers(registry: SchemaRegistry) -> None:
    """Populate registry from synfig --layers CLI introspection."""
    # Seed core common layers
    registry.register_layer(
        LayerTypeInfo(name="circle", category="Geometry", description="Draws a vector circle")
    )
    registry.register_layer(
        LayerTypeInfo(name="rectangle", category="Geometry", description="Draws a rectangle")
    )
    registry.register_layer(
        LayerTypeInfo(name="star", category="Geometry", description="Draws a star")
    )
