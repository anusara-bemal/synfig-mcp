# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""MCP resources: expose project state and docs over synfig:// URIs."""

from __future__ import annotations

import json
from typing import cast

from lxml import etree

from ..document.layers import list_layers
from ..document.validators import KNOWN_LAYER_TYPES
from ..errors import DocumentNotFoundError
from ..logging import get_logger

logger = get_logger(__name__)


def render_known_layer_types() -> str:
    return json.dumps(
        {
            "count": len(KNOWN_LAYER_TYPES),
            "layer_types": sorted(KNOWN_LAYER_TYPES),
            "note": "Availability of a type depends on your synfig build; run list_layer_types for the live list.",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def register(server, ctx) -> None:  # type: ignore[no-untyped-def]
    @server.resource("synfig://projects", name="Open projects", mime_type="application/json")
    async def projects() -> str:
        return json.dumps(
            {"projects": await ctx.registry.list()}, ensure_ascii=False, sort_keys=True
        )

    @server.resource(
        "synfig://project/{project_id}/info", name="Project info", mime_type="application/json"
    )
    async def project_info(project_id: str) -> str:
        try:
            session = await ctx.registry.get(project_id)
        except DocumentNotFoundError as exc:
            return json.dumps(exc.to_dict(), ensure_ascii=False)
        return json.dumps(session.info(), ensure_ascii=False, sort_keys=True)

    @server.resource(
        "synfig://project/{project_id}/layers", name="Project layers", mime_type="application/json"
    )
    async def project_layers(project_id: str) -> str:
        try:
            session = await ctx.registry.get(project_id)
        except DocumentNotFoundError as exc:
            return json.dumps(exc.to_dict(), ensure_ascii=False)
        return json.dumps(
            {"project_id": project_id, "layers": list_layers(session.root)},
            ensure_ascii=False,
            sort_keys=True,
        )

    @server.resource(
        "synfig://project/{project_id}/xml", name="Project XML", mime_type="application/xml"
    )
    async def project_xml(project_id: str) -> str:
        try:
            session = await ctx.registry.get(project_id)
        except DocumentNotFoundError as exc:
            # Return a plain-text error body; still 200 so clients can read it.
            return f"<!-- error: {exc.message} -->"
        return cast(
            str,
            etree.tostring(
                session.tree, xml_declaration=True, encoding="UTF-8", pretty_print=True
            ).decode("utf-8", errors="replace"),
        )

    @server.resource(
        "synfig://docs/layer-types", name="Synfig layer types", mime_type="application/json"
    )
    async def docs_layer_types() -> str:
        return render_known_layer_types()
