"""
Schema registry storing layer, valuenode, and param descriptions.
"""

from typing import Any

from pydantic import BaseModel


class LayerTypeInfo(BaseModel):
    """Metadata describing a layer type."""

    name: str
    category: str
    description: str
    params: dict[str, Any] = {}


class SchemaRegistry:
    """Registry of known Synfig layers, valuenodes, and targets."""

    def __init__(self) -> None:
        self._layers: dict[str, LayerTypeInfo] = {}

    def register_layer(self, layer_info: LayerTypeInfo) -> None:
        """Register a layer type schema."""
        self._layers[layer_info.name] = layer_info

    def get_layer(self, name: str) -> LayerTypeInfo | None:
        """Get schema for a specific layer type."""
        return self._layers.get(name)

    def list_layers(self) -> list[str]:
        """List all registered layer names."""
        return sorted(self._layers.keys())
