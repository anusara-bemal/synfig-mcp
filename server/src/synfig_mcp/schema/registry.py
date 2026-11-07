"""
Schema registry storing introspected Synfig layer types, parameters, valuenodes, and targets.
"""

from typing import Any

from pydantic import BaseModel, Field


class LayerParamInfo(BaseModel):
    """Metadata describing an individual layer parameter."""

    name: str
    localized_name: str = ""
    description: str = ""
    type: str = "any"
    hint: str = ""


class LayerTypeInfo(BaseModel):
    """Metadata describing a layer type and its parameters."""

    name: str
    localized_name: str = ""
    category: str = "General"
    version: str = "0.1"
    description: str = ""
    params: dict[str, LayerParamInfo] = Field(default_factory=dict)


class SchemaRegistry:
    """Registry of known Synfig layers, valuenodes, renderers, and targets."""

    def __init__(self) -> None:
        self._layers: dict[str, LayerTypeInfo] = {}
        self._valuenodes: set[str] = set()
        self._targets: set[str] = set()
        self._renderers: set[str] = set()

    def register_layer(self, layer_info: LayerTypeInfo) -> None:
        """Register a layer type schema."""
        self._layers[layer_info.name] = layer_info

    def get_layer(self, name: str) -> LayerTypeInfo | None:
        """Get schema for a specific layer type."""
        return self._layers.get(name)

    def list_layers(self) -> list[str]:
        """List all registered layer names."""
        return sorted(self._layers.keys())

    def register_valuenodes(self, valuenodes: list[str]) -> None:
        """Register discovered valuenode types."""
        self._valuenodes.update(valuenodes)

    def list_valuenodes(self) -> list[str]:
        """List all registered valuenodes."""
        return sorted(self._valuenodes)

    def register_targets(self, targets: list[str]) -> None:
        """Register render targets."""
        self._targets.update(targets)

    def list_targets(self) -> list[str]:
        """List all render targets."""
        return sorted(self._targets)

    def register_renderers(self, renderers: list[str]) -> None:
        """Register renderers."""
        self._renderers.update(renderers)

    def list_renderers(self) -> list[str]:
        """List all renderers."""
        return sorted(self._renderers)

    def export_dict(self) -> dict[str, Any]:
        """Serialize complete registry to a dict for caching."""
        return {
            "layers": {k: v.model_dump() for k, v in self._layers.items()},
            "valuenodes": sorted(self._valuenodes),
            "targets": sorted(self._targets),
            "renderers": sorted(self._renderers),
        }

    def import_dict(self, data: dict[str, Any]) -> None:
        """Hydrate registry from a cached dictionary."""
        layers_data = data.get("layers", {})
        for name, l_data in layers_data.items():
            self._layers[name] = LayerTypeInfo.model_validate(l_data)
        self._valuenodes = set(data.get("valuenodes", []))
        self._targets = set(data.get("targets", []))
        self._renderers = set(data.get("renderers", []))
