"""
Machine-readable capability registry and compact meta-tools.

Rather than making an LLM read ~90 verbose tool schemas, the server exposes a
single searchable registry of *capabilities* (its own tools, the bridge's
protocol methods, and Synfig's introspected layer/valuenode types) that can be
explored and invoked through a handful of compact meta-tools:

``capability_search``, ``capability_list``, ``capability_inspect``,
``capability_execute``, ``capability_batch_execute``, ``capability_validate``,
``capability_discover``, ``capability_load_profile``, ``capability_unload_profile``,
``capability_workflow_execute`` and ``capability_workflow_resume``.

The registry is built by introspecting the *actually registered* MCP tools, so it
can never advertise a capability the server cannot serve (honest-by-construction).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from synfig_mcp.errors import SynfigError, ValidationError

#: Built-in error codes surfaced by tools, reused across capabilities.
_DEFAULT_ERROR_CODES = [
    "DocumentNotFoundError",
    "LayerNotFoundError",
    "ParamNotFoundError",
    "ValidationError",
    "SecuritySandboxError",
    "ActionExecutionError",
    "RenderError",
    "BridgeConnectionError",
]


class Capability(BaseModel):
    """A single, machine-readable thing the server can do."""

    id: str
    name: str
    description: str = ""
    domain: str = "general"
    kind: str = "tool"  # tool | protocol | schema
    required_params: list[str] = Field(default_factory=list)
    optional_params: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    #: "read" | "write" | "destructive"
    permission: str = "write"
    #: Available against the pure-Python headless engine.
    native: bool = True
    #: Available against a live Synfig Studio through the bridge.
    gui: bool = False
    dependencies: list[str] = Field(default_factory=list)
    execution_method: str = "direct"
    error_codes: list[str] = Field(default_factory=lambda: list(_DEFAULT_ERROR_CODES))
    retry_safe: bool = False
    undoable: bool = False
    verification: str = "unit"
    synfig_version: str = "any"
    profiles: list[str] = Field(default_factory=list)


class WorkflowStep(BaseModel):
    capability: str
    args: dict[str, Any] = Field(default_factory=dict)
    #: Optional key under which this step's output is stored in the run context.
    save_as: str | None = None
    description: str = ""


class CapabilityWorkflow(BaseModel):
    id: str
    name: str
    description: str = ""
    steps: list[WorkflowStep] = Field(default_factory=list)


#: Ready-made workflows that chain capabilities without the caller having to
#: orchestrate each call. Steps reference capability ids and may pull arguments
#: from the run context via ``${name}`` placeholders.
BUILTIN_WORKFLOWS: list[CapabilityWorkflow] = [
    CapabilityWorkflow(
        id="new_document",
        name="Create a blank document",
        description="Create a document and confirm it is open.",
        steps=[
            WorkflowStep(
                capability="doc_new",
                args={"width": 1920, "height": 1080, "fps": 24.0},
                save_as="doc",
                description="Create the canvas",
            ),
            WorkflowStep(capability="doc_info", args={"doc_id": "${doc.id}"}),
        ],
    ),
    CapabilityWorkflow(
        id="build_scene",
        name="Build and render a simple scene",
        description="Create a document, add a layer, then render a frame.",
        steps=[
            WorkflowStep(
                capability="doc_new",
                args={"width": 640, "height": 480, "fps": 24.0},
                save_as="doc",
            ),
            WorkflowStep(
                capability="layer_add",
                args={"doc_id": "${doc.id}", "layer_type": "circle"},
                save_as="layer",
            ),
            WorkflowStep(
                capability="render_frame",
                args={"doc_id": "${doc.id}", "time": 0.0},
                save_as="render",
            ),
        ],
    ),
]


def _resolve(value: Any, context: dict[str, Any]) -> Any:
    """Resolve ``${a.b}`` placeholders inside strings against the run context."""
    if isinstance(value, str):
        match = re.fullmatch(r"\$\{([^}]+)\}", value)
        if match:
            current: Any = context
            for part in match.group(1).split("."):
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
            return current
        return value
    if isinstance(value, dict):
        return {k: _resolve(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, context) for v in value]
    return value


# ---------------------------------------------------------------------------
# Introspection: turn the live tool surface into capabilities
# ---------------------------------------------------------------------------

_DOMAIN_SECTIONS: dict[str, str] = {}


def _domain_map() -> dict[str, str]:
    """Map tool name -> domain by reading the section comments in register.py."""
    global _DOMAIN_SECTIONS
    if _DOMAIN_SECTIONS:
        return _DOMAIN_SECTIONS
    mapping: dict[str, str] = {}
    try:
        src = (Path(__file__).parent / "tools" / "register.py").read_text(encoding="utf-8")
    except OSError:
        return mapping
    lines = src.splitlines()
    current = "core"
    for idx, line in enumerate(lines):
        header = re.match(r"\s*# ([A-Z].*?)\s*$", line)
        if header and idx + 1 < len(lines) and re.match(r"\s*# -+\s*$", lines[idx + 1]):
            label = header.group(1).split(" (")[0].strip().lower()
            current = re.sub(r"[^a-z0-9]+", "_", label).strip("_")
        tool = re.search(r'@tool_for\("([a-z_]+)"', line)
        if tool:
            mapping[tool.group(1)] = current
    _DOMAIN_SECTIONS = mapping
    return mapping


def _permission_from_annotations(annotations: Any) -> str:
    if annotations is None:
        return "write"
    if getattr(annotations, "read_only_hint", False):
        return "read"
    if getattr(annotations, "destructive_hint", False):
        return "destructive"
    return "write"


def _protocol_gui_methods() -> dict[str, bool]:
    """Parse docs/protocol.md -> {method: gui_available}."""
    result: dict[str, bool] = {}
    candidates = [
        Path(__file__).resolve().parents[2] / "docs" / "protocol.md",
        Path(__file__).resolve().parents[3] / "docs" / "protocol.md",
    ]
    doc = next((c for c in candidates if c.is_file()), None)
    if doc is None:
        return result
    for line in doc.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        method = cells[0].strip("`")
        result[method] = "Not implemented" not in line
    return result


def build_capabilities(mcp: Any) -> list[Capability]:
    """Introspect the registered tools and build the capability list."""
    domains = _domain_map()
    gui_methods = _protocol_gui_methods()
    caps: list[Capability] = []

    for tool in mcp._tool_manager.list_tools():
        schema = tool.parameters or {}
        props = schema.get("properties", {})
        required = list(schema.get("required", []))
        optional = [p for p in props if p not in required]
        permission = _permission_from_annotations(tool.annotations)
        caps.append(
            Capability(
                id=tool.name,
                name=tool.name,
                description=(tool.description or "").split("\n")[0][:200],
                domain=domains.get(tool.name, "general"),
                kind="tool",
                required_params=required,
                optional_params=optional,
                input_schema=schema,
                output_schema=tool.output_schema or {},
                permission=permission,
                native=True,
                gui=gui_methods.get(_to_protocol_name(tool.name), False),
                retry_safe=permission == "read",
                undoable=permission in ("write",),
            )
        )

    # Bridge protocol methods that are not 1:1 with a tool are still worth
    # discovering, but only advertise the ones the bridge actually implements.
    tool_protocols = {_to_protocol_name(c.id) for c in caps}
    for method, available in sorted(gui_methods.items()):
        if method in tool_protocols:
            continue
        caps.append(
            Capability(
                id=method,
                name=method,
                description=f"Bridge protocol method ({'available' if available else 'planned'}).",
                domain="protocol",
                kind="protocol",
                permission="write",
                native=False,
                gui=available,
                execution_method="bridge",
                verification="protocol",
            )
        )
    return caps


def _to_protocol_name(tool_name: str) -> str:
    """Best-effort map from a tool name to its dotted protocol method."""
    parts = tool_name.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}.{'_'.join(parts[1:])}"
    return tool_name


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class CapabilityRegistry:
    """Searchable, invokable view over the server's capabilities."""

    def __init__(self, capabilities: list[Capability]) -> None:
        self._caps: dict[str, Capability] = {c.id: c for c in capabilities}

    def all(self) -> list[Capability]:
        return list(self._caps.values())

    def get(self, capability_id: str) -> Capability | None:
        return self._caps.get(capability_id)

    def search(self, query: str, domain: str | None = None, limit: int = 20) -> list[Capability]:
        q = query.lower().strip()
        tokens = [t for t in re.split(r"\W+", q) if t]
        scored: list[tuple[int, Capability]] = []
        for cap in self._caps.values():
            if domain and cap.domain != domain:
                continue
            haystack = f"{cap.id} {cap.description} {cap.domain}".lower()
            score = sum(3 if t in cap.id.lower() else (1 if t in haystack else 0) for t in tokens)
            if score or not tokens:
                scored.append((score, cap))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [cap for _, cap in scored[:limit]]

    def compact(self, cap: Capability) -> dict[str, Any]:
        """A one-line-per-capability summary that keeps the token cost low."""
        return {
            "id": cap.id,
            "domain": cap.domain,
            "summary": cap.description[:100],
            "required": cap.required_params,
            "permission": cap.permission,
        }


class WorkflowRunner:
    """Executes capability workflows and can persist/resume their state."""

    def __init__(self, registry: CapabilityRegistry, mcp: Any, state_dir: Path) -> None:
        self.registry = registry
        self.mcp = mcp
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _state_path(self, run_id: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", run_id)
        return self.state_dir / f"workflow_{safe}.json"

    async def execute(
        self, workflow: CapabilityWorkflow, run_id: str | None = None
    ) -> dict[str, Any]:
        run_id = run_id or workflow.id
        state: dict[str, Any] = {
            "run_id": run_id,
            "workflow": workflow.id,
            "context": {},
            "results": [],
        }
        return await self._run(workflow, state, start=0)

    async def resume(self, run_id: str) -> dict[str, Any]:
        path = self._state_path(run_id)
        if not path.is_file():
            raise ValidationError(f"No resumable workflow state for run '{run_id}'.")
        state = json.loads(path.read_text(encoding="utf-8"))
        workflow = next((w for w in BUILTIN_WORKFLOWS if w.id == state["workflow"]), None)
        if workflow is None:
            raise ValidationError(f"Unknown workflow '{state['workflow']}' in saved state.")
        return await self._run(workflow, state, start=state.get("next_step", 0))

    async def _run(
        self, workflow: CapabilityWorkflow, state: dict[str, Any], start: int
    ) -> dict[str, Any]:
        context: dict[str, Any] = state.setdefault("context", {})
        results: list[Any] = state.setdefault("results", [])
        for index in range(start, len(workflow.steps)):
            step = workflow.steps[index]
            cap = self.registry.get(step.capability)
            if cap is None:
                state["next_step"] = index
                self._persist(state)
                return {
                    "status": "failed",
                    "step": step.capability,
                    "error": "unknown capability",
                    **state,
                }
            try:
                args = _resolve(step.args, context)
                output = await self._invoke(step.capability, args)
            except SynfigError as exc:
                state["next_step"] = index
                self._persist(state)
                return {"status": "failed", "step": step.capability, "error": exc.message, **state}
            results.append({"step": step.capability, "ok": True})
            if step.save_as:
                context[step.save_as] = output
        state["next_step"] = len(workflow.steps)
        self._persist(state)
        return {"status": "completed", **state}

    def _persist(self, state: dict[str, Any]) -> None:
        path = self._state_path(state["run_id"])
        path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    async def _invoke(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self.mcp.call_tool(name, arguments)
        return _call_result_to_data(result)


def _call_result_to_data(result: Any) -> Any:
    """Best-effort conversion of a CallToolResult into plain JSON data."""
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if text is None:
            continue
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return text
    return None


# ---------------------------------------------------------------------------
# Meta-tool argument models
# ---------------------------------------------------------------------------


class BatchOperation(BaseModel):
    capability: str
    args: dict[str, Any] = Field(default_factory=dict)


class BatchRequest(BaseModel):
    operations: list[BatchOperation]
    stop_on_error: bool = True
