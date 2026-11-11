"""
Schema registry storing introspected Synfig layer types, parameters, valuenodes, and targets.
"""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class LayerParamInfo(BaseModel):
    """Metadata describing an individual layer parameter."""

    name: str
    localized_name: str = ""
    description: str = ""
    type: str = "any"
    hint: str = ""
    #: Whether the MCP can write values of this parameter.
    editable: bool = True
    #: Whether the Synfig GUI exposes the parameter for writing (``None`` when
    #: the information comes from a source that does not report it).
    writable: bool | None = None
    #: Whether the parameter is hidden from the GUI.
    hidden: bool = False
    #: Whether the parameter can carry waypoints in Synfig.
    animatable: bool = True
    #: ``ParamDesc`` origin (for example ``"Synfig"`` or ``"user"``).
    origin: str = ""
    #: Enumeration values of an integer parameter with ``hint == "enum"``.
    enum: list[dict[str, Any]] = Field(default_factory=list)
    #: Default value the layer factory reports, in wire format.
    default: Any = None

    @model_validator(mode="after")
    def _sync_editable(self) -> "LayerParamInfo":
        from synfig_mcp.schema.param_types import is_editable_param

        if self.type and self.type not in ("any", "unknown"):
            supported = is_editable_param(self.name, self.type)
            if self.writable is not None:
                # A live probe knows both halves: Synfig's own write flag and
                # whether the MCP can serialise the value type.
                object.__setattr__(self, "editable", bool(self.writable) and supported)
            else:
                object.__setattr__(self, "editable", supported)
        return self


class LayerTypeInfo(BaseModel):
    """Metadata describing a layer type and its parameters."""

    name: str
    localized_name: str = ""
    category: str = "General"
    version: str = "0.1"
    description: str = ""
    params: dict[str, LayerParamInfo] = Field(default_factory=dict)


def layer_info_from_bridge(entry: dict[str, Any]) -> LayerTypeInfo:
    """Convert one ``schema.list_layers`` entry into a :class:`LayerTypeInfo`.

    The bridge reports the live ``synfig::Layer::book()`` entry: the factory
    metadata plus the real ``ParamDesc`` vocabulary of a freshly constructed
    instance.  This function is the single translation point between the wire
    format and the schema models used by the tools.
    """
    raw_params = entry.get("params")
    params: dict[str, LayerParamInfo] = {}
    if isinstance(raw_params, dict):
        for param_name, payload in raw_params.items():
            if not isinstance(payload, dict):
                payload = {"type": payload}
            params[str(param_name)] = LayerParamInfo(
                name=str(param_name),
                localized_name=str(payload.get("local_name", "")),
                description=str(payload.get("description", "")),
                type=str(payload.get("type", "any")),
                hint=str(payload.get("hint", "")),
                writable=bool(payload.get("writable", True)),
                hidden=bool(payload.get("hidden", False)),
                animatable=bool(payload.get("animatable", True)),
                origin=str(payload.get("origin", "")),
                enum=list(payload.get("enum") or []),
                default=payload.get("default"),
            )

    return LayerTypeInfo(
        name=str(entry.get("name", "")),
        localized_name=str(entry.get("local_name", "")),
        category=str(entry.get("category", "General")),
        version=str(entry.get("version", "0.1")),
        description=str(entry.get("description", "")),
        params=params,
    )


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
