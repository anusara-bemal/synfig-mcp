"""
JSON-RPC 2.0 wire models and tagged union Synfig value types.
Single source of truth matching protocol/schema/*.json.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Synfig Value Tagged Union Types (matching protocol/schema/types.json)
# ---------------------------------------------------------------------------


class RealValue(BaseModel):
    type: Literal["real"] = "real"
    value: float


class IntegerValue(BaseModel):
    type: Literal["integer"] = "integer"
    value: int


class BoolValue(BaseModel):
    type: Literal["bool"] = "bool"
    value: bool


class StringValue(BaseModel):
    type: Literal["string"] = "string"
    value: str


class AngleValue(BaseModel):
    type: Literal["angle"] = "angle"
    degrees: float
    radians: float | None = None


class TimeValue(BaseModel):
    type: Literal["time"] = "time"
    seconds: float
    frame: int | None = None
    time_string: str | None = None


class ColorValue(BaseModel):
    type: Literal["color"] = "color"
    r: float = Field(ge=0.0, le=1.0)
    g: float = Field(ge=0.0, le=1.0)
    b: float = Field(ge=0.0, le=1.0)
    a: float = Field(default=1.0, ge=0.0, le=1.0)


class VectorValue(BaseModel):
    type: Literal["vector"] = "vector"
    x: float
    y: float
    unit: Literal["synfig", "pixels"] = "synfig"
    pixel_x: float | None = None
    pixel_y: float | None = None


class ColorStop(BaseModel):
    pos: float = Field(ge=0.0, le=1.0)
    color: ColorValue


class GradientValue(BaseModel):
    type: Literal["gradient"] = "gradient"
    cpoints: list[ColorStop]


class BLinePoint(BaseModel):
    vertex: tuple[float, float]
    t1: tuple[float, float]
    t2: tuple[float, float]
    width: float = 1.0
    origin: float = 0.5
    split: bool = False


class BLinePointListValue(BaseModel):
    type: Literal["bline_point_list"] = "bline_point_list"
    points: list[BLinePoint]


class CanvasRefValue(BaseModel):
    type: Literal["canvas_ref"] = "canvas_ref"
    canvas_id: str


class ValueNodeLinkValue(BaseModel):
    type: Literal["valuenode_link"] = "valuenode_link"
    link_id: str


SynfigValue = Annotated[
    RealValue
    | IntegerValue
    | BoolValue
    | StringValue
    | AngleValue
    | TimeValue
    | ColorValue
    | VectorValue
    | GradientValue
    | BLinePointListValue
    | CanvasRefValue
    | ValueNodeLinkValue,
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Handshake Models (matching protocol/schema/handshake.json)
# ---------------------------------------------------------------------------


class HelloParams(BaseModel):
    protocol_version: str = "1.0"
    client_name: str = "synfig-mcp"
    token: str
    workspace_roots: list[str] | None = None


class HelloResult(BaseModel):
    protocol_version: str
    studio_version: str
    capabilities: list[str]
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Document & Action Results
# ---------------------------------------------------------------------------


class DiffSummary(BaseModel):
    action: str
    created: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)
    deleted: list[str] = Field(default_factory=list)


class DocInfoResult(BaseModel):
    doc_id: str
    name: str
    file_path: str | None = None
    width: int
    height: int
    fps: float
    start_time: float = 0.0
    end_time: float = 5.0
    duration_frames: int


class LayerAddResult(BaseModel):
    doc_id: str
    layer_id: str
    layer_type: str
    description: str = ""
    depth: int = 0
    diff: DiffSummary


class ParamSetResult(BaseModel):
    doc_id: str
    layer_id: str
    param_name: str
    before: SynfigValue | None = None
    after: SynfigValue


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 Base Framing
# ---------------------------------------------------------------------------


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 Request."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class JsonRpcErrorPayload(BaseModel):
    """JSON-RPC 2.0 Error object."""

    code: int
    message: str
    data: dict[str, Any] | None = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 Response."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = None
    result: Any | None = None
    error: JsonRpcErrorPayload | None = None


class JsonRpcNotification(BaseModel):
    """JSON-RPC 2.0 Notification (server-to-client events)."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
